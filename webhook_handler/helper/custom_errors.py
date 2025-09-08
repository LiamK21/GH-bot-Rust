from typing import Literal


class DataMissingError(Exception):
    """Raised whenever required data is missing"""

    def __init__(
        self, field: str, value: str, message: str = "Required data is missing"
    ) -> None:
        super().__init__(f"{message}: {field} = {value}")


class ExecutionError(Exception):
    """Raised whenever an error occurs during execution"""

    def __init__(self, message: str = "An error occurred during execution") -> None:
        super().__init__(message)
