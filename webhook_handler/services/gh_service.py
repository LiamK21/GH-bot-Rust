import logging
import re
import subprocess
import time

import requests

from webhook_handler.helper.custom_errors import *
from webhook_handler.models import PullRequestData
from webhook_handler.services import Config

GH_API_URL = "https://api.github.com/repos"
GH_RAW_URL = "https://raw.githubusercontent.com"

logger = logging.getLogger(__name__)


class GitHubService:
    def __init__(self, config: Config, pr_data: PullRequestData | None = None) -> None:
        self._config = config
        self._pr_data = pr_data

    def fetch_pr_files(self) -> dict:
        """
        Fetches all files of a pull request.

        Returns:
            dict: All raw files
        """
        if self._pr_data is None:
            raise ValueError("PR data is required for fetch_pr_files()")

        url = f"{GH_API_URL}/{self._pr_data.owner}/{self._pr_data.repo}/pulls/{self._pr_data.number}/files"
        response = requests.get(url, headers=self._config.HEADER)
        if response.status_code == 403 and "X-RateLimit-Reset" in response.headers:
            reset_time = int(response.headers["X-RateLimit-Reset"])
            wait_time = reset_time - int(time.time()) + 1
            logger.warning(f"Rate limit exceeded. Waiting for {wait_time} seconds...")
            time.sleep(max(wait_time, 1))
            return self.fetch_pr_files()

        response.raise_for_status()
        return response.json()

    def get_linked_data(self) -> str | None:
        """
        Checks and fetches a linked issue.

        Returns:
            str: The linked issue title and description
        """
        if self._pr_data is None:
            raise ValueError("PR data is required for get_linked_data()")
        
        owner = self._pr_data.owner
        repo = self._pr_data.repo
        pr_description = self._pr_data.description
        pr_title = self._pr_data.title
        issue_description: str = f"{pr_title} {pr_description}"

        if repo == "glean":
            logger.marker(f"Checking for linked Bugzilla issues in PR #{self._pr_data.number}") # type: ignore[attr-defined]
            linked_issue_description = self._get_bugzilla_issue(issue_description)
            if linked_issue_description:
                return linked_issue_description
            
        # The regex patterns look for instances of "#123" or direct links in the PR title and description.
        # It will only capture the issue/bug number.
        issue_pattern = r"#(\d+)"
        url_pattern = rf"\bhttps://github\.com/{re.escape(owner)}/{re.escape(repo)}/issues/(\d+)\b"

        issue_matches: list[str] = re.findall(
            issue_pattern, issue_description, re.IGNORECASE
        )
        url_matches: list[str] = re.findall(
            url_pattern, issue_description, re.IGNORECASE
        )
        all_matches = issue_matches + url_matches
        for match in all_matches:
            issue_nr = int(match)
            if not issue_nr:
                continue

            linked_issue_description = self._get_github_issue(issue_nr)
            if linked_issue_description:
                return linked_issue_description
        return None

    def fetch_file_version(self, commit: str, file_name: str) -> str:
        """
        Fetches the version of a file at a specific commit.

        Parameters:
            commit (str): Commit hash
            file_name (str): File name
            get_bytes (bool, optional): Get bytes instead of text

        Returns:
            str | bytes: File contents
        """
        if self._pr_data is None:
            raise ValueError("PR data is required for fetch_file_version()")

        url = f"{GH_RAW_URL}/{self._pr_data.owner}/{self._pr_data.repo}/{commit}/{file_name}"
        try:
            response = requests.get(url, headers=self._config.HEADER, timeout=10)
        except requests.Timeout:
            logger.error(f"Request timed out while fetching file: {file_name}")
            return ""
        if response.status_code == 200:
            return response.text  # File exists
        return ""  # File most likely does not exist (anymore)

    def clone_repo(self) -> None:
        """
        Clones a GitHub repository.
        """
        if self._pr_data is None:
            raise ValueError("PR data is required for clone_repo()")
        if self._config.cloned_repo_dir is None:
            raise DataMissingError(
                "cloned_repo_dir", "None", "Path to cloned repository directory not set"
            )
        logger.info(
            f"Cloning repository https://github.com/{self._pr_data.owner}/{self._pr_data.repo}.git"
        )

        try:
            _ = subprocess.run(
                [
                    "git",
                    "clone",
                    f"https://github.com/{self._pr_data.owner}/{self._pr_data.repo}.git",
                    self._config.cloned_repo_dir,
                ],
                capture_output=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            logger.critical(f"Cloning failed: {e.stderr.decode().strip()}")
            raise ExecutionError("Git cloning failed")

        logger.success(f"Cloning successful")  # type: ignore[attr-defined]

    def fetch_issue_description(self, owner: str, repo: str, number: int) -> str | None:
        """
        Fetches a GitHub issue description (public method).

        Parameters:
            owner (str): Repository owner
            repo (str): Repository name
            number (int): The number of the issue

        Returns:
            str | None: The GitHub issue title and description
        """
        if repo == "glean":
            logger.marker(f"Checking for linked Bugzilla Glean issue in PR #{self._pr_data.number}") # type: ignore[attr-defined]
            linked_issue_description = self._fetch_bugzilla_data(number)
            if linked_issue_description:
                return linked_issue_description 
        
        
        url = f"{GH_API_URL}/{owner}/{repo}/issues/{number}"
        try:
            response = requests.get(url, headers=self._config.HEADER, timeout=10)
        except requests.Timeout:
            logger.error(f"Request timed out while fetching issue: #{number}")
            return None

        if response.status_code == 200:
            issue_data: dict = response.json()

            if "pull_request" in issue_data:
                logger.warning(
                    f"Linked issue #{number} is a pull request, not an issue"
                )
                return None

            return "\n".join(
                value for value in (issue_data["title"], issue_data["body"]) if value
            )

        logger.error("No GitHub issue found")
        return None

    def _get_github_issue(self, number: int) -> str | None:
        """Fetches a GitHub issue"""
        if self._pr_data is None:
            raise ValueError("PR data is required for _get_github_issue()")
        return self.fetch_issue_description(
            self._pr_data.owner, self._pr_data.repo, number
        )

    def _get_bugzilla_issue(self, issue_description: str) -> str | None:
        bugzilla_url_pattern = r"\bhttps://bugzilla\.mozilla\.org/show_bug\.cgi\?id=(\d+)\b"
        bugzilla_bug_id_pattern = r"\bbug\s+(\d+)\b"
        bugzilla_url_matches: list[str] = re.findall(
        bugzilla_url_pattern, issue_description, re.IGNORECASE
        )
        bugzilla__bug_id_matches: list[str] = re.findall(
        bugzilla_bug_id_pattern, issue_description, re.IGNORECASE
        )
        all_matches = bugzilla_url_matches + bugzilla__bug_id_matches
        if all_matches:
            for bug_id in all_matches:
                bug_id = int(bug_id)
                if not bug_id:
                    continue
                
                return self._fetch_bugzilla_data(bug_id)
        return ""
    
    def _fetch_bugzilla_data(self, bug_id: int) -> str:
        """
        Fetches data from Bugzilla API.

        Parameters:
            bug_id (str): Bugzilla id.

        Returns:
            dict: Data.
        """
        url = f"https://bugzilla.mozilla.org/rest/bug?id={bug_id}&include_fields=id,summary,component,description"
        response = requests.get(url, headers={"Accept": "application/json"}, timeout=10)
        if response.status_code == 403 and "X-RateLimit-Reset" in response.headers:
            logger.info("[*] Sleeping...")
            reset_time = int(response.headers["X-RateLimit-Reset"])
            wait_time = reset_time - int(time.time()) + 1
            time.sleep(max(wait_time, 1))
            return self._fetch_bugzilla_data(bug_id)
        response.raise_for_status()
        bug_data: dict = response.json()
        
        if "bugs" in bug_data and len(bug_data["bugs"]) == 1:
            bug = bug_data["bugs"][0]
            bug_bug_id: int = bug.get("id")
            if not bug_bug_id:
                print(f"[!] Invalid Bugzilla bug ID: {bug_bug_id}")
                return ""
            
            component: str = bug.get("component", "")
            # We are only interested in Glean bugs
            if not "glean" in component.lower():
                return ""
            summary, descrption =  bug.get("summary", ""), bug.get("description", "")
            # Both summary and description should not be empty
            if not summary and not descrption:
                return ""
            return summary + "\n" + descrption
        
        return response.json()


    def add_comment_to_pr(self, comment) -> tuple[int, dict]:
        """
        Adds a comment to the pull request.

        Parameters:
            comment (str): Comment to add

        Returns:
            int: Status code
            dict: The response data
        """
        if self._pr_data is None:
            raise ValueError("PR data is required for add_comment_to_pr()")

        url = f"{GH_API_URL}/{self._pr_data.owner}/{self._pr_data.repo}/issues/{self._pr_data.number}/comments"
        data = {"body": comment}
        response = requests.post(url, json=data, headers=self._config.HEADER)
        return response.status_code, response.json()
