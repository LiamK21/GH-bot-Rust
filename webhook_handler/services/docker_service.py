import io
import json
import logging
import os
import re
import shlex
import tarfile
import tempfile
from pathlib import Path

import docker
from docker.errors import APIError, BuildError, ImageNotFound
from docker.models.containers import Container
from docker.models.images import Image

from webhook_handler.helper.custom_errors import *
from webhook_handler.models import PullRequestData, PullRequestFileDiff

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
                            print(
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
        test_patch: str,
        tests_to_run: list,
        file_diff: PullRequestFileDiff,
        golden_code_patch: str | None = None,
    ) -> TestResult:
        """
        Creates a container, applies the patch, runs the test, and returns the result.

        Parameters:
            test_patch (str): Patch to apply to the model test
            tests_to_run (list): List of tests to run
            added_test_file (str): Path to the file to add to the added tests
            golden_code_patch (str): Patch content for source code

        Returns:
            bool: True if the test has passed, False otherwise
            str: The output from running the test
        """
        patch_file_path: str = ""
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
            self._handle_newly_added_files(test_patch, container)

            #### A) Test patch (Always)
            patch_result = self._add_file_and_apply_patch_in_container(
                container, test_patch
            )
            if isinstance(patch_result, tuple):
                return patch_result
            patch_file_path = patch_result
            if golden_code_patch is not None:
                #### B) Model patch (Only in post-PR code)
                patch_result = self._add_file_and_apply_patch_in_container(
                    container, golden_code_patch, is_golden_patch=True
                )
                if isinstance(patch_result, tuple):
                    return patch_result

                patch_file_path = patch_result

            logger.marker("Tests to run: %s" % ", ".join(tests_to_run))  # type: ignore[attr-defined]
            # Run the test command
            coverage_report_separator: str = "COVERAGE_REPORT_STARTING_HERE"
            test_command: str = (
                "/bin/sh -c 'cd /app/testbed && "
                f"cargo test -- --nocapture " + " ".join(tests_to_run) + " ; "
                "coverage report -m > coverage_report.txt && "
                f"echo '{coverage_report_separator}' && "
                "cat coverage_report.txt'"
            )
            exec_result = container.exec_run(test_command, stdout=True, stderr=True)
            stdout_output_all = exec_result.output.decode()
            stdout = ""
            test_result: bool = False
            try:  # TODO: fix, find a better way to handle the "test-not-ran" error
                stdout, coverage_report = stdout_output_all.split(
                    coverage_report_separator
                )
            except:
                test_result = False
                logger.warning(
                    "Internal error: docker command failed with: %s" % stdout_output_all
                )
                return test_result, stdout_output_all
            logger.info("[+] Test command executed.")

            # Determine PASS/FAIL from output
            if (
                "= FAILURES =" in stdout or "= ERRORS =" in stdout
            ):  # if at least one test failed, we consider it a failure
                test_result = (
                    False  # because we may run one AI test with many developer tests
                )
            else:
                test_result = True

            logger.info(f"[+] Test result: {test_result}")
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
            os.remove(patch_file_path)
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
        container: Container, patch: str, is_golden_patch: bool = False
    ) -> TestResult | str:
        """
        Adds file to Docker container.

        Parameters:
            container (Container): Container to add file to
            file_path (str): Path to the file to add to the container
            file_content (str | bytes, optional): Content to add to the file
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
            logger.marker(f"File {file_path} added to container successfully")  # type: ignore[attr-defined]
        except APIError as e:
            logger.critical(f"Docker API error: {e}")
            raise ExecutionError("Docker API error")

        # Apply the patch inside the container
        apply_patch_cmd = f"/bin/sh -c 'cd /app/testbed && git apply {patch_fname}'"
        exec_result = container.exec_run(apply_patch_cmd)

        if exec_result.exit_code != 0:
            logger.info(f"[!] Failed to apply patch: {exec_result.output.decode()}")
            return False, exec_result.output.decode()

        logger.info("[+] Patch applied successfully.")
        return patch_file_path
