import re

from groq import Groq
from openai import OpenAI

from webhook_handler.models import LLM, PipelineInputs
from webhook_handler.services.config import Config


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

    def build_prompt(
        self,
        # include_golden_code: bool,
        # sliced: bool,
        # include_pr_summary: bool,
        # include_predicted_test_file: bool,
        # test_filename: str,
        # test_file_content_sliced: str,
    ) -> str:
        """
        Builds prompt with available data.

        Parameters:
            include_golden_code (bool): Whether to include golden code
            sliced (bool): Whether to slice source code or not
            include_pr_summary (bool): Whether to include pull request title & description
            include_predicted_test_file (bool): Whether to include test file
            test_filename (str): The filename of the test file
            test_file_content_sliced (str): The content of the test file

        Returns:
            str: Prompt
        """

        guidelines: str = (
            "Before you begin:\n"
            "- Keep going until the job is completely solved — don’t stop halfway.\n"
            "- If you’re unsure about the behavior, reread the provided patch carefully; do not hallucinate.\n"
            "- Plan your approach before writing code by reflecting on whether the test truly fails before and passes after.\n\n"
        )

        linked_issue: str = (
            f"Issue:\n<issue>\n{self._pipeline_inputs.problem_statement}\n</issue>\n\n"
        )

        # golden_code_patch = self._pr_diff_ctx.golden_code_patch
        # src_code_file_diffs = self._pr_diff_ctx.source_code_file_diffs
        diff, funcs = self._pr_diff_ctx.get_patch_and_modified_functions

        patch = f"Patch:\n<patch>\n{diff}\n</patch>\n\n"
        funcs = f"Function signatures\n<Signatures>\n{"\n\n".join(funcs)}\n</Signatures>\n\n"

        # available_imports = f"Imports:\n<imports>\n{available_packages}\n{available_relative_imports}\n</imports>\n\n"

        # golden_code = ""
        # if include_golden_code:
        #     code_filenames = self._pr_diff_ctx.code_names
        #     if sliced:
        #         code = self._pipeline_inputs.code_sliced
        #         golden_code += "Code:\n<code>\n"
        #         for (f_name, f_code) in zip(code_filenames, code):
        #             golden_code += ("File:\n"
        #                             f"{f_name}\n"
        #                             f"{f_code}\n")
        #         golden_code += "</code>\n\n"
        #     else:
        #         code = self._pr_diff_ctx.code_before  # whole code
        #         code = [self._add_line_numbers(x) for x in code]
        #         golden_code += "Code:\n<code>\n"
        #         for (f_name, f_code) in zip(code_filenames, code):
        #             golden_code += ("File:\n"
        #                             f"{f_name}\n"
        #                             f"{f_code}\n")
        #         golden_code += "</code>\n\n"

        instructions: str = (
            f"You are a software tester at {self._pr_data.repo} and your are reviewing the above <patch> for the above <issue>\n"
            "Identify whether a unit test is needed.\n"
            "If there is no test needed, return <NO>.\n"
            "If a test is needed, your task is:\n"
            "1. Write exactly one rust test `#[test]fn test_...(){...}` block. Do NOT wrap the test inside a 'mod tests' block.\n"
            "2. Your test must fail on the code before the patch, and pass after, hence "
            "the test will verify that the patch resolves the issue.\n"
            "3. The test must be self-contained and to-the-point.\n"
            "4. All 'use' declarations must be inside a <imports>...</imports> block.\n "
            "Use `use super::<function name> for the function under test.\n"
            "5. To help you write the test, <Signatures> contains all modified function's:\n"
            "- name\n"
            "- parameters\n"
            "- Return type (assume '()' if empty)\n"
            "6. Return only the filename, the use statements, and rust test (no comments or explanations).\n\n"
        )

        example: str = (
            "Here is an example structure:\n"
            "<Filename> ... </Filename>\n"
            "<imports> ... </imports>\n"
            "'''rust\n"
            "#[test]\n"
            "fn test_<describe_behavior>() {\n"
            "  <initialize required variables>;\n"
            "  <define expected variable>;\n"
            "  <generate actual variables>;\n"
            "  <compare expected with actual>;\n"
            "};"
            "'''rust\n\n"
        )

        # test_code: str = ""
        # if include_predicted_test_file:
        #     if test_file_content_sliced:
        #         test_code += f"Test file:\n<test_file>\nFile:\n{test_filename}\n{test_file_content_sliced}\n</test_file>\n\n"
        #         instructions = ("Your task:\n"
        #                         f"You are a software tester at {self._pr_data.repo}.\n"
        #                         "1. Examine the existing test file. You may reuse any imports, helpers or setup blocks it already has.\n"
        #                         "2. Write exactly one javascript test `it(\"...\", async () => {...})` block.\n"
        #                         "3. Your test must fail on the code before the patch, and pass after, hence "
        #                         "the test will verify that the patch resolves the issue.\n"
        #                         "4. The test must be self-contained and to-the-point.\n"
        #                         "5. If you need something new use only the provided imports (respect the paths "
        #                         "exactly how they are given) by importing dynamically for compatibility with Node.js "
        #                         "— no new dependencies. "
        #                         f"{use_pdf}"
        #                         "6. Return only the javascript code for the new `it(...)` block (no comments or explanations).\n\n")
        #     else:
        #         instructions = ("Your task:\n"
        #                         f"You are a software tester at {self._pr_data.repo}.\n"
        #                         "1. Create a new test file that includes:\n"
        #                         "   - All necessary imports (use only the provided imports and respect the "
        #                         "paths exactly how they are given) — no new dependencies. "
        #                         f"{use_pdf}"
        #                         "   - A top-level `describe(\"<brief suite name>\", () => {{ ... }})`.\n"
        #                         "   - Exactly one `it(\"...\", async () => {{ ... }})` inside that block.\n"
        #                         "2. The `it` test must fail on the code before the patch, and pass after, hence "
        #                         "the test will verify that the patch resolves the issue.\n"
        #                         "3. Keep the file self-contained — no external dependencies beyond those you import here.\n"
        #                         "4. Return only the full JavaScript file contents (no comments explanations).\n\n")

        #         example = ("Example structure:\n"
        #                    "import { example } from \"../../src/core/example.js\";\n\n"
        #                    "describe(\"<describe purpose>\", () => {\n"
        #                    "  it(\"<describe behavior>\", async () => {\n"
        #                    "    <initialize required variables>;\n"
        #                    "    <define expected variable>;\n"
        #                    "    <generate actual variables>;\n"
        #                    "    <compare expected with actual>;\n"
        #                    "  });\n"
        #                    "});\n\n")

        # pr_summary = ""
        # if include_pr_summary:
        #     pr_summary += f"PR summary:\n<pr_summary>\n{
        #         self._pr_data.title
        #     }\n{
        #         self._pr_data.description
        #     }\n</pr_summary>\n\n"

        return (
            f"{guidelines}"
            f"{linked_issue}"
            f"{patch}"
            f"{funcs}"
            # f"{available_imports}"
            # f"{golden_code}"
            # f"{test_code}"
            # f"{pr_summary}"
            f"{instructions}"
            f"{example}"
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
            elif model == LLM.DEEPSEEK:
                response = self._groq_client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an experienced software tester specializing in developing regression tests. Follow the user's instructions for generating a regression test. The output format is STRICT: do all your reasoning in the beginning, but the end of your output should ONLY contain javascript code, i.e., NO natural language after the code.",
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
        if cleaned_response.strip() == "<NO>":
            return None
        lines = cleaned_response.splitlines()
        # Extract filename
        filename, cleaned_response = lines[0].strip(), lines[1:]
        if not filename.startswith("<Filename>") or not filename.endswith(
            "</Filename>"
        ):
            raise Exception("Filename not found in response")
        filename = filename.lstrip("<Filename>").rstrip("</Filename>").strip()

        # Extract imports
        imports: list[str] = []
        imports_starting_idx = next(
            (
                idx
                for idx, val in enumerate(cleaned_response)
                if val.strip() == "<imports>"
            ),
            None,
        )
        imports_ending_idx = next(
            (
                idx
                for idx, val in enumerate(cleaned_response)
                if val.strip() == "</imports>"
            ),
            None,
        )
        if imports_starting_idx is not None and imports_ending_idx is not None:
            imports.extend(
                val
                for val in cleaned_response[
                    imports_starting_idx + 1 : imports_ending_idx
                ]
                if val.strip()
            )
            cleaned_test = "\n".join(cleaned_response[imports_ending_idx + 1 :])
        else:
            cleaned_test = "\n".join(cleaned_response)

        # Extract test
        cleaned_test = cleaned_test.replace("'''rust", "")
        cleaned_test = cleaned_test.replace("```rust", "")
        cleaned_test = cleaned_test.replace("'''", "")
        cleaned_test = cleaned_test.lstrip("\n")
        cleaned_test = self._clean_descriptions(cleaned_test)
        return filename, imports, self._adjust_function_indentation(cleaned_test)

    @staticmethod
    def _clean_descriptions(function_code: str) -> str:
        """
        Cleans the call expression descriptions used in the generated test by removing every non-letter character and multiple whitespaces.

        Parameters:
            function_code (str): Function code to clean

        Returns:
            str: Cleaned function code
        """

        pattern = re.compile(
            r"\b(?P<ttype>describe|it)\(\s*"  # match describe( or it(
            r'(?P<quote>[\'"])\s*'  # capture opening quote
            r"(?P<name>.*?)"  # capture the raw name
            r"(?P=quote)\s*,",  # match the same closing quote, then comma
            flags=re.DOTALL,
        )

        def clean_test_name(match):
            test_type = match.group("ttype")
            q = match.group("quote")
            name = match.group("name")
            # strip out anything but A–Z or a–z
            cleaned = re.sub(r"[^A-Za-z ]", "", name)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            return f"{test_type}({q}{cleaned}{q},"

        return pattern.sub(clean_test_name, function_code)

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
