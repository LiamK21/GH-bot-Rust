import logging

from webhook_handler.helper import git_diff
from webhook_handler.models import PullRequestFileDiff
from webhook_handler.services.gh_service import GitHubService
from webhook_handler.services.local_diff_service import LocalDiffService

logger = logging.getLogger(__name__)


class PullRequestDiffContext:
    """
    Holds all the PullRequestFileDiffs for one PR and provides common operations.
    """

    def __init__(self, base_commit: str, head_commit: str, gh_service: GitHubService):
        self._gh_service = gh_service
        self._pr_file_diffs: list[PullRequestFileDiff] = []
        raw_files = gh_service.fetch_pr_files()
        for raw_file in raw_files:
            file_name = raw_file["filename"]
            before = gh_service.fetch_file_version(base_commit, file_name)
            after = gh_service.fetch_file_version(head_commit, file_name)
            if before != after:
                self._pr_file_diffs.append(
                    PullRequestFileDiff(file_name, before, after)
                )

    @property
    def source_code_file_diffs(self) -> list[PullRequestFileDiff]:
        return [
            pr_file_diff
            for pr_file_diff in self._pr_file_diffs
            if pr_file_diff.is_source_code_file
        ]

    @property
    def non_source_code_file_diffs(self) -> list[PullRequestFileDiff]:
        return [
            pr_file_diff
            for pr_file_diff in self._pr_file_diffs
            if pr_file_diff.is_non_source_code_file
        ]
        
    @property
    def config_file_diffs(self) -> list[PullRequestFileDiff]:
        return [
            pr_file_diff
            for pr_file_diff in self._pr_file_diffs
            if pr_file_diff.is_config_file
        ]

    @property
    def test_file_diffs(self) -> list[PullRequestFileDiff]:
        return [
            pr_file_diff
            for pr_file_diff in self._pr_file_diffs
            if pr_file_diff.is_test_file
        ]

    @property
    def has_at_least_one_source_code_file(self) -> bool:
        return len(self.source_code_file_diffs) > 0

    @property
    def has_at_least_one_test_file(self) -> bool:
        return len(self.test_file_diffs) > 0

    @property
    def fulfills_requirements(self) -> bool:
        return (
            self.has_at_least_one_source_code_file
            and not self.has_at_least_one_test_file
            and len(self.non_source_code_file_diffs) == 0
        )

    @property
    def golden_code_patch(self) -> str:
        return (
            "\n\n".join(
                pr_file_diff.unified_code_diff()
                for pr_file_diff in self.source_code_file_diffs
            )
            + "\n\n"
        )

    def get_absolute_file_path(self, file_path: str) -> str | None:
        return next(
            (
                pr_file_diff.name
                for pr_file_diff in self.source_code_file_diffs
                if pr_file_diff.passed_path_matches_name(file_path)
            ),
            None,
        )

    @property
    def get_patch_and_modified_functions(self) -> tuple[str, list[str]]:
        patch = self.golden_code_patch
        modified_functions: list[str] = []
        for pr_file_diff in self.source_code_file_diffs:
            modified_functions.extend(pr_file_diff.get_modified_functions(patch))
        return patch, modified_functions

    def get_updated_golden_code_patch(self, filename: str, content: str) -> str:
        """
        Returns the golden code patch for all files except the passed one.
        It uses the provided content for the passed file instead of the original "after" content.

        Returns:
            str: Updated diff between before and after code files
        """
        patch: list[str] = []
        for pr_file_diff in self.source_code_file_diffs + self.config_file_diffs:
            if filename == pr_file_diff.name:
                diff = git_diff.unified_diff_with_function_context(
                    pr_file_diff.before,
                    content,
                    pr_file_diff.name,
                )
            else:
                diff = pr_file_diff.unified_code_diff()
            patch.append(diff)
        return "\n\n".join(patch) + "\n\n"

    def get_specific_file_diff(self, filename: str) -> PullRequestFileDiff | None:
        """
        Returns the PullRequestFileDiff for a specific file if it exists.

        Parameters:
            filename (str): The name of the file to look for

        Returns:
            PullRequestFileDiff | None: The file diff or None if not found
        """
        return next(
            (
                pr_file_diff
                for pr_file_diff in self.source_code_file_diffs
                if pr_file_diff.name == filename
            ),
            None,
        )

    @classmethod
    def from_local_git(
        cls,
        base_commit: str,
        local_service: LocalDiffService,
    ) -> "PullRequestDiffContext":
        """
        Create a PullRequestDiffContext from the local git repository.
        Args:
            base_commit: The HEAD commit to compare against
            local_service: LocalDiffService instance

        Returns:
            PullRequestDiffContext: Instance with file diffs from local git (working dir vs HEAD)
        """
        instance = cls.__new__(cls)
        instance._gh_service = None 
        instance._pr_file_diffs = []

        changed_files = local_service.get_changed_files()

        for filepath in changed_files:
            try:
                before = local_service.get_file_content(base_commit, filepath)

                after = local_service.get_working_directory_content(filepath)

                # Only add if there's an actual difference
                if before != after:
                    instance._pr_file_diffs.append(
                        PullRequestFileDiff(filepath, before, after)
                    )
                    logger.debug(f"Added file diff for: {filepath}")
            except Exception as e:
                logger.warning(f"Failed to process file {filepath}: {e}")
                continue

        logger.info(
            f"Created PullRequestDiffContext with {len(instance._pr_file_diffs)} file diffs"
        )
        return instance