import json
import os
import re
import time
from enum import StrEnum
from pathlib import Path
from typing import Literal

import requests
from dotenv import load_dotenv

load_dotenv()

type Repo = Literal["grcov", "rust-code-analysis"]

class FileType(StrEnum):
    TEST = "test"
    SRC = "src"
    NON_SRC = "non-src"
    OTHER = "other"
    UNCHANGED = "unchanged"

############### Global Variables ################
SCRAPE_TARGET = 500
OUTPUT_DIR = Path(Path.cwd(), "scrape_mocks")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "code_only").mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "code_test").mkdir(parents=True, exist_ok=True)

API_URL = "https://api.github.com/repos"
OWNER = "mozilla"
HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
}


def _fetch_github_data(url: str) -> dict:
    """
    Fetches data from GitHub API.

    Parameters:
        url (str): GitHub URL.

    Returns:
        dict: Data.
    """

    response = requests.get(url, headers=HEADERS)
    if response.status_code == 403 and "X-RateLimit-Reset" in response.headers:
        print("[*] Sleeping...")
        reset_time = int(response.headers["X-RateLimit-Reset"])
        wait_time = reset_time - int(time.time()) + 1
        time.sleep(max(wait_time, 1))
        return _fetch_github_data(url)
    response.raise_for_status()
    return response.json()


def _fetch_pr_list(curr_page: int, repo: Repo) -> dict:
    """
    Fetches list of PRs on current page.

    Parameters:
        curr_page (int): Current page number.

    Returns:
        dict: PR list.
    """
    list_url = (
        f"{API_URL}/{OWNER}/{repo}/pulls"
        f"?state=all&sort=created&direction=desc"
        f"&per_page=100&page={curr_page}"
    )
    return _fetch_github_data(list_url)


def _fetch_pr_files(pr_number: int, repo: Repo) -> dict:
    """
    Fetches PR files.

    Parameters:
        pr_number (int): PR number.

    Returns:
        dict: All files modified in that PR.
    """ 

    url = f"{API_URL}/{OWNER}/{repo}/pulls/{pr_number}/files"
    return _fetch_github_data(url)


def _get_linked_data(pr_title: str, pr_description: str, repo: Repo) -> str:
    """
    Checks and fetches a linked issue.

    Parameters:
        pr_title (str): Title of the PR.
        pr_description (str): Description of the PR.

    Returns:
        str: The linked issue title and description
    """
    issue_pattern = r"#(\d+)"
    url_pattern = rf"\bhttps://github\.com/mozilla/{re.escape(repo)}/issues/(\d+)\b"
        
    # issue_pattern = (
    #     r"\b(?:Closes|Fixes|Resolves)\s+#(\d+)\b|\(?\b(?:bug|issue)\b\s+(\d+)\)?"
    # )
    issue_description = f"{pr_title} {pr_description}"
    issue_matches: list[str] = re.findall(
            issue_pattern, issue_description, re.IGNORECASE
        )
    url_matches: list[str] = re.findall(
            url_pattern, issue_description, re.IGNORECASE
        )
    all_matches = issue_matches + url_matches

    for match in all_matches:
        issue_nr_str = match[0] or match[1]
        if not issue_nr_str:
            continue

        issue_nr = int(issue_nr_str)
        linked_issue_description = _get_github_issue(issue_nr, repo)
        if linked_issue_description:
            return linked_issue_description

    return ""


def _get_github_issue(number: int, repo: Repo) -> str | None:
    """
    Fetches a GitHub issue.

    Parameters:
        number (int): The number of the issue

    Returns:
        str | None: The GitHub issue title and description
    """

    url = f"{API_URL}/{OWNER}/{repo}/issues/{number}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        issue_data = response.json()
        if not "pull_request" in issue_data:
            return "\n".join(
                value for value in (issue_data["title"], issue_data["body"]) if value
            )

    return None


def _is_test_file(filename: str) -> bool:
    """
    Determines whether the given file is an integration test file or not

    Parameters:
        filename (str): The name of the file

    Returns:
        bool: True if it is a test file, False otherwise
    """

    is_in_test_folder = False
    parts = filename.split("/")

    # at least one folder in the dir path starts with test
    for part in parts[:-1]:
        if part.startswith("test"):
            is_in_test_folder = True
            break

    if is_in_test_folder and parts[-1].endswith("rs"):
        return True
    return False


def _is_src_code_file(filename) -> bool:
    """
    Determines whether the given file is a source code file or not

    Parameters:
        filename (str): The name of the file

    Returns:
        bool: True if it is a source code file, False otherwise
    """

    is_in_src_folder = False
    parts: list[str] = filename.split("/")

    # at least one folder in the dir path starts with src
    for part in parts[:-1]:
        if part.startswith("src"):
            is_in_src_folder = True
            break

    if is_in_src_folder and parts[-1].endswith(".rs"):
        return True
    return False


