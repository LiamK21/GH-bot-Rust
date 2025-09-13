import json
import os
import re
import sys
import time
from enum import StrEnum
from pathlib import Path
from typing import Literal, cast

import requests
from dotenv import load_dotenv

load_dotenv()

type Repo = Literal["grcov", "rust-code-analysis", "glean", "neqo"]

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
GITHUB_HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
}
BUGZILLA_GET_BUG_URL = "https://bugzilla.mozilla.org/rest/bug"
BUGZILLA_BUGS: list[int] = []
BUGZILLA_BUGS_DICT = dict() 
BUGZILLA_BUGS_REQUIRED = 50
BUGZILLA_PR = {}
BUGZILLA_HEADERS = {
    "Accept": "application/json",
}


def _fetch_github_data(url: str) -> dict:
    """
    Fetches data from GitHub API.

    Parameters:
        url (str): GitHub URL.

    Returns:
        dict: Data.
    """

    response = requests.get(url, headers=GITHUB_HEADERS)
    if response.status_code == 403 and "X-RateLimit-Reset" in response.headers:
        print("[*] Sleeping...")
        reset_time = int(response.headers["X-RateLimit-Reset"])
        wait_time = reset_time - int(time.time()) + 1
        time.sleep(max(wait_time, 1))
        return _fetch_github_data(url)
    response.raise_for_status()
    return response.json()

def _fetch_bugzilla_data() -> dict:
    """
    Fetches data from Bugzilla API.

    Parameters:
        bug_id (str): Bugzilla id.

    Returns:
        dict: Data.
    """
    bugs_str = ",".join(str(bug) for bug in BUGZILLA_BUGS)
    print("[*] Sleeping for 60 seconds before Bugzilla API call...")
    time.sleep(60)  # to avoid hitting rate limits
    url = f"https://bugzilla.mozilla.org/rest/bug?id={bugs_str}&include_fields=id,summary,component,description"
    response = requests.get(url, headers=BUGZILLA_HEADERS)
    if response.status_code == 403 and "X-RateLimit-Reset" in response.headers:
        print("[*] Sleeping...")
        reset_time = int(response.headers["X-RateLimit-Reset"])
        wait_time = reset_time - int(time.time()) + 1
        time.sleep(max(wait_time, 1))
        return _fetch_bugzilla_data()
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


def _get_linked_bugzilla_data(pr_description: str, is_pre_processing: bool) -> str:
    bugzilla_url_pattern = r"\bhttps://bugzilla\.mozilla\.org/show_bug\.cgi\?id=(\d+)\b"
    bugzilla_bug_id_pattern = r"\bbug\s+(\d+)\b"
    bugzilla_url_matches: list[str] = re.findall(
        bugzilla_url_pattern, pr_description, re.IGNORECASE
    )
    bugzilla__bug_id_matches: list[str] = re.findall(
        bugzilla_bug_id_pattern, pr_description, re.IGNORECASE
    )
    all_matches = bugzilla_url_matches + bugzilla__bug_id_matches
    
    if all_matches:
        for bug_id in all_matches:
            bug_id = int(bug_id)
            if not bug_id:
                continue
            
            if is_pre_processing:
                BUGZILLA_BUGS.append(bug_id)
                if len(BUGZILLA_BUGS) >= BUGZILLA_BUGS_REQUIRED:
                    _add_bugzilla_issues()
                return "BUGZILLA"
            else:
                # retrieve from already fetched bugs
                linked_issue_description = BUGZILLA_BUGS_DICT.get(bug_id)
                if linked_issue_description:
                    del(BUGZILLA_BUGS_DICT[bug_id])
                    return linked_issue_description
    return ""


def _get_linked_data(pr_title: str, pr_description: str, repo: Repo, is_pre_processing: bool = False) -> str:
    """
    Checks and fetches a linked issue.

    Parameters:
        pr_title (str): Title of the PR.
        pr_description (str): Description of the PR.

    Returns:
        str: The linked issue title and description
    """
    issue_description = f"{pr_title} {pr_description}"
    # Glean often links to bugs in Bugzilla, not GitHub issues
    if repo == "glean":
        linked_issue_description = _get_linked_bugzilla_data(issue_description, is_pre_processing)
        if linked_issue_description:
            return linked_issue_description
                
    issue_pattern = r"#(\d+)"
    url_pattern = rf"\bhttps://github\.com/mozilla/{re.escape(repo)}/issues/(\d+)\b"
        
    # issue_pattern = (
    #     r"\b(?:Closes|Fixes|Resolves)\s+#(\d+)\b|\(?\b(?:bug|issue)\b\s+(\d+)\)?"
    # )
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


def _add_bugzilla_issues() -> None:
    """
    Fetches Bugzilla issues and stores them in the BUGZILLA_BUG_DICT.
    """
    bug_data = _fetch_bugzilla_data()
    if "bugs" in bug_data and len(bug_data["bugs"]) > 0:
        for bug in bug_data["bugs"]:
            bug_id: int = bug.get("id")
            if not bug_id:
                print(f"[!] Invalid Bugzilla bug ID: {bug_id}")
                continue
            
            BUGZILLA_BUGS.remove(bug_id)
            component: str = bug.get("component", "")
            # We are only interested in Glean bugs
            if not "glean" in component.lower():
                continue
            # Bug ID should be numeric
            summary, descrption =  bug.get("summary", ""), bug.get("description", "")
            # Both summary and description should not be empty
            if not summary and not descrption:
                continue
            BUGZILLA_BUGS_DICT[int(bug_id)] =  summary + "\n" + descrption


