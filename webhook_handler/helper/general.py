import logging
import os
import shutil
import stat
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def remove_dir(
    path: Path, max_retries: int = 3, delay: float = 0.1, log_success: bool = False
) -> None:
    """
    Helper method to remove a directory.

    Parameters:
        path (Path): The path to the directory to remove
        max_retries (int, optional): The maximum number of times to retry the command
        delay (float, optional): The delay between retries
        log_success (bool, optional): Whether to log the success message
    """

    if not path.exists():
        return

    def on_error(func, path, _) -> None:
        os.chmod(path, stat.S_IWRITE)
        func(path)

    for attempt in range(max_retries):
        try:
            shutil.rmtree(path, onerror=on_error)
            # if log_success: logger.success(f"Directory {path} removed successfully")
            return
        except Exception as e:
            if attempt < max_retries:
                logger.warning(
                    f"Failed attempt {attempt} removing {path}: {e}, retrying in {delay}s"
                )
                time.sleep(delay)
            else:
                pass
                logger.error(
                    f"Final attempt failed removing {path}, must be removed manually: {e}"
                )


def run_command(command: str, cwd: str) -> str | None:
    """
    Helper method to run a command in subprocess.

    Parameters:
        command (str): The command to execute
        cwd (str): The location in which the command should be executed

    Returns:
        str: Output of the command
    """

    result = subprocess.run(
        command, cwd=cwd, shell=True, text=True, capture_output=True
    )
    if result.returncode != 0:
        logger.error(f"Command failed: {command}")
        logger.error(f"stderr: {result.stderr}")
    return result.stdout.strip() if result.returncode == 0 else None


def get_candidate_file(commit_hash: str, filename: str, tmp_repo_dir: str) -> str:
    """
    Finds a fitting test file and its content to inject the newly generated test into.

    Parameters:
        base_commit (str): The base commit used to check out
        patch (str): The golden code patch
        tmp_repo_dir (str): The directory to look for test files in

    Returns:
        str: The name of the test file
        bool: if the file is from the base commit
    """
    current_branch = run_command("git rev-parse --abbrev-ref HEAD", cwd=tmp_repo_dir)
    run_command(f"git checkout {commit_hash}", cwd=tmp_repo_dir)

    file_content = ""
    file_path = Path(tmp_repo_dir, filename)
    if file_path.exists():
        logger.marker(f"File {filename} exists in commit {commit_hash}")  # type: ignore[attr-defined]
        file_content = file_path.read_text(encoding="utf-8")
    else:
        logger.marker(f"File {filename} does not exist in commit {commit_hash}")  # type: ignore[attr-defined]

    run_command(f"git checkout {current_branch}", cwd=tmp_repo_dir)

    return file_content
