COMMENT_TEMPLATE = """Hi! 🤖 The test below is automatically generated and could serve as a regression test for this PR because it:
- passes, and
- fails in the codebase before the PR.

```rust
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


def get_instructions_template(repo: str) -> str:
    return (
        f"You are a software tester at {repo} and your are reviewing the above <patch> for the above <issue>\n"
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
