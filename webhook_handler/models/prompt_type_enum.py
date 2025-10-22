from enum import StrEnum


class PromptType(StrEnum):
    """
    Determines the type of prompt used to query the model.
    """

    INITIAL = "INITIAL"
    LINTING_ISSUE = "LINTING_ISSUE"
    PASS_TO_PASS = "PASS_TO_PASS"
    COMPILATION_ERROR = "COMPILATION_ERROR"
    ASSERTION_ERROR = "ASSERTION_ERROR"
