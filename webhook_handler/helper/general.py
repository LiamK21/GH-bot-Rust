import logging
import os
import re
import shutil
import stat
import subprocess
import time
from pathlib import Path

from webhook_handler.models import GitHubEvent, LLMResponse

logger = logging.getLogger(__name__)


def get_changed_files_from_git(
    repo_path: Path | str
) -> list[str]:
    """
    Get list of changed files between two git references.
    
    Parameters:
        repo_path (Path | str): Path to the git repository
        
    Returns:
        list[str]: List of changed file paths relative to repo root
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        
        files = result.stdout.strip().split("\n")
        return [f for f in files if f]
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Error getting changed files: {e.stderr}")
        return []


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


def get_candidate_file(commit_hash: str, filename: str, tmp_repo_dir: str, gh_event: GitHubEvent) -> str:
    """
    Gets file content at a specific commit without modifying working directory.

    Parameters:
        commit_hash (str): The commit hash to get file from
        filename (str): The file path relative to repo root
        tmp_repo_dir (str): The directory of the git repository
        gh_event (GitHubEvent): The type of GitHub event (PR or Issue)

    Returns:
        str: The file content at the specified commit, or empty string if file doesn't exist
    """
    file_content = ""
    
    if gh_event == GitHubEvent.ISSUE:
        # For issues, use git show to get file from HEAD without touching working directory
        # This preserves uncommitted changes (the fix) in the working directory
        try:
            result = subprocess.run(
                ["git", "show", f"{commit_hash}:{filename}"],
                cwd=tmp_repo_dir,
                capture_output=True,
                text=True,
                check=True,
            )
            file_content = result.stdout
            logger.marker(f"File {filename} exists in commit {commit_hash}")  # type: ignore[attr-defined]
        except subprocess.CalledProcessError:
            logger.marker(f"File {filename} does not exist in commit {commit_hash}")  # type: ignore[attr-defined]
    else:
        # For PRs, checkout the commit (original behavior)
        current_branch = run_command("git rev-parse --abbrev-ref HEAD", cwd=tmp_repo_dir)
        run_command(f"git checkout {commit_hash}", cwd=tmp_repo_dir)
        
        file_path = Path(tmp_repo_dir, filename)
        if file_path.exists():
            logger.marker(f"File {filename} exists in commit {commit_hash}")  # type: ignore[attr-defined]
            file_content = file_path.read_text(encoding="utf-8")
        else:
            logger.marker(f"File {filename} does not exist in commit {commit_hash}")  # type: ignore[attr-defined]
        
        run_command(f"git checkout {current_branch}", cwd=tmp_repo_dir)

    return file_content

def retrieve_output_errors(out: str) -> str:
    """
    Retrieves only the linting errors from the linting output.

    Parameters:
        out (str): The full linting output
    Returns:
        str: The linting errors only
    """
    idx: int = 0
    line: str = ""
    result: list[str] = []
    out_lines = out.splitlines()    
    while idx < len(out_lines):
        line = out_lines[idx].strip()
        if line.startswith("error") and "could not compile" not in line: 
            startIdx = idx
            # Capture all lines related to this error
            while idx < len(out_lines) and not out_lines[idx].strip() == "":
                idx += 1
            result.append("\n".join(out_lines[startIdx:idx]))
        else:
            idx += 1
            
    return "\n\n".join(result)

def retrieve_output_test_failure(out: str) -> str:
    out_lines = out.splitlines()
    idx: int = 0
    failure_reason: list[str] = []
    running_test_pattern = r"running \d+ test"
    
    while idx < len(out_lines):
        line = out_lines[idx].strip()
        match = re.match(running_test_pattern, line)
        if match:
            startIdx = idx
            idx += 2 # Skip the following newline
            while idx < len(out_lines) and not out_lines[idx].strip() == "":
                idx += 1
            failure_reason.append("\n".join(out_lines[startIdx:idx]))
        else:
            idx += 1
    
    return "\n\n".join(failure_reason)

def build_response_test(llm_response: LLMResponse) -> str:
    filename_block = f"\n<Filename>{llm_response.filename}</Filename>\n"
    imports_block = f"<imports>{"\n".join(llm_response.imports)}</imports>\n"
    test_block = f"<Rust>{llm_response.test_code}\n</Rust>\n"
    return f"<TEST>{filename_block + imports_block + test_block}</TEST>\n\n"