def _save_pr(payload, repo: Repo) -> None:
    """
    Saves PR data in the 'code_only' directory.

    Parameters:
        payload (dict): PR data.
    """

    pr_number = payload["pull_request"]["number"]
    filename = f"{repo}_{pr_number}.json"
    path = OUTPUT_DIR / "code_only" / filename
    if not path.exists():
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"[+] Saved PR #{pr_number} to {path}\n")
    else:
        print(f"[!] PR #{pr_number} at {path} already exists\n")


def _save_pr_amp(payload, repo: Repo) -> None:
    """
    Saves PR data in the 'code_test' directory.

    Parameters:
        payload (dict): PR data.
    """

    pr_number = payload["pull_request"]["number"]
    filename = f"{repo}_{pr_number}.json"
    path = OUTPUT_DIR / "code_test" / filename
    if not path.exists():
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"[+] Saved PR #{pr_number} to {path}\n")
    else:
        print(f"[!] PR #{pr_number} at {path} already exists\n")


def _process_pr(curr_pr: dict, repo: Repo) -> bool:
    """
    Processes PR fetched from the GitHub PR list.

    Parameters:
        curr_pr (dict): PR data.

    Returns:
        bool: True if PR fulfills requirements, False otherwise.
    """
    if repo == "grcov":
        global valid_grcov_payloads
        global valid_grcov_payloads_amp
    else:
        global valid_rust_code_analysis_payloads
        global valid_rust_code_analysis_payloads_amp

    pr_number = curr_pr["number"]
    print(f"[*] Processing PR #{pr_number}...")

    # Requirement #1: PR must have action OPENED or MERGED (=CLOSED and MERGED_AT)
    if not (
        curr_pr["state"] == "open"
        or (curr_pr["state"] == "closed" and curr_pr["merged_at"] is not None)
    ):
        print(f"[!] PR #{pr_number} was closed but not merged\n")
        return False

    # Requirement #2: PR must have linked issue
    if not _get_linked_data(curr_pr["title"], curr_pr["body"], repo):
        print(f"[!] No linked issue for PR #{pr_number}\n")
        return False

    files = _fetch_pr_files(pr_number, repo)
    file_types = []
    for f in files:
        filename = f["filename"]
        if "patch" in f:
            if _is_test_file(filename):
                file_types.append(FileType.TEST)
            elif _is_src_code_file(filename):
                file_types.append(FileType.SRC)
            elif filename.endswith(".rs"):
                file_types.append(FileType.NON_SRC)
            else:
                file_types.append(FileType.OTHER)
        else:
            file_types.append(FileType.UNCHANGED)

    # Perhaps we can relax this requirement to at least one src file
    # Requirement #3: All .rs files modified in PR must be source code files
    if "non-src" in file_types:
        print(f"[!] Non-source code files in PR #{pr_number}\n")
        return False

    current_payload = {
        "action": "opened",
        "number": pr_number,
        "pull_request": curr_pr,
        "repository": {"owner": {"login": OWNER}, "name": repo},
    }

    # Requirement #4: PR must modify at least one .rs file
    if "src" in file_types:
        if "test" in file_types:
            valid_grcov_payloads_amp += 1 if repo == "grcov" else 0
            valid_rust_code_analysis_payloads_amp += 1 if repo == "rust-code-analysis" else 0
            _save_pr_amp(current_payload, repo)
        else:
            valid_grcov_payloads_amp += 1 if repo == "grcov" else 0
            valid_rust_code_analysis_payloads_amp += 1 if repo == "rust-code-analysis" else 0
            _save_pr(current_payload, repo)
        return True
    else:
        print(f"[!] No .rs changes in source code in PR #{pr_number}\n")
        return False


################## Main Logic ###################
#valid_payloads = 0
valid_grcov_payloads = 0
valid_rust_code_analysis_payloads = 0
#valid_payloads_amp = 0
valid_grcov_payloads_amp = 0
valid_rust_code_analysis_payloads_amp = 0
page = 1


if __name__ == "__main__":
    while (valid_grcov_payloads + valid_rust_code_analysis_payloads) < SCRAPE_TARGET:
        pr_list_grcov = _fetch_pr_list(page, "grcov")
        pr_list_rust_code_analysis = _fetch_pr_list(page, "rust-code-analysis")
        if not pr_list_grcov and not pr_list_rust_code_analysis:
            print("[*] No PRs to process")
            break

        for pr in pr_list_grcov:
            if _process_pr(pr, "grcov") and (valid_grcov_payloads + valid_rust_code_analysis_payloads) >= SCRAPE_TARGET:
                break
        print("Processing rust-code-analysis PRs...")
        for pr in pr_list_rust_code_analysis:
            if _process_pr(pr, "rust-code-analysis") and (valid_grcov_payloads + valid_rust_code_analysis_payloads) >= SCRAPE_TARGET:
                break

        page += 1

    print(f"[+] Found {valid_grcov_payloads} valid grcov payloads")
    print(f"[+] Found {valid_rust_code_analysis_payloads} valid rust-code-analysis payloads")
    print(f"[+] Found {valid_grcov_payloads_amp} valid grcov payloads with integration test files\n")
    print(f"[+] Found {valid_rust_code_analysis_payloads_amp} valid rust-code-analysis payloads with integration test files\n")
