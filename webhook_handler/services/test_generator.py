import logging
import re
from pathlib import Path

from webhook_handler.helper import general, git_diff, templates
from webhook_handler.helper.custom_errors import *
from webhook_handler.models import LLM, PipelineInputs, PullRequestFileDiff
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

    def generate(self) -> bool | None:
        """
        Runs the pipeline to generate a fail-to-pass test.

        Returns:
            bool: True if a fail-to-pass test has been generated, False otherwise
        """

        logger.marker("Attempt %d with model %s" % (self._i_attempt + 1, self._model))  # type: ignore[attr-defined]
        logger.marker("=============== Test Generation Started ==============")  # type: ignore[attr-defined]

        prompt = self._llm_handler.build_prompt()

        if len(prompt) >= 1048576:  # gpt4o limit
            logger.critical("Prompt exceeds limits, skipping...")
            raise ExecutionError("Prompt is too long.")

        assert self._config.output_dir is not None
        self._generation_dir = Path(self._config.output_dir)
        (self._generation_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
        logger.marker(  # type: ignore[attr-defined]
            "New prompt written to %s" % (self._generation_dir / "prompt.txt")
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
            return None

        response_filename, imports, new_test = postprocess_response

        (self._generation_dir / "generated_test.txt").write_text(
            new_test, encoding="utf-8"
        )
        new_test = new_test.replace(
            "src/", ""
        )  # temporary replacement to run in lib-legacy

        filename = self._pr_diff_ctx.get_absolute_file_path(response_filename)
        assert filename is not None, "Filename received from model does not exist"

        test_name_pattern = r"fn (\w+)"
        match = re.search(test_name_pattern, new_test)
        if not match:
            logger.error("Could not extract test name from generated test")
            return None

        test_to_run: str = match.group(1)

        test_passed_before = self.run_test_pre_pr(
            filename, new_test, imports, test_to_run
        )

        if test_passed_before:
            logger.warning("No Fail-to-Pass test generated")
            logger.marker("=============== Test Generation Finished =============")  # type: ignore[attr-defined]
            return False

        test_passed_after = self.run_test_post_pr(
            filename, new_test, imports, test_to_run
        )

        fail_2_pass = (not test_passed_before) and test_passed_after

        if fail_2_pass:
            logger.success("Fail-to-Pass test generated")  # type: ignore[attr-defined]
            self._handle_commenting(filename)
            logger.marker("=============== Test Generation Finished =============")  # type: ignore[attr-defined]
            return True
        else:
            logger.info("No Fail-to-Pass test generated")  # type: ignore[attr-defined]
            logger.marker("=============== Test Generation Finished =============")  # type: ignore[attr-defined]
            return False

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

        self._pr_diff_ctx

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
        new_test_file = f"#{filename}\n{new_file_content}"

        (self._generation_dir / "new_test_file_content.rs").write_text(
            new_test_file, encoding="utf-8"
        )
        return test_passed

    def run_test_post_pr(
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
        # Try to get the direct file content from the head commit instead of checking out the commit
        # This is to avoid issues where PRs or such are from forked repos and the commit does not exist in the main repo            
        logger.info("Getting file content from head commit rather than checking out commit...")
        pr_file_diff = self._pr_diff_ctx.get_specific_file_diff(filename)
        file_content = pr_file_diff.after if pr_file_diff else ""
        # logger.warning("An error occurred while fetching the file content from head commit")

        # file_content = general.get_candidate_file(
        #     self._pr_data.head_commit, filename, self._config.cloned_repo_dir
        # )

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
        return test_passed

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

    def _handle_commenting(
        self, filename: str, no_test_gen_reason: str | None = None
    ) -> None:
        assert self._generation_dir is not None
        if self._post_comment:
            if no_test_gen_reason is None:
                comment = templates.COMMENT_TEMPLATE % (
                    (self._generation_dir / "generated_test.txt").read_text(
                        encoding="utf-8"
                    ),
                    filename,
                )
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