def _get_github_issue(number: int, repo: Repo) -> str | None:
    """
    Fetches a GitHub issue.

    Parameters:
        number (int): The number of the issue

    Returns:
        str | None: The GitHub issue title and description
    """

    url = f"{API_URL}/{OWNER}/{repo}/issues/{number}"
    response = requests.get(url, headers=GITHUB_HEADERS)
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


def pre_process_glean_prs(pr_list: dict):
    copied_pr_list = pr_list.copy()
    for pr in copied_pr_list:
        pr_number, is_valid_pr = _validate_pr(pr)
        if not is_valid_pr:
            cast(list, pr_list).remove(pr)
            continue
        res = _get_linked_data(pr["title"], pr["body"], "glean", True)
        
        if not res:
            print(f"[!] Neither GitHub nor Bugzilla linked issue for PR #{pr_number}\n")
            cast(list, pr_list).remove(pr)
            continue
        
        if res == "BUGZILLA":
            print(f"[*] linked issue belongs to Bugzilla")
            cast(list, pr_list).remove(pr)
            BUGZILLA_PR[pr_number] = pr

def process_pr(curr_pr: dict, repo: Repo) -> bool | str:
    """
    Processes PR fetched from the GitHub PR list.
    The repository cannot be glean.
    
    Parameters:
        curr_pr (dict): PR data.

    Returns:
        bool: True if PR fulfills requirements, False otherwise.
    """
    pr_number, is_valid_pr = _validate_pr(curr_pr)
    if not is_valid_pr:
        return False

    # Requirement #2: PR must have linked issue
    if not _get_linked_data(curr_pr["title"], curr_pr["body"], repo):
        print(f"[!] No linked issue for PR #{pr_number}\n")
        return False

    files = _fetch_pr_files(pr_number, repo)
    file_types: list[FileType] = []
    for f in files:
        filename: str = f["filename"]
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
    if FileType.NON_SRC in file_types:
        print(f"[!] Non-source code files in PR #{pr_number}\n")
        return False

    current_payload = {
        "action": "opened",
        "number": pr_number,
        "pull_request": curr_pr,
        "repository": {"owner": {"login": OWNER}, "name": repo},
    }

    # Requirement #4: PR must modify at least one .rs file
    if FileType.SRC in file_types:
        if FileType.TEST in file_types:
            _save_pr_amp(current_payload, repo)
            return "amp"
        else:
            _save_pr(current_payload, repo)
            return "src"
    else:
        print(f"[!] No .rs changes in source code in PR #{pr_number}\n")
        return False


def _validate_pr(curr_pr: dict) -> tuple[int, bool]:
    pr_number = curr_pr["number"]
    if not isinstance(pr_number, int):
        return 0, False
    print(f"[*] Processing PR #{pr_number}...")
    
    is_valid: bool = True

    # Requirement #1: PR must have action OPENED or MERGED (=CLOSED and MERGED_AT)
    if not (
        curr_pr["state"] == "open"
        or (curr_pr["state"] == "closed" and curr_pr["merged_at"] is not None)
    ):
        print(f"[!] PR #{pr_number} was closed but not merged\n")
        is_valid = False
        
    return pr_number, is_valid

def _validate_passed_args(args: list[str]) -> bool:
    if len(args) == 0:
        print("Usage: python scrape_pr.py [repository, repository...]")
        print("Available repositories: grcov, rust-code-analysis, glean, neqo")
        sys.exit(1)
   
    valid_repos = ["grcov", "rust-code-analysis", "glean", "neqo"]
    for arg in args:
        if arg not in valid_repos:
            print(f"[!] Invalid repository: {arg}")
            print("Usage: python scrape_pr.py [repository, repository...]")
            print("Available repositories: grcov, rust-code-analysis, glean, neqo")
            sys.exit(1)
    return True
    
    


################## Main Logic ###################
valid_payloads = 0
valid_payloads_amp = 0
page = 1


if __name__ == "__main__":
    repos: list[Repo] = []

    cli_args = sys.argv[1:]
    _validate_passed_args(cli_args)
    
    if "grcov" in cli_args:
        repos.append("grcov")
    if "rust-code-analysis" in cli_args:
        repos.append("rust-code-analysis")
    if "glean" in cli_args:
        repos.append("glean")
    if "neqo" in cli_args:
        repos.append("neqo")
    
    
    for repo in repos:
        curr_valid_payloads = 0
        curr_valid_payloads_amp = 0
        print(f"[*] Scraping PRs from {repo}...")
        while (valid_payloads) < SCRAPE_TARGET:
            pr_list = _fetch_pr_list(page, repo)
            if not pr_list:
                print("[*] No PRs to process")
                break
            if repo == "glean":
                print("[*] Pre-processing the PR list for repository glean")
                pre_process_glean_prs(pr_list)
            
            
            for pr in pr_list:
                res = process_pr(pr, repo)
                if res and (valid_payloads) >= SCRAPE_TARGET:
                    break
                curr_valid_payloads += 1 if res == "src" else 0
                curr_valid_payloads_amp += 1 if res == "amp" else 0
                        
            page += 1
            break
        
        if repo == "glean":
            for pr_number, pr in BUGZILLA_PR.items():
                res = process_pr(pr, repo)
                if res and (valid_payloads) >= SCRAPE_TARGET:
                    break
                curr_valid_payloads += 1 if res == "src" else 0
                curr_valid_payloads_amp += 1 if res == "amp" else 0
        

        print(f"[+] Found {curr_valid_payloads} valid {repo} payloads")
        print(f"[+] Found {curr_valid_payloads_amp} valid {repo} payloads with tests")
        valid_payloads += curr_valid_payloads
        valid_payloads_amp += curr_valid_payloads_amp
    
    print(f"[+] Found {valid_payloads} valid total payloads")
    print(f"[+] Found {valid_payloads_amp} valid total payloads with tests")
