from enum import StrEnum


class GitHubEvent(StrEnum):
    PULL_REQUEST = "pull_request"
    ISSUE = "issue"