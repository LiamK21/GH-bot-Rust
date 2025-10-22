from dataclasses import dataclass


@dataclass
class LLMResponse:
    """
    Holds all data about the LLM's response.
    """

    filename: str
    imports: list[str]
    test_code: str
    test_name: str
    curr_llm_cal: int
