import logging
import re
from pathlib import Path

from webhook_handler.helper import general, git_diff, templates
from webhook_handler.helper.custom_errors import *
from webhook_handler.models import (LLM, LLMResponse, PipelineInputs,
                                    PromptType, TestCoverage)
from webhook_handler.services import Config
from webhook_handler.services.cst_builder import CSTBuilder
from webhook_handler.services.docker_service import DockerService
from webhook_handler.services.gh_service import GitHubService
from webhook_handler.services.llm_handler import LLMHandler

logger = logging.getLogger(__name__)


class TestGenerator:
    """
    Runs a full pipeline to generate a test using a LLM and then verifying its correctness.
    """

    def __init__(
        self,
        config: Config,
        data: PipelineInputs,
        post_comment: bool,
        gh_service: GitHubService,
        cst_builder: CSTBuilder,
        docker_service: DockerService,
        llm_handler: LLMHandler,
        i_attempt: int,
        model: LLM,
    ):
        self._config = config
        self._pipeline_inputs = data
        self._pr_data = data.pr_data
        self._pr_diff_ctx = data.pr_diff_ctx
        self._post_comment = post_comment
        self._gh_service = gh_service
        self._cst_builder = cst_builder
        self._docker_service = docker_service
        self._llm_handler = llm_handler
        self._i_attempt = i_attempt
        self._model = model
        self._generation_dir: Path | None = None

    def generate(self) -> tuple[bool, Path | None]:

        logger.marker("=============== Test Generation Started ==============")  # type: ignore[attr-defined]
        logger.marker("Attempt %d with model %s" % (self._i_attempt + 1, self._model))  # type: ignore[attr-defined]

        curr_llm_attempt = 1
        fail_2_pass, llm_response = self.run_workflow(curr_llm_attempt)

        if fail_2_pass:
            logger.success("Fail-to-Pass test generated")  # type: ignore[attr-defined]
            logger.marker("Running code coverage to verify usability of generated test")  # type: ignore[attr-defined]
            coverage_passed, test_coverage = (
                self._determine_test_usability(llm_response)
            )
            if coverage_passed:
                logger.marker("[*] Handling commenting on PR")  # type: ignore[attr-defined]
                filename, imports = llm_response.filename, llm_response.imports
                assert test_coverage is not None
                self._handle_commenting(
                    filename, imports, test_coverage
                )
            logger.marker("=============== Test Generation Finished =============")  # type: ignore[attr-defined]
            return True, self._generation_dir
        else:
            logger.info("No Fail-to-Pass test generated")
            logger.marker("=============== Test Generation Finished =============")  # type: ignore[attr-defined]
            return False, None

    def run_workflow(
        self,
        curr_llm_attempt: int,
        prompt_type: PromptType = PromptType.INITIAL,
        previous_test: str = "",
        failure_reason: str = "",
    ) -> tuple[bool, LLMResponse]:
        """
        Runs the pipeline to generate a fail-to-pass test.

        Returns:
            bool: True if a fail-to-pass test has been generated, False otherwise
        """

        logger.marker("Current LLM call %s" % (curr_llm_attempt))  # type: ignore[attr-defined]

        prompt = self._llm_handler.build_prompt(
            prompt_type, previous_test, failure_reason
        )

        if len(prompt) >= 1048576:  # gpt4o limit
            logger.critical("Prompt exceeds limits, skipping...")
            raise ExecutionError("Prompt is too long.")

        assert self._config.output_dir is not None
        self._generation_dir = Path(
            self._config.output_dir, f"llm_call_{curr_llm_attempt}"
        )
        self._generation_dir.mkdir(parents=True, exist_ok=True)
        (self._generation_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
        logger.marker(  # type: ignore[attr-defined]
            "New prompt written to %s"
            % (self._generation_dir / f"prompt_{curr_llm_attempt}.txt")
        )

        # print("Mocking response for debugging...")
        # response = Path(Path.cwd(), "bot_logs", "raw_model_response.txt").read_text(
        #     encoding="utf-8"
        # )
        logger.info("Querying LLM...")
        response = self._llm_handler.query_model(
            prompt, model=self._model, temperature=0.0
        )
        if not response:
            logger.critical("Failed to query model")
            raise Exception("Failed to query model")

        logger.success("LLM response received")  # type: ignore[attr-defined]
        (self._generation_dir / "raw_model_response.txt").write_text(
            response, encoding="utf-8"
        )
        postprocess_response = self._llm_handler.postprocess_response(response)
        if postprocess_response is None:
            logger.info("Model did not return a test, skipping...")
            # self._handle_commenting()
            return False, LLMResponse(
                filename="",
                imports=[],
                test_code="",
                test_name="",
                curr_llm_cal=curr_llm_attempt,
            )

        response_filename, imports, new_test = postprocess_response

        (self._generation_dir / f"generated_test.txt").write_text(
            new_test, encoding="utf-8"
        )

        filename = self._pr_diff_ctx.get_absolute_file_path(response_filename)
        assert filename is not None, "Filename received from model does not exist"

        test_name_pattern = r"fn (\w+)"
        match = re.search(test_name_pattern, new_test)
        if not match:
            logger.error("Could not extract test name from generated test")
            return False, LLMResponse(
                filename="",
                imports=[],
                test_code="",
                test_name="",
                curr_llm_cal=curr_llm_attempt,
            )

        test_to_run: str = match.group(1)

        llm_response = LLMResponse(
            filename=filename,
            imports=imports,
            test_code=new_test,
            test_name=test_to_run,
            curr_llm_cal=curr_llm_attempt,
        )
        lint_passed, lint_out = self.check_for_linting_issues(llm_response)

        if not lint_passed:
            logger.warning("Linting issues found in generated test")
            if curr_llm_attempt < self._config.MAX_LLM_CALLS:
                logger.info("Retrying with LINTING_ISSUE prompt...")
                full_test = general.build_response_test(llm_response)
                return self.run_workflow(
                    curr_llm_attempt + 1, PromptType.LINTING_ISSUE, full_test, lint_out
                )
            else:
                logger.critical("Max LLM calls reached, continuing execution...")

        test_passed_before = self.run_test_pre_pr(
            filename, new_test, imports, test_to_run
        )

        if test_passed_before:
            logger.warning("No Fail-to-Pass test generated")
            if curr_llm_attempt < self._config.MAX_LLM_CALLS:
                logger.info("Retrying with PASS_TO_PASS prompt...")
                full_test = general.build_response_test(llm_response)
                return self.run_workflow(
                    curr_llm_attempt + 1, PromptType.PASS_TO_PASS, full_test
                )

            logger.critical("Max LLM calls reached, continuing execution...")
            logger.marker("=============== Test Generation Finished =============")  # type: ignore[attr-defined]
            return False, llm_response

        test_passed_after, after_out = self.run_test_post_pr(
            filename, new_test, imports, test_to_run
        )

        fail_2_pass = (not test_passed_before) and test_passed_after

        if fail_2_pass:
            return True, llm_response
        else:
            logger.info("No Fail-to-Pass test generated")  # type: ignore[attr-defined]
            if curr_llm_attempt < self._config.MAX_LLM_CALLS:
                is_assertion_error = "test result: FAILED." in after_out
                full_test = general.build_response_test(llm_response)
                if is_assertion_error:
                    logger.marker("Test failed due to assertion error, retrying...")  # type: ignore[attr-defined]
                    failures = general.retrieve_output_test_failure(after_out)
                    return self.run_workflow(
                        curr_llm_attempt + 1, PromptType.ASSERTION_ERROR, full_test, failures
                    )
                else:
                    logger.marker("Test failed due to compilation/runtime error, retrying...")  # type: ignore[attr-defined]
                    errors = general.retrieve_output_errors(after_out)
                    return self.run_workflow(
                        curr_llm_attempt + 1,
                        PromptType.COMPILATION_ERROR,
                        full_test,
                        errors,
                    )
            logger.marker("=============== Test Generation Finished =============")  # type: ignore[attr-defined]
            return False, llm_response

    def check_for_linting_issues(self, llm_response: LLMResponse) -> tuple[bool, str]:
        if not self._config.cloned_repo_dir:
            raise DataMissingError(
                "cloned_repo_dir", "None", "Cloned repo dir should not be None"
            )
        if not self._generation_dir:
            raise DataMissingError(
                "generation_dir", "None", "Generation dir should not be None"
            )

        filename, new_test, imports = (
            llm_response.filename,
            llm_response.test_code,
            llm_response.imports,
        )

        pr_file_diff = self._pr_diff_ctx.get_specific_file_diff(llm_response.filename)
        file_content = pr_file_diff.after if pr_file_diff else ""

        if file_content:
            logger.marker(f"File {filename} exists in head commit")  # type: ignore[attr-defined]
            new_file_content = self._cst_builder.append_test(
                file_content, new_test, imports
            )
        else:
            logger.critical(f"File {filename} does not exist in head commit")  # type: ignore[attr-defined]
            raise ExecutionError(
                f"File {filename} should exist in head commit but does not"
            )

        golden_code_patch: str = self._pr_diff_ctx.get_updated_golden_code_patch(
            filename, new_file_content
        )

        lint_passed, stdout = self._docker_service.run_linter(golden_code_patch)
        (self._generation_dir / "lint.txt").write_text(stdout, encoding="utf-8")

        linting_errors = general.retrieve_output_errors(stdout)
        return lint_passed, linting_errors

    def run_test_pre_pr(
        self, filename: str, new_test: str, imports: list[str], test_to_run: str
    ) -> bool:
        if not self._config.cloned_repo_dir:
            raise DataMissingError(
                "cloned_repo_dir", "None", "Cloned repo dir should not be None"
            )
        if not self._generation_dir:
            raise DataMissingError(
                "generation_dir", "None", "Generation dir should not be None"
            )

        file_content = general.get_candidate_file(
            self._pr_data.base_commit, filename, self._config.cloned_repo_dir
        )

        if file_content:
            logger.marker(f"File {filename} exists in base commit")  # type: ignore[attr-defined]
            new_file_content = self._cst_builder.append_test(
                file_content, new_test, imports
            )
        else:
            logger.marker(f"File {filename} does not exist in base commit")  # type: ignore[attr-defined]
            new_file_content = self._cst_builder._create_test_block(new_test, imports)

        test_passed, stdout = self._run_test(
            filename, file_content, new_file_content, [test_to_run], True
        )

        (self._generation_dir / "before.txt").write_text(stdout, encoding="utf-8")
        return test_passed

    def run_test_post_pr(
        self, filename: str, new_test: str, imports: list[str], test_to_run: str
    ) -> tuple[bool, str]:
        if not self._config.cloned_repo_dir:
            raise DataMissingError(
                "cloned_repo_dir", "None", "Cloned repo dir should not be None"
            )
        if not self._generation_dir:
            raise DataMissingError(
                "generation_dir", "None", "Generation dir should not be None"
            )
        # Try to get the direct file content from the head commit instead of checking out the commit
        # This is to avoid issues where PRs or such are from forked repos and the commit does not exist in the main repo
        logger.info(
            "Getting file content from head commit rather than checking out commit..."
        )
        pr_file_diff = self._pr_diff_ctx.get_specific_file_diff(filename)
        file_content = pr_file_diff.after if pr_file_diff else ""

        if file_content:
            logger.marker(f"File {filename} exists in head commit")  # type: ignore[attr-defined]
            new_file_content = self._cst_builder.append_test(
                file_content, new_test, imports
            )
        else:
            logger.critical(f"File {filename} does not exist in head commit")  # type: ignore[attr-defined]
            raise ExecutionError(
                f"File {filename} should exist in head commit but does not"
            )

        test_passed, stdout = self._run_test(
            filename, file_content, new_file_content, [test_to_run], False
        )

        (self._generation_dir / "after.txt").write_text(stdout, encoding="utf-8")
        new_test_file = f"#{filename}\n{new_file_content}"

        (self._generation_dir / "new_file_content.rs").write_text(
            new_test_file, encoding="utf-8"
        )

        return test_passed, stdout

    def _run_test(
        self,
        filename: str,
        old_file_content: str,
        new_file_content: str,
        test_to_run: list[str],
        is_pre_pr: bool,
    ) -> tuple[bool, str]:
        if is_pre_pr:
            model_test_patch = (
                git_diff.unified_diff(
                    old_file_content,
                    new_file_content,
                    fromfile=filename,
                    tofile=filename,
                )
                + "\n\n"
            )
            if old_file_content:
                logger.marker("Running test in pre-PR codebase...")  # type: ignore[attr-defined]
                return self._docker_service.run_test_in_container(
                    model_test_patch, test_to_run, False
                )
            else:
                logger.marker("File did not exist in pre-PR codebase, cannot run test...")  # type: ignore[attr-defined]
                return (
                    False,
                    "Empty stdout because file did not exist in pre-PR codebase",
                )

        elif not is_pre_pr and old_file_content:
            logger.marker("Running test in post-PR codebase...")  # type: ignore[attr-defined]
            # The golden code patch must be equal to all other files the test was not generated for
            # For the file the test was generated for, we need to modify the patch to
            # include the new test as well
            golden_code_patch: str = self._pr_diff_ctx.get_updated_golden_code_patch(
                filename, new_file_content
            )
            return self._docker_service.run_test_in_container(
                golden_code_patch, test_to_run, True
            )
        else:
            raise ExecutionError(
                "Cannot run test in post-PR codebase without old file content"
            )

    def _determine_test_usability(
        self, llm_response: LLMResponse
    ) -> tuple[bool, TestCoverage | None]:
        if not self._config.cloned_repo_dir:
            raise DataMissingError(
                "cloned_repo_dir", "None", "Cloned repo dir should not be None"
            )
        if not self._generation_dir:
            raise DataMissingError(
                "generation_dir", "None", "Generation dir should not be None"
            )
        filename, new_test, imports = (
            llm_response.filename,
            llm_response.test_code,
            llm_response.imports,
        )

        pr_file_diff = self._pr_diff_ctx.get_specific_file_diff(filename)
        file_content = pr_file_diff.after if pr_file_diff else ""

        if file_content:
            new_file_content = self._cst_builder.append_test(
                file_content, new_test, imports
            )
        else:
            logger.critical(f"File {filename} does not exist in head commit")  # type: ignore[attr-defined]
            raise ExecutionError(
                f"File {filename} should exist in head commit but does not"
            )

        # We first want to run code coverage in a container only with the golden patch to evaluate it before the auto-generated test
        logger.marker("Running code coverage with golden patch only...")  # type: ignore[attr-defined]
        golden_code_patch = self._pr_diff_ctx.golden_code_patch
        file_line_coverage_without, suite_line_coverage_without = self._docker_service.run_coverage_in_container(
            filename, golden_code_patch
        )

        logger.marker("Running code coverage with golden patch and generated test...")  # type: ignore[attr-defined]
        golden_code_patch: str = self._pr_diff_ctx.get_updated_golden_code_patch(
            filename, new_file_content
        )
        file_line_coverage_with, suite_line_coverage_with = self._docker_service.run_coverage_in_container(
            filename, golden_code_patch
        )
        test_coverage = TestCoverage(
            file_line_coverage_with=file_line_coverage_with,
            suite_line_coverage_with=suite_line_coverage_with,
            file_line_coverage_without=file_line_coverage_without,
            suite_line_coverage_without=suite_line_coverage_without,
        )

        if not test_coverage.coverage_exists():
            logger.error("Could not retrieve line coverage, marking test as non-usable")
            return False, None

        elif test_coverage.coverage_improved():
            logger.success("Generated test does improve line coverage, marking as non-usable")  # type: ignore[attr-defined]
            return True, test_coverage
        else:
            return False, test_coverage

    def _handle_commenting(
        self,
        filename: str,
        imports: list[str],
        test_coverage: TestCoverage
        
    ) -> None:
        assert self._generation_dir is not None
        comment = templates.COMMENT_TEMPLATE % (
            f"{test_coverage.file_line_coverage_without:.2f}%",
            f"{test_coverage.file_line_coverage_with:.2f}%",
            f"{test_coverage.suite_line_coverage_without:.2f}%",
            f"{test_coverage.suite_line_coverage_with:.2f}%",
            "\n".join(imports),
            (self._generation_dir / "generated_test.txt").read_text(encoding="utf-8"),
            filename,
        )
        (self._generation_dir / "comment_incl_coverage.txt").write_text(comment)
        if self._post_comment:
            status_code, response_data = self._gh_service.add_comment_to_pr(comment)
            if status_code == 201:
                logger.success("Comment added successfully:\n\n%s" % comment)  # type: ignore[attr-defined]
            else:
                logger.error(f"Failed to add comment: {status_code}", response_data)
        return

    def _get_relevant_file(
        self, rel_filename: str, repo_dir: str, base_commit: str
    ) -> tuple[str, str]:
        filename = self._pr_diff_ctx.get_absolute_file_path(rel_filename)
        assert filename is not None, "Absolute filename should not be None"

        file_content = general.get_candidate_file(base_commit, filename, repo_dir)

        return filename, file_content
