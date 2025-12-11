import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class LocalDiffService:
    """
    Service for performing git operations on a local repository.
    """

    def __init__(self, repo_path: Path | str):
        self.repo_path = Path(repo_path)
        if not self._is_git_repo():
            raise ValueError(f"{repo_path} is not a valid git repository")

    def _is_git_repo(self) -> bool:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.returncode == 0
        except subprocess.CalledProcessError:
            return False

    def get_changed_files(self) -> list[str]:
        """
        Get list of files with uncommitted changes in working directory (including untracked files).
        
        Returns:
            list[str]: List of file paths that have uncommitted changes
        """
        # Get uncommitted changes
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        files = set(f for f in result.stdout.strip().splitlines() if f)

        # Get untracked files
        untracked_result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        
        untracked_files = [f for f in untracked_result.stdout.strip().splitlines() if f]
        files.update(untracked_files)

        return list(files)

    def get_file_content(self, commit: str, filepath: str) -> str:
        """
        Get the content of a file at a specific commit.

        Args:
            commit: Commit hash or ref 
            filepath: Relative file path

        Returns:
            str: Content of the file at the specified commit

        """
        try:
            result = subprocess.run(
                ["git", "show", f"{commit}:{filepath}"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            # File might be new (doesn't exist in base commit)
            if "does not exist" in e.stderr or "exists on disk" in e.stderr:
                return ""
            raise

    def get_working_directory_content(self, filepath: str) -> str:
        """
        Get the current content of a file in the working directory.
        This includes uncommitted changes.

        Args:
            filepath: Path to the file relative to repo root

        Returns:
            str: Content of the file in working directory
        """
        full_path = self.repo_path / filepath
        if not full_path.exists():
            return ""
        return full_path.read_text()