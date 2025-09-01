import logging
from pathlib import Path

from webhook_handler.constants import PROMPT_COMBINATIONS_GEN
from webhook_handler.helper import general, git_diff, templates
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
        self._prompt_combinations = PROMPT_COMBINATIONS_GEN
        self._post_comment = post_comment
        self._comment_template = templates.COMMENT_TEMPLATE
        self._gh_service = gh_service
        self._cst_builder = cst_builder
        self._docker_service = docker_service
        self._llm_handler = llm_handler
        self._i_attempt = i_attempt
        self._model = model

        self._generation_dir: Path | None = None

    def generate(self) -> bool:
        """
        Runs the pipeline to generate a fail-to-pass test.

        Returns:
            bool: True if a fail-to-pass test has been generated, False otherwise
        """

        logger.marker("Attempt %d with model %s" % (self._i_attempt + 1, self._model))
        logger.marker("=============== Test Generation Started ==============")

        # include_golden_code = bool(self._prompt_combinations["include_golden_code"][self._i_attempt])
        # sliced = bool(self._prompt_combinations["sliced"][self._i_attempt])
        # include_pr_summary = bool(self._prompt_combinations["include_pr_summary"][self._i_attempt])
        # include_predicted_test_file = bool(self._prompt_combinations["include_predicted_test_file"][self._i_attempt])

        prompt = self._llm_handler.build_prompt(
            # include_golden_code,
            # sliced,
            # include_pr_summary,
            # include_predicted_test_file,
            # self._pipeline_inputs.test_filename,
            # self._pipeline_inputs.test_file_content_sliced,
            # self._pipeline_inputs.available_packages,
            # self._pipeline_inputs.available_relative_imports
        )

        if len(prompt) >= 1048576:  # gpt4o limit
            logger.critical("Prompt exceeds limits, skipping...")
            raise Exception("Prompt is too long.")

        assert self._config.output_dir is not None
        self._generation_dir = Path(self._config.output_dir, "generation")
        (self._generation_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
        logger.marker(
            "New prompt written to %s" % (self._generation_dir / "prompt.txt")
        )
        logger.marker("Stopping execution for debugging purposes")

        # print("Mocking response for debugging...")
        # response = Path(Path.cwd(), "bot_logs", "raw_model_response.txt").read_text(
        #     encoding="utf-8"
        # )
        # if self._mock_response is None:
        logger.info("Querying LLM...")
        response = self._llm_handler.query_model(
            prompt, model=self._model, temperature=0.0
        )
        if not response:
           logger.critical("Failed to query model")
           raise Exception("Failed to query model")

        logger.success("LLM response received")
        (self._generation_dir / "raw_model_response.txt").write_text(
            response, encoding="utf-8"
        )
        postprocess_response = self._llm_handler.postprocess_response(response)
        if postprocess_response is None:
            # self._handle_commenting()
            return True

        response_filename, imports, new_test = postprocess_response

        (self._generation_dir / "generated_test.txt").write_text(
            new_test, encoding="utf-8"
        )
        new_test = new_test.replace(
            "src/", ""
        )  # temporary replacement to run in lib-legacy

        # Retrieve the test file content from the filename
        assert self._config.cloned_repo_dir is not None, "Cloned repo dir must be set"

        filename, file_content = self._get_relevant_file(
            response_filename, self._config.cloned_repo_dir, self._pr_data.base_commit
        )

        new_file_content = ""
        if file_content:
            new_file_content = self._cst_builder.append_test(
                file_content, new_test, imports
            )
        else:
            new_file_content = new_test

        is_pass_2_fail = self._run_test_pre_and_post_pr(
            file_content, new_file_content, filename
        )

        if is_pass_2_fail:
            logger.success("Fail-to-Pass test generated")
            self._handle_commenting(filename)
            logger.marker("=============== Test Generation Finished =============")
            return True
        else:
            logger.fail("No Fail-to-Pass test generated")
            logger.marker("=============== Test Generation Finished =============")
            return False

    def _run_test_pre_and_post_pr(
        self, old_file_content: str, new_file_content: str, filename: str
    ) -> bool:
        assert self._generation_dir is not None
        model_test_patch: str = ""
        if old_file_content:
            model_test_patch = (
                git_diff.unified_diff(
                    old_file_content,
                    new_file_content,
                    fromfile=filename,
                    tofile=filename,
                )
                + "\n\n"
            )
        else:
            model_test_patch = new_file_content + "\n\n"

        test_file_diff = PullRequestFileDiff(
            filename,
            old_file_content,
            new_file_content,
        )

        test_to_run = self._cst_builder.extract_changed_tests(test_file_diff)

        logger.marker("Running test in pre-PR codebase...")
        # TODO: Does this method actually need to be called if the file_content doesn't exist (file was only created later)
        test_passed_before, stdout_before = self._docker_service.run_test_in_container(
            model_test_patch, test_to_run, test_file_diff
        )
        (self._generation_dir / "before.txt").write_text(
            stdout_before, encoding="utf-8"
        )
        new_test_file = f"#{filename}\n{new_file_content}"

        (self._generation_dir / "new_test_file_content.rs").write_text(
            new_test_file, encoding="utf-8"
        )

        if test_passed_before:
            logger.fail("No Fail-to-Pass test generated")
            logger.marker("=============== Test Generation Finished =============")
            return False

        logger.marker("Running test in post-PR codebase...")
        test_passed_after, stdout_after = self._docker_service.run_test_in_container(
            model_test_patch,
            test_to_run,
            test_file_diff,
            golden_code_patch=self._pr_diff_ctx.golden_code_patch,
        )
        (self._generation_dir / "after.txt").write_text(stdout_after, encoding="utf-8")
        return test_passed_after

    def _handle_commenting(
        self, filename: str, no_test_gen_reason: str | None = None
    ) -> None:
        assert self._generation_dir is not None
        if self._post_comment:
            if no_test_gen_reason is None:
                comment = self._comment_template % (
                    (self._generation_dir / "generated_test.txt").read_text(
                        encoding="utf-8"
                    ),
                    filename,
                )
                status_code, response_data = self._gh_service.add_comment_to_pr(comment)
                if status_code == 201:
                    logger.success("Comment added successfully:\n\n%s" % comment)
                else:
                    logger.fail(f"Failed to add comment: {status_code}", response_data)
        return

    def _get_relevant_file(
        self, rel_filename: str, repo_dir: str, base_commit: str
    ) -> tuple[str, str]:
        filename = self._pr_diff_ctx.get_absolute_file_path(rel_filename)
        assert filename is not None, "Absolute filename should not be None"

        file_content = general.get_candidate_file(base_commit, filename, repo_dir)
        return filename, file_content
