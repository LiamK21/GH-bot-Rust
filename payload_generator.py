import os
import re
import subprocess
import time
from enum import StrEnum
from pathlib import Path
from typing import cast

import requests
from dotenv import load_dotenv

from webhook_handler.helper import general

load_dotenv()

MOZILLA_API_URL = "https://api.github.com/repos/mozilla"
GITHUB_HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
}
BUGZILLA_GET_BUG_URL = "https://bugzilla.mozilla.org/rest/bug"
BUGZILLA_PR = {}
BUGZILLA_HEADERS = {
    "Accept": "application/json",
}


class FileType(StrEnum):
    TEST = "test"
    SRC = "src"
    NON_SRC = "non-src"
    OTHER = "other"
    UNCHANGED = "unchanged"


class PayloadGenerator:
    def __init__(self, repo: str, pr_number: int | None = None, issue_number: int | None = None):
        self.repo = repo
        self.pr_number = pr_number
        self.issue_number = issue_number

    def generate_payload(self) -> dict:
        """
        Generates a payload for the given PR after validating it.
        
        Returns:
            dict: The payload if PR is valid.
            
        Raises:
            ValueError: If the repository is unsupported or PR fails validation.
        """
        if (self.pr_number is None and self.issue_number is None):
            raise ValueError("PR number and Issue number must be provided")
        
        if self.repo not in ["grcov", "rust-code-analysis", "glean"]:
            raise ValueError(f"Unsupported repository: {self.repo}")

        if self.pr_number is not None:
            return self.generate_pr_payload()
        else:
            return self.generate_issue_payload()

    def generate_pr_payload(self) -> dict:
        assert self.pr_number is not None
        
        # Fetch PR data from GitHub
        pr_data = self._fetch_github_data(
            f"{MOZILLA_API_URL}/{self.repo}/pulls/{self.pr_number}"
        )
        pr_data = cast(dict, pr_data)


        # Validate the PR
        if not self._validate_pr(pr_data):
            raise ValueError(f"PR #{self.pr_number} failed validation checks")

        # Check for linked issue (GitHub or Bugzilla)
        if not self._has_linked_issue(pr_data):
            raise ValueError(f"PR #{self.pr_number} has no linked issue")

        # Validate PR files
        if not self._validate_pr_files():
            raise ValueError(f"PR #{self.pr_number} files do not meet requirements")

        # Generate and return payload
        payload = {
            "action": "opened",
            "number": self.pr_number,
            "pull_request": pr_data,
            "repository": {"owner": {"login": "mozilla"}, "name": self.repo},
        }
        return payload

    def generate_issue_payload(self) -> dict:
        """
        Generates a payload for the given issue using local git state.
        
        Returns:
            dict: The payload mimicking PR structure for issue-based generation.
            
        Raises:
            ValueError: If the issue fails validation or git operations fail.
        """
        assert self.issue_number is not None
        issue_data = {}
        glean_is_bugzilla_linked = False
        # For Glean, check Bugzilla first
        if self.repo == "glean":
            bug_data = self._fetch_bugzilla_data(self.issue_number)
            if "bugs" in bug_data and len(bug_data["bugs"]) > 0:
                glean_is_bugzilla_linked = True
                issue_data = {"number": bug_data["bugs"][0].get("id", self.issue_number),
                              "title": bug_data["bugs"][0].get("summary", ""),
                              "body": bug_data["bugs"][0].get("description", ""),
                              "url": bug_data["bugs"][0].get("url", ""),}
        
        if not glean_is_bugzilla_linked:
        # Fetch issue data from GitHub
            issue_data = self._fetch_github_data(
                f"{MOZILLA_API_URL}/{self.repo}/issues/{self.issue_number}"
            )
            issue_data = cast(dict, issue_data)
            # Validate the issue
            if not self._validate_issue(issue_data):
                raise ValueError(f"Issue #{self.issue_number} failed validation checks")
            


        print(f"[*] Issue #{self.issue_number} passed validation checks")
        # Build PR-like data structure from local git state
        issue_payload = self._build_issue_payload_from_local_git(issue_data)

        # Generate and return payload
        payload = {
            "action": "opened",
            "number": self.issue_number,
            "issue": issue_payload,
            "repository": {"owner": {"login": "mozilla"}, "name": self.repo},
        }
        return payload

    def _validate_pr(self, pr_data: dict) -> bool:
        """
        Validates that PR is either open or merged.
        
        Requirement #1: PR must have action OPENED or MERGED (=CLOSED and MERGED_AT)
        
        Parameters:
            pr_data (dict): PR data from GitHub API.
            
        Returns:
            bool: True if PR is valid, False otherwise.
        """
        if not isinstance(self.pr_number, int):
            return False

        if not (
            pr_data["state"] == "open"
            or (pr_data["state"] == "closed" and pr_data["merged_at"] is not None)
        ):
            print(f"[!] PR #{self.pr_number} was closed but not merged")
            return False

        return True
    
    def _validate_issue(self, issue_data: dict) -> bool:
        """
        Validates that PR is either open or merged.
        
        Requirement #1: PR must have action OPENED or MERGED (=CLOSED and MERGED_AT)
        
        Parameters:
            pr_data (dict): PR data from GitHub API.
            
        Returns:
            bool: True if PR is valid, False otherwise.
        """
        if not isinstance(self.issue_number, int):
            return False

        if not (
            issue_data["state"] == "open"
            or (issue_data["state"] == "closed" and issue_data["closed_at"] is not None)
        ):
            print(f"[!] PR #{self.issue_number} was closed but not merged")
            return False

        return True

    def _has_linked_issue(self, pr_data: dict) -> bool:
        """
        Checks if PR has a linked GitHub issue or Bugzilla bug.
        
        Requirement #2: PR must have linked issue
        
        Parameters:
            pr_data (dict): PR data from GitHub API.
            
        Returns:
            bool: True if linked issue exists, False otherwise.
        """
        title = pr_data.get("title", "")
        body = pr_data.get("body", "")
        issue_description = f"{title} {body}"

        # For Glean, check Bugzilla first
        if self.repo == "glean":
            if self._get_linked_bugzilla_issue(issue_description):
                return True

        # Check for GitHub issues
        if self._get_linked_github_issue(issue_description):
            return True

        print(f"[!] No linked issue for PR #{self.pr_number}")
        return False

    def _get_linked_bugzilla_issue(self, issue_description: str) -> bool:
        """
        Checks for linked Bugzilla bug.
        
        Parameters:
            issue_description (str): Combined PR title and body.
            
        Returns:
            bool: True if Bugzilla bug found, False otherwise.
        """
        bugzilla_url_pattern = r"\bhttps://bugzilla\.mozilla\.org/show_bug\.cgi\?id=(\d+)\b"
        bugzilla_bug_id_pattern = r"\bbug\s+(\d+)\b"
        
        bugzilla_url_matches = re.findall(
            bugzilla_url_pattern, issue_description, re.IGNORECASE
        )
        bugzilla_bug_id_matches = re.findall(
            bugzilla_bug_id_pattern, issue_description, re.IGNORECASE
        )
        
        all_matches = bugzilla_url_matches + bugzilla_bug_id_matches
        
        if all_matches:
            for bug_id in all_matches:
                bug_id = int(bug_id)
                if bug_id:
                    # Verify the bug exists
                    try:
                        bug_data = self._fetch_bugzilla_data(bug_id)
                        if "bugs" in bug_data and len(bug_data["bugs"]) > 0:
                            return True
                    except:
                        continue
        
        return False

    def _get_linked_github_issue(self, issue_description: str) -> bool:
        """
        Checks for linked GitHub issue.
        
        Parameters:
            issue_description (str): Combined PR title and body.
            
        Returns:
            bool: True if GitHub issue found, False otherwise.
        """
        issue_pattern = r"#(\d+)"
        url_pattern = rf"\bhttps://github\.com/mozilla/{re.escape(self.repo)}/issues/(\d+)\b"
        
        issue_matches = re.findall(issue_pattern, issue_description, re.IGNORECASE)
        url_matches = re.findall(url_pattern, issue_description, re.IGNORECASE)
        all_matches = issue_matches + url_matches

        for match in all_matches:
            issue_nr_str = match if isinstance(match, str) else (match[0] or match[1])
            if not issue_nr_str:
                continue

            issue_nr = int(issue_nr_str)
            if self._get_github_issue(issue_nr):
                return True

        return False

    def _get_github_issue(self, number: int) -> bool:
        """
        Fetches a GitHub issue to verify it exists.
        
        Parameters:
            number (int): The number of the issue.
            
        Returns:
            bool: True if issue exists and is not a PR, False otherwise.
        """
        url = f"{MOZILLA_API_URL}/{self.repo}/issues/{number}"
        response = requests.get(url, headers=GITHUB_HEADERS)
        if response.status_code == 200:
            issue_data = response.json()
            if "pull_request" not in issue_data:
                return True
        return False

    def _validate_pr_files(self) -> bool:
        """
        Validates that PR files meet requirements.
        
        Requirement #3: All .rs files modified in PR must be source code files
        Requirement #4: PR must modify at least one .rs file
        
        Returns:
            bool: True if files are valid, False otherwise.
        """
        files = self._fetch_pr_files()
        file_types = []

        for f in files:
            filename = f["filename"]
            if "patch" in f:
                if self._is_test_file(filename):
                    file_types.append(FileType.TEST)
                elif self._is_src_code_file(filename):
                    file_types.append(FileType.SRC)
                elif filename.endswith(".rs"):
                    file_types.append(FileType.NON_SRC)
                else:
                    file_types.append(FileType.OTHER)
            else:
                file_types.append(FileType.UNCHANGED)

        # Requirement #3: All .rs files modified in PR must be source code files
        if FileType.NON_SRC in file_types:
            print(f"[!] Non-source code files in PR #{self.pr_number}")
            return False

        # Requirement #4: PR must modify at least one .rs file
        if FileType.SRC not in file_types:
            print(f"[!] No .rs changes in source code in PR #{self.pr_number}")
            return False

        return True

    def _validate_issue_files(self, files: list[str]) -> bool:
        """
        Validates that PR files meet requirements.
        
        Requirement #3: All .rs files modified in PR must be source code files
        Requirement #4: PR must modify at least one .rs file
        
        Returns:
            bool: True if files are valid, False otherwise.
        """
        file_types = []

        for filename in files:
                if self._is_test_file(filename):
                    file_types.append(FileType.TEST)
                elif self._is_src_code_file(filename):
                    file_types.append(FileType.SRC)
                elif filename.endswith(".rs"):
                    file_types.append(FileType.NON_SRC)
                else:
                    file_types.append(FileType.OTHER)

        # Requirement #3: All .rs files modified in PR must be source code files
        if FileType.NON_SRC in file_types:
            print(f"[!] Non-source code files in PR #{self.pr_number}")
            return False

        # Requirement #4: PR must modify at least one .rs file
        if FileType.SRC not in file_types:
            print(f"[!] No .rs changes in source code in PR #{self.pr_number}")
            return False

        return True

    def _build_issue_payload_from_local_git(self, issue_data: dict) -> dict:
        """
        Build a PR-like data structure from local git repository state.
        Compares uncommitted changes in working directory against HEAD.
        
        Parameters:
            issue_data (dict): Issue data from GitHub API
            
        Returns:
            dict: PR-like data structure with local git information
        """
        # Get current working directory (should be the repo)
        repo_path = Path.cwd()
    
        # Get current HEAD commit and branch
        head_commit = self._get_current_commit(repo_path)
        head_branch = self._get_current_branch(repo_path)
        
        # Get uncommitted changes (working directory vs HEAD)
        changed_files = general.get_changed_files_from_git(repo_path)
        
        if not self._validate_issue_files(changed_files):
            raise ValueError(f"Issue #{self.issue_number} files do not meet requirements")
        
        # Build PR-like structure
        # Both base and head use HEAD since we're comparing working directory vs HEAD
        issue_payload = {
            "number": issue_data.get("number"),
            "title": issue_data.get("title"),
            "body": issue_data.get("body"),
            "url": issue_data.get("url"),
            "diff_url": "",  # Not applicable for local mode
            "state": issue_data.get("state"),
            "base": {
                "ref": head_branch,
                "sha": head_commit,
            },
            "head": {
                "ref": head_branch,
                "sha": head_commit,
            },
        }
        
        return issue_payload
    
    def _get_current_commit(self, repo_path: Path) -> str:
        """Get the current HEAD commit hash."""
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    
    def _get_current_branch(self, repo_path: Path) -> str:
        """Get the current branch name."""
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    
    def _is_test_file(self, filename: str) -> bool:
        """
        Determines whether the given file is a test file.
        
        Parameters:
            filename (str): The name of the file.
            
        Returns:
            bool: True if it is a test file, False otherwise.
        """
        is_in_test_folder = False
        parts = filename.split("/")

        # At least one folder in the dir path starts with test
        for part in parts[:-1]:
            if part.startswith("test"):
                is_in_test_folder = True
                break

        if is_in_test_folder and parts[-1].endswith("rs"):
            return True
        return False

    def _is_src_code_file(self, filename: str) -> bool:
        """
        Determines whether the given file is a source code file.
        
        Parameters:
            filename (str): The name of the file.
            
        Returns:
            bool: True if it is a source code file, False otherwise.
        """
        is_in_src_folder = False
        parts = filename.split("/")

        # At least one folder in the dir path starts with src
        for part in parts[:-1]:
            if part.startswith("src"):
                is_in_src_folder = True
                break

        if is_in_src_folder and parts[-1].endswith(".rs"):
            return True
        return False

    def _fetch_pr_files(self) -> list[dict]:
        """
        Fetches PR files.
        
        Returns:
            list[dict]: All files modified in that PR.
        """
        url = f"{MOZILLA_API_URL}/{self.repo}/pulls/{self.pr_number}/files"
        data = self._fetch_github_data(url)
        # GitHub API returns a list for files endpoint
        return data if isinstance(data, list) else [data]

    def _fetch_github_data(self, url: str) -> dict | list[dict]:
        """
        Fetches data from GitHub API.

        Parameters:
            url (str): GitHub URL.

        Returns:
            dict | list[dict]: Data from GitHub API (can be dict or list depending on endpoint).
        """
        response = requests.get(url, headers=GITHUB_HEADERS)
        if response.status_code == 403 and "X-RateLimit-Reset" in response.headers:
            print("[*] Sleeping...")
            reset_time = int(response.headers["X-RateLimit-Reset"])
            wait_time = reset_time - int(time.time()) + 1
            time.sleep(max(wait_time, 1))
            return self._fetch_github_data(url)
        response.raise_for_status()
        return response.json()

    def _fetch_bugzilla_data(self, bug_nr: int) -> dict:
        """
        Fetches data from Bugzilla API.

        Parameters:
            bug_nr (int): Bugzilla bug ID.

        Returns:
            dict: Data.
        """
        url = f"https://bugzilla.mozilla.org/rest/bug?id={bug_nr}&include_fields=id,summary,component,description,url,"
        response = requests.get(url, headers=BUGZILLA_HEADERS)
        if response.status_code == 403 and "X-RateLimit-Reset" in response.headers:
            print("[*] Sleeping...")
            reset_time = int(response.headers["X-RateLimit-Reset"])
            wait_time = reset_time - int(time.time()) + 1
            time.sleep(max(wait_time, 1))
            return self._fetch_bugzilla_data(bug_nr)
        response.raise_for_status()
        
        return response.json()
    