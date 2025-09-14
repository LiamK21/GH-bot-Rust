import logging
from pathlib import Path

import docker
from docker.errors import ImageNotFound

from webhook_handler.helper import logger
from webhook_handler.helper.custom_errors import *
from webhook_handler.models import LLM, PipelineInputs, PullRequestData
from webhook_handler.services import (Config, CSTBuilder, DockerService,
                                      GitHubService, LLMHandler,
                                      PullRequestDiffContext, TestGenerator)


class BotRunner:
    """Handles running the bot"""

    def __init__(
        self, payload: dict, config: Config, post_comment: bool = False
    ) -> None:
        self._pr_data = PullRequestData.from_payload(payload)
        self._execution_id = f"{self._pr_data.repo}_{self._pr_data.number}"
        self._config = config
        self._post_comment = post_comment
        self._generation_completed = False
        self._environment_prepared = False

        self._gh_service = GitHubService(config, self._pr_data)
        self._issue_statement = None
        self._pr_diff_ctx = None
        self._pipeline_inputs = None
        self._llm_handler = None
        self._docker_service = None
        self._cst_builder = None

    def is_valid_pr(self) -> tuple[str, bool]:
        """
        PR must have linked issue and source code changes.

        Returns:
            str: Message to deliver to client
            bool: True if PR is valid, False otherwise
        """

        self._logger.marker(  # type: ignore[attr-defined]
            f"=============== Running Payload #{self._pr_data.number} ==============="
        )
        self._logger.marker("================ Preparing Environment ===============")  # type: ignore[attr-defined]
        self._issue_statement = self._gh_service.get_linked_data()
        if not self._issue_statement:
            # helpers.remove_dir(self._config.pr_log_dir)
            self._gh_api = None
            self._issue_statement = None
            self._pdf_candidate = None
            return "No linked issue found", False

        self._pr_diff_ctx = PullRequestDiffContext(
            self._pr_data.base_commit, self._pr_data.head_commit, self._gh_service
        )
        if not self._pr_diff_ctx.fulfills_requirements:
            # helpers.remove_dir(self._config.pr_log_dir)
            self._gh_api = None
            self._issue_statement = None
            self._pdf_candidate = None
            self._pr_diff_ctx = None
            return "Must modify source code files only", False

        return "Payload is being processed...", True

    def execute_runner(self, curr_attempt: int, model: LLM) -> bool:
        """
        Execute the bot runner once with the current attempt and provided model.

        Parameters:
            curr_attempt (int): The current attempt number
            model (LLM): The model to be queried

        Returns:
            bool: True if the generation was successful, False otherwise
        """
        # setup the output directory
        self._config.setup_output_dir(curr_attempt, model)

        # Prepare environment
        self.prepare_environment()
        if self._pipeline_inputs is None:
            raise DataMissingError(
                "pipeline_inputs", "None", "Pipeline inputs not prepared"
            )

        if self._llm_handler is None:
            raise DataMissingError("llm_handler", "None", "LLM Handler not prepared")

        if self._cst_builder is None:
            raise DataMissingError("cst_builder", "None", "CST Builder not prepared")

        if self._docker_service is None:
            raise DataMissingError(
                "docker_service", "None", "Docker Service not prepared"
            )

        if self._config.output_dir is None:
            raise DataMissingError("output_dir", "None", "Output directory not set")

        generator = TestGenerator(
            self._config,
            self._pipeline_inputs,
            # self._mock_response,
            self._post_comment,
            self._gh_service,
            self._cst_builder,
            self._docker_service,
            self._llm_handler,
            i_attempt=curr_attempt,
            model=model,
        )

        try:
            result = generator.generate()
            self._logger.success(f"Attempt %d with model %s finished successfully" % (curr_attempt + 1, model))  # type: ignore[attr-defined]
            if result is True:
                generated_test: str = Path(
                    self._config.output_dir, "generated_test.txt"
                ).read_text(encoding="utf-8")
                new_filename = (
                    f"{self._execution_id}_{self._config.output_dir.name}.txt"
                )
                Path(self._config.gen_test_dir, new_filename).write_text(
                    generated_test, encoding="utf-8"
                )
            return result if result is not None else False

        except (FileExistsError, FileNotFoundError, PermissionError) as e:
            self._logger.critical(f"File error occurred during runner execution: {e}")
            # raise ExecutionError("File error occurred during execution")
            return False
        except DataMissingError as e:
            self._logger.critical(
                f"Data missing error occurred during runner execution: {e}"
            )
            # raise ExecutionError("Data missing error occurred during execution")
            return False
        except ExecutionError as e:
            self._logger.critical(
                f"Execution error occurred during runner execution: {e}"
            )
            # raise ExecutionError("Data missing error occurred during execution")
            return False
        except Exception as e:
            self._logger.critical(
                f"Another error occurred during runner execution: {e}"
            )
            # raise ExecutionError("File error occurred during execution")
            return False
        finally:
            self._record_result(curr_attempt, model)

    def prepare_environment(self) -> None:
        """Prepares all services and data used in each attempt"""

        if self._environment_prepared:
            self._logger.info(
                "Environment already prepared, skipping preparation phase..."
            )
            return

        self._setup_logging()
        # Check if PR has a linked issue (and verify that it is a bug)
        self._issue_statement = self._gh_service.get_linked_data()
        if self._issue_statement:
            self._logger.info("Linked issue found")
        else:
            self._logger.critical("No Linked issue found, raising exception")
            raise ExecutionError("No linked issue found for PR")

        # Prepare directories

        # Get the file contents
        if self._pr_diff_ctx is None:
            self._pr_diff_ctx = PullRequestDiffContext(
                self._pr_data.base_commit, self._pr_data.head_commit, self._gh_service
            )
        if len(self._pr_diff_ctx.source_code_file_diffs) == 0:
            raise ExecutionError("No source code changes found in PR")

        # Clone repository and checkout to the PR branch
        if self._config.cloned_repo_dir is None:
            raise DataMissingError(
                "cloned_repo_dir", "None", "Path to cloned repository directory not set"
            )

        # If repository has not been cloned yet, clone it
        if not Path(self._config.cloned_repo_dir).exists():
            self._logger.info("Repository does not exist yet, cloning...")
            self._gh_service.clone_repo()

        # If it is a different repository, clone the new one
        if self._config.cloned_repo_dir.find(self._pr_data.repo) == -1:
            self._logger.info("Different repository exists, cloning new one...")
            self._gh_service.clone_repo()

        self._cst_builder = CSTBuilder(self._config.parsing_language, self._pr_diff_ctx)
        # code_sliced = self._cst_builder.get_sliced_code_files()

        # Build docker image if not exists
        self._docker_service = DockerService(self._config.root_dir, self._pr_data)
        self._docker_service.check_and_build_image()

        # Gather Pipeline data
        self._pipeline_inputs = PipelineInputs(
            pr_data=self._pr_data,
            pr_diff_ctx=self._pr_diff_ctx,
            # code_sliced,
            problem_statement=self._issue_statement,
        )

        # Setup LLM handler
        self._llm_handler = LLMHandler(self._config, self._pipeline_inputs)
        self._environment_prepared = True

    def _setup_logging(self) -> None:
        """Sets up logging for the current PR run"""

        if self._config.pr_log_dir is None:
            raise DataMissingError(
                "pr_log_dir", "None", "Pull Request logging directory not set"
            )
        assert self._config.pr_log_dir
        logger.configure_logger(self._config.pr_log_dir, self._execution_id)
        self._logger = logging.getLogger()

    def _create_model_attempt_dir(self, curr_attempt: int, model: LLM) -> None:
        """Creates a directory for the current attempt with the current model"""

        if self._config.pr_log_dir is None:
            raise DataMissingError(
                "pr_log_dir", "None", "Pull Request logging directory not set"
            )

        attempt_instance_dir = Path(
            self._config.pr_log_dir, f"{model}_i{curr_attempt + 1}"
        )
        attempt_instance_dir.mkdir(parents=True, exist_ok=True)

        # Create a generation subdirectory within the attempt directory
        self._logger.info(f"Created model attempt directory: {attempt_instance_dir}")

    def _record_result(
        self,
        i_attempt: int,
        model: LLM,
    ) -> None:
        """
        Writes result to csv.

        Parameters:
            number (str): The number of the PR
            model (LLM): The model
            i_attempt (int): The attempt number
            stop (bool | str): The stop flag or an error string
        """

        with open(Path(self._config.bot_log_dir, "results.csv"), "a") as f:
            f.write(
                "{:<9},{:<30},{:<9},{:<45}\n".format(
                    self._pr_data.number, model, i_attempt, self._generation_completed
                )
            )

    def teardown(self) -> None:
        """
        Remove all temporary created directories, files, and data
        """
        self._config._teardown()
        image_tag = f"{self._pr_data.image_tag}:latest"
        try:
            client = docker.from_env()
            client.images.remove(image=image_tag, force=True)
            self._logger.success(f"Removed Docker image {image_tag}")  # type: ignore[attr-defined]
            pass
        except ImageNotFound:
            self._logger.error(f"Docker image {image_tag} not found, skipping removal")  # type: ignore[attr-defined]
        except Exception as e:
            self._logger.error(f"Failed to remove Docker image '{image_tag}': {e}")
        
        
        self._gh_api = None
        self._issue_statement = None
        self._pdf_candidate = None
        self._pr_diff_ctx = None
        self._pipeline_inputs = None
        self._cst_builder = None
        self._llm_handler = None
        self._docker_service = None
        self._environment_prepared = False
        self._logger.info("Teardown completed")
        