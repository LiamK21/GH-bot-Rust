from webhook_handler.models.prompt_type_enum import PromptType

COMMENT_TEMPLATE = """Hi! 🤖 The test below is automatically generated and could serve as a regression test for this PR because it:
- passes on the PR, 
- fails in the codebase before the PR, and
- increases line coverage from %s to %s.

```rust
%s

%s
```

If you find this regression test useful, feel free to insert it to your test suite.
Our automated pipeline inserted the test at the end of the `%s` file before running it.

This is part of our research at the [ZEST](https://www.ifi.uzh.ch/en/zest.html) group of University of Zurich in collaboration with [Mozilla](https://www.mozilla.org).
If you have any suggestions, questions, or simply want to learn more, feel free to contact us at konstantinos.kitsios@uzh.ch and mcastelluccio@mozilla.com.
"""

GUIDELINES: str = (
    "Before you begin:\n"
    "- Keep going until the job is completely solved — don’t stop halfway.\n"
    "- If you’re unsure about the behavior, reread the provided patch carefully; do not hallucinate.\n"
    "- Plan your approach before writing code by reflecting on whether the test truly fails before and passes after.\n\n"
)

EXAMPLE_TEST_STRUCTURE: str = (
    "Follow this expected output format, do not deviate from this structure:\n"
    "<Filename> ... </Filename>\n"
    "<imports> ... </imports>\n"
    "<Rust>\n"
    "#[test]\n"
    "fn test_<describe_behavior>() {\n"
    "  <initialize required variables>;\n"
    "  <define expected variable>;\n"
    "  <generate actual variables>;\n"
    "  <compare expected with actual>;\n"
    "}"
    "</Rust>\n\n"
)

INITIAL_INSTRUCTIONS: str = (
    "Identify whether a unit test is needed.\n"
    "If there is no test needed or you believe you need additional testing resources beyond "
    "the Rust standard library (e.g., mocking libraries) to write a useful unit test, return <NO>.\n"
    "If a test is needed, your task is:\n"
    "1. Write exactly one rust test `#[test]fn test_...(){...}` block. Do NOT wrap the test inside a 'mod tests' block.\n"
    "If the file you are adding the test already contains a test in the <patch>, ensure that the test name is unique.\n"
    "2. Your test must fail on the code before the patch, and pass after, hence "
    "the test will verify that the patch resolves the issue.\n"
    "3. The test must be self-contained and to-the-point.\n"
    "4. All 'use' declarations must be inside a <imports>...</imports> block. Additionally:\n "
    "  - Do not use group imports.\n"
    "  - Import only what is necessary for the test to run and make sure not to have colliding imports.\n"
    "  - If the <patch> contains a 'mod tests' block with useful imports, do not add them to the <imports> block.\n"
    "  - Use `use super::<function name> for the function under test.\n."
    "  - If multiple 'use' statements are needed, list each on a separate line.\n"
    "5. To help you write the test, <Signatures> contains all modified function's:\n"
    "  - name\n"
    "  - parameters\n"
    "  - Return type (assume '()' if empty)\n"
    "6. Return only the absolute filename as it is in the <patch> block, the use statements, and rust test (no comments or explanations).\n\n"
    
)

LINTING_ISSUE_INSTRUCTIONS: str = (
    "A unit test has already been created for this PR and can be found alongside the filename and the imports "
    "used inside the <TEST> block.\n"
    "It currently contains linting issues, which are inside the <output> block.\n"
    "Your task is to:\n"
    "1. Identify and understand the linting issue introduced by the unit test.\n"
    "2. Update the unit test in the <TEST> block to resolve these issues.\n"
    "3. Return only the absolute filename as it is in the <patch> block, the use statements, and rust test (no comments or explanations).\n\n"
    )

PASS_TO_PASS_INSTRUCTIONS: str = (
    "A unit test has already been created for this PR and can be found alongside the filename and the imports used inside the <TEST> block."
    "The test should fail on the code before the patch, and pass after, hence the test verifies that the patch resolves the issue.\n"
    "However, the test currently passes before the patch.\n"
    "Your task is to:\n"
    "1. Identify and understand the reason behind the unit test passing before the patch.\n"
    "2. Update the unit test in the <TEST> block to resolve these issues. "
    "The updated test must fail on the code before the patch, and pass after, hence "
    "the test will verify that the patch resolves the issue.\n"
    "3. Return only the absolute filename as it is in the <patch> block, the use statements, and rust test (no comments or explanations).\n\n"
    )


ASSERTION_ERROR_INSTRUCTIONS: str = (
    "A unit test has already been created for this PR and can be found alongside the filename and the imports used inside the <TEST> block."
    "The test should fail on the code before the patch, and pass after, hence the test verifies that the patch resolves the issue.\n"
    "However, the test currently fails after the patch.\n"
    "Your task is to:\n"
    "1. Identify and understand why the unit test failed.\n"
    "2. Update the unit test in the <TEST> block in order for it to pass after the patch is introduced. "
    "The updated test must fail on the code before the patch, and pass after, hence "
    "the test will verify that the patch resolves the issue.\n"
    "3. Return only the absolute filename as it is in the <patch> block, the use statements, and rust test (no comments or explanations).\n\n"
)

COMPILATION_ERROR_INSTRUCTIONS: str = (
    "A unit test has already been created for this PR and can be found alongside the filename and the imports "
    "used inside the <TEST> block.\n"
    "It currently fails on codebase after the patch, which the errors in the <output> block.\n"
    "Your task is to:\n"
    "1. Identify and understand the errors introduced by the unit test.\n"
    "2. Update the unit test in the <TEST> block to resolve these issues. "
    "The updated test must fail on the code before the patch, and pass after, hence "
    "the test will verify that the patch resolves the issue.\n"
    "3. Return only the absolute filename as it is in the <patch> block, the use statements, and rust test (no comments or explanations).\n\n"
)

def get_instructions_template(repo: str, prompt_type: PromptType) -> str:
    instructions = f"You are a software tester at {repo} and your are reviewing the above <patch> for the above <issue>.\n"
    if prompt_type == PromptType.INITIAL:
        instructions += INITIAL_INSTRUCTIONS
    elif prompt_type == PromptType.LINTING_ISSUE:
        instructions += LINTING_ISSUE_INSTRUCTIONS
    elif prompt_type == PromptType.PASS_TO_PASS:
        instructions += PASS_TO_PASS_INSTRUCTIONS
    elif prompt_type == PromptType.ASSERTION_ERROR:
        instructions += ASSERTION_ERROR_INSTRUCTIONS
    elif prompt_type == PromptType.COMPILATION_ERROR:
        instructions += COMPILATION_ERROR_INSTRUCTIONS
    else:
        raise ValueError(f"Unknown prompt type: {prompt_type}")
    return instructions
    
