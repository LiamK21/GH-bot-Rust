import logging
import re

from groq import Groq
from openai import OpenAI

from webhook_handler.helper import templates
from webhook_handler.models import LLM, PipelineInputs, PromptType
from webhook_handler.services.config import Config

logger = logging.getLogger(__name__)


class LLMHandler:
    """
    Used to interact with LLMs.
    """

    def __init__(self, config: Config, data: PipelineInputs) -> None:
        self._pipeline_inputs = data
        self._pr_data = data.pr_data
        self._pr_diff_ctx = data.pr_diff_ctx
        self._openai_client = OpenAI(api_key=config.openai_key)
        self._groq_client = Groq(api_key=config.groq_key)

    def build_prompt(self, prompt_type: PromptType, previous_test: str = "", failure_reason: str = "") -> str:
        # previous_test is only called for non-initial prompts
        # failure_reason is only called for LINTING_ISSUE, ASSERTION_ERROR
        """
        Builds prompt with available data.
        
        Parameters:
            prompt_type (PromptType): Type of prompt to build

        Returns:
            str: Prompt
        """

        linked_issue: str = (
            f"Issue:\n<issue>\n{self._pipeline_inputs.problem_statement}\n</issue>\n\n"
        )

        diff, funcs = self._pr_diff_ctx.get_patch_and_modified_functions

        patch = f"Patch:\n<patch>\n{diff}\n</patch>\n\n"
        funcs = f"Function signatures\n<Signatures>\n{"\n\n".join(funcs)}\n</Signatures>\n\n"


        instructions = templates.get_instructions_template(self._pr_data.repo, prompt_type)
        failed_output = ("<output>\n" + failure_reason + "\n</output>\n\n") if failure_reason else ""

        return (
            f"{templates.GUIDELINES}"
            f"{linked_issue}"
            f"{patch}"
            f"{previous_test}"
            f"{failed_output}"
            f"{funcs}"
            f"{instructions}"
            f"{templates.EXAMPLE_TEST_STRUCTURE}"
        )

    def query_model(self, prompt: str, model: LLM, temperature: float = 0.0) -> str:
        """
        Query a model and return its results.

        Parameters:
            prompt (str): Prompt to ask for
            model (LLM): Model to use
            temperature (float, optional): Temperature to use. Defaults to 0.0

        Returns:
            str: Response from model
        """

        try:
            if model == LLM.GPT4o:
                response = self._openai_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                )
                result = response.choices[0].message.content
                assert isinstance(result, str), "Expected response to be a string"
                return result.strip()
            elif model == LLM.GPTo3_MINI:  # does not accept temperature
                response = self._openai_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                )
                result = response.choices[0].message.content
                assert isinstance(result, str), "Expected response to be a string"
                return result.strip()
            elif model == LLM.LLAMA:
                completion = self._groq_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=700,
                    temperature=temperature,
                )
                result = completion.choices[0].message.content
                assert isinstance(result, str), "Expected response to be a string"
                return result.strip()
            elif model == LLM.QWEN3:
                response = self._groq_client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an experienced software tester specializing in developing regression tests. Follow the user's instructions for generating a regression test. The output format is STRICT: do all your reasoning in the beginning, but the end of your output should ONLY contain rust code, i.e., NO natural language after the code.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                )
                result = response.choices[0].message.content
                assert isinstance(result, str), "Expected response to be a string"
                return result.strip()
            else:
                return ""
        except:
            return ""

    def postprocess_response(self, response: str) -> tuple[str, list[str], str] | None:
        """
        Postprocess the response from the LLM.

        Parameters:
            response (str): Response from the LLM

        Returns:
            str: Filename
            list[str]: List of imports
            str: Postprocessed response
        """
        cleaned_response = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL)

        # Check for <NO> tag
        no_test_generated = re.search(r"<NO>", cleaned_response)
        if no_test_generated:
            logger.info("Model determined no test is needed.")
            logger.marker("=============== Test Generation Finished ==============")  # type: ignore[attr-defined]
            return None

        # Extract filename
        filename_pattern = re.compile(r"<Filename>(.*?)</Filename>", re.DOTALL)
        filename_match = filename_pattern.search(cleaned_response)
        if not filename_match:
            raise Exception("Filename not found in response")
        filename: str = filename_match.group(1).strip()

        # Extract imports
        imports_pattern = re.compile(r"<imports>(.*?)</imports>", re.DOTALL)
        imports_match = imports_pattern.search(cleaned_response)
        imports: list[str] = []
        if imports_match:
            imports = [
                line.strip()
                for line in imports_match.group(1).strip().splitlines()
                if line.strip()
            ]

        # Extract test code
        code_pattern = re.compile(r"<Rust>(.*?)</Rust>", re.DOTALL)
        code_match = code_pattern.search(cleaned_response)
        if not code_match:
            raise Exception("Test code not found in response")
        cleaned_test = code_match.group(1).strip()

        return filename, imports, self._adjust_function_indentation(cleaned_test)

    @staticmethod
    def _adjust_function_indentation(function_code: str) -> str:
        """
        Adjusts the indentation of a rust function so that the function definition
        has no leading spaces, and the internal code indentation is adjusted accordingly.

        Parameters:
            function_code (str): The Javascript function

        Returns:
            str: The adjusted function code
        """

        lines = function_code.splitlines()

        if not lines:
            return ""

        # find the leading spaces of the first non-empty line
        first_non_empty_line = next(line for line in lines if line.strip())
        leading_spaces = len(first_non_empty_line) - len(first_non_empty_line.lstrip())

        return "\n".join(
            [line[leading_spaces:] if line.strip() else "" for line in lines]
        )
