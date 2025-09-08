import io
import logging
import os
import re
import tarfile
import tempfile
from pathlib import Path

import docker
from docker.errors import APIError, BuildError, ImageNotFound
from docker.models.containers import Container
from docker.models.images import Image

from webhook_handler.helper.custom_errors import *
from webhook_handler.models import PullRequestData

logger = logging.getLogger(__name__)

type TestResult = tuple[bool, str]  # (test_passed, output)


class DockerService:
    """
    Used for Docker operations.
    """

    def __init__(self, project_root: Path, pr_data: PullRequestData) -> None:
        self._project_root = project_root
        self._pr_data = pr_data
        self._client = docker.from_env()

    def check_and_build_image(self) -> None:
        """Check if the Docker image exists, and if not, build it from the Dockerfiles in the dockerfile directory"""

        logger.marker("Checking Docker image...")  # type: ignore[attr-defined]

        tag = f"{self._pr_data.image_tag}:latest"
        docker_image: Image | None = None

        try:
            docker_image = self._client.images.get(tag)
            return
        except ImageNotFound:
            logger.marker("Image not found. Building image...")  # type: ignore[attr-defined]
        except APIError as e:
            logger.critical(f"Error while accessing Docker API: {e.explanation}")
            return

        if docker_image:
            logger.marker("Docker image already exists, skipping build")  # type: ignore[attr-defined]
            return

        self._build_image(tag)

    def _build_image(self, tag: str) -> None:
        """Builds the Docker image from the Dockerfiles in the dockerfile directory"""
        build_args = {"commit_hash": self._pr_data.base_commit}
        repo_name = self._pr_data.repo.lower()
        dockerfile_path = Path("dockerfiles", f"Dockerfile_{repo_name}")
        build_succeeded = False
        try:
            self._client.images.build(
                path=self._project_root.as_posix(),
                tag=tag,
                dockerfile=dockerfile_path.as_posix(),
                buildargs=build_args,
                network_mode="host",
                rm=True,
            )
            build_succeeded = True
            logger.success(  # type: ignore[attr-defined]
                f"Docker image '{tag}' built successfully"
            )
        except BuildError as e:
            log_lines = []
            for chunk in e.build_log:
                if "stream" in chunk:
                    log_lines.append(chunk["stream"].rstrip())
            full_build_log = "\n".join(log_lines)
            logger.critical(f"Build failed for image '{tag}':\n{full_build_log}")
            raise ExecutionError("Docker build failed")
        except APIError as e:
            logger.critical(f"Docker API error: {e}")
            raise ExecutionError("Docker API error")
        except TypeError as e:
            logger.critical(f"Docker Type error: {e}")
            raise ExecutionError(
                "Docker Type error: Check if path or fileobj is specified as args"
            )
        finally:
            if not build_succeeded:
                logger.marker("Cleaning up leftover containers and dangling images...")  # type: ignore[attr-defined]
                for container in self._client.containers.list(all=True):
                    img_str: str = container.image.tags or container.image.id
                    if img_str == "<none>:<none>" or not container.image.tags:
                        try:
                            if container.status == "running":
                                container.stop()
                            container.remove()
                        except APIError as stop_err:
                            logger.error(
                                f"Failed to remove container {container.id[:12]}: {stop_err}"
                            )
                try:
                    dangling = self._client.images.list(filters={"dangling": True})
                    for img in dangling:
                        try:
                            self._client.images.remove(image=img.id, force=True)
                        except APIError as img_err:
                            logger.error(
                                f"Failed to remove image {img.id[:12]}: {img_err}"
                            )
                except APIError as list_err:
                    logger.error(f"Error listing dangling images: {list_err}")

    def run_test_in_container(
        self,
        patch: str,
        tests_to_run: list,
        is_golden_patch: bool,
    ) -> TestResult:
        """
        Creates a container, applies the patch, runs the test, and returns the result.

        Parameters:
            patch (str): Patch to apply
            tests_to_run (list): List of tests to run
            is_test_patch (bool): Flag indicating if the patch is a test patch or a golden code patch

        Returns:
            bool: True if the test has passed, False otherwise
            str: The output from running the test
        """
        container: Container | None = None
        try:
            logger.marker("Creating container...")  # type: ignore[attr-defined]
            container = self._client.containers.create(
                image=self._pr_data.image_tag,
                command="/bin/sh -c 'sleep infinity'",  # keep the container running
                tty=True,  # allocate a TTY for interactive use
                detach=True,
            )
            container.start()
            logger.marker(f"Container {container.short_id} started")  # type: ignore[attr-defined]

            # Create placeholder empty files for PRs that add new files
            self._handle_newly_added_files(patch, container)

            # Add the patch file to the container and apply it
            self._add_file_and_apply_patch_in_container(
                container, patch, is_golden_patch
            )

            logger.marker("Tests to run: %s" % ", ".join(tests_to_run))  # type: ignore[attr-defined]

            test_command: str = (
                "/bin/sh -c 'cd /app/testbed && "
                f"cargo test -- --nocapture " + " ".join(tests_to_run) + "'"
            )
            exec_result = container.exec_run(test_command, stdout=True, stderr=True)
            stdout = exec_result.output.decode()
            test_result = self._evaluate_test(stdout)
            return test_result, stdout

        except ImageNotFound as e:
            logger.critical(f"Docker image not found: {e}")
            raise ExecutionError("Docker image not found")
        except APIError as e:
            logger.critical(f"Docker API error: {e}")
            raise ExecutionError("Docker API error")
        except Exception as e:
            logger.critical(f"Unexpected error: {e}")
            raise ExecutionError("Unexpected Docker error")
        finally:
            # Cleanup
            # os.remove(patch_file_path)
            if container is not None:
                container.stop()
                container.remove()
                logger.info("[*] Container stopped and removed.")

    def _handle_newly_added_files(self, patch: str, container: Container) -> set[str]:
        """Finds and creates files only if their patch chunk starts with '@@ -0,0 +'."""
        new_files: set[str] = set()
        current_file = None
        create_file = False

        for line in patch.splitlines():
            # Detect file changes
            match = re.match(r"^diff --git a/(.+) b/(.+)", line)
            if match:
                current_file = match.group(2)  # Get file path after 'b/'
                create_file = False  # Reset flag for each new file

            # Detect start of a new file
            if line.startswith("@@ -0,0 +"):
                create_file = True  # Mark this file for creation

            # If the file should be created, ensure it exists
            if current_file and create_file:
                new_files.add(current_file)
                logger.marker(f"Creating empty file in Docker: {current_file}")  # type: ignore[attr-defined]

                # Ensure parent directory exists inside the container
                parent_dir = os.path.dirname(current_file)
                if parent_dir:
                    exec_result = container.exec_run(
                        f"mkdir -p {parent_dir}", stdout=True, stderr=True
                    )
                    if exec_result.exit_code != 0:
                        logger.warning(
                            f"Error creating directory: {exec_result.stderr.decode()}"
                        )

                # Create the empty file inside the Docker container
                exec_result = container.exec_run(
                    f"touch {current_file}", stdout=True, stderr=True
                )
                if exec_result.exit_code != 0:
                    logger.warning(
                        f"Error creating file: {exec_result.stderr.decode()}"
                    )

                logger.marker(f"Created empty file in Docker: {current_file}")  # type: ignore[attr-defined]
                create_file = False  # Reset flag after creating

        return new_files

    @staticmethod
    def _add_file_and_apply_patch_in_container(
        container: Container,
        patch: str,
        is_golden_patch: bool = False,
    ) -> None:
        """
        Adds file to Docker container.

        Parameters:
            container (Container): Container to add file to
            patch (str): Patch to add to the container and apply
            is_golden_patch (bool): Flag to indicate if the patch is a golden code patch or not
        """
        # Create a temporary patch file
        with tempfile.NamedTemporaryFile(delete=False, mode="w") as patch_file:
            patch_file.write(patch)
            patch_file_path: str = patch_file.name

        patch_fname: str = ""
        if is_golden_patch:
            patch_fname = "golden_code_patch.diff"
            logger.marker("[+] Applying golden code patch")  # type: ignore[attr-defined]
        else:
            patch_fname: str = "test_patch.diff"
        # Create a tar archive
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode="w") as tar:
            tar.add(patch_file_path, arcname=patch_fname)
        tar_stream.seek(0)
        try:
            # Copy the tar archive to the container
            container.put_archive("/app/testbed", tar_stream.read())
            logger.marker(f"File {patch_file_path} added to container successfully")  # type: ignore[attr-defined]
        except APIError as e:
            logger.critical(f"Docker API error: {e}")
            raise ExecutionError("Docker API error")

        DockerService._apply_patch_in_container(container, patch_fname)

    @staticmethod
    def _apply_patch_in_container(container: Container, patch_fname: str) -> None:
        """
        Applies a patch file inside the Docker container.

        Parameters:
            container (Container): Container to apply the patch in
            patch_fname (str): Name of the patch file inside the container
        """
        logger.marker("[+] Applying patch")  # type: ignore[attr-defined]
        apply_patch_cmd = f"/bin/sh -c 'cd /app/testbed && git apply {patch_fname}'"

        exec_result = container.exec_run(apply_patch_cmd)

        if exec_result.exit_code != 0:
            logger.warning(f"[!] Failed to apply patch: {exec_result.output.decode()}")
            raise ExecutionError()

        logger.info("[+] Patch applied successfully.")

    @staticmethod
    def _evaluate_test(stdout: str) -> bool:
        """
        Evaluates the test result from the stdout.

        Parameters:
            stdout (str): The stdout from running the test command

        Returns:
            bool: True if the test has passed, False otherwise
        """
        logger.info("[+] Test command executed.")
        test_result: bool = False

        # Determine matches that indicate test results
        # Could not compile errors:
        compilation_error_pattern = re.compile(r"could not compile", re.IGNORECASE)
        # Failed tests: test <test_name> ... FAILED
        test_failed_pattern = re.compile(r"test\s+\S+\s+\.\.\.\s+FAILED", re.IGNORECASE)

        compilation_error_matches = compilation_error_pattern.findall(stdout)
        test_failed_matches = test_failed_pattern.findall(stdout)

        if compilation_error_matches or test_failed_matches:
            test_result = False
        else:
            test_result = True

        logger.info(f"[+] Test result: {test_result}")
        return test_result
