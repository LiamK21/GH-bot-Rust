import json
import os
import re
import sys
from enum import StrEnum
from pathlib import Path

# Types of failures:
# - Pre prompt failures
# - Model query failures
# - Model response parsing failures
# - No test needed
# - Response filename does not exist
# - Pass2Pass Test
# - Assertion Failure
# - "Any failure codes"


class Model(StrEnum):
    GPT_4O = "gpt-4o"
    DEEPSEEK = "deepseek-r1-distill-llama-70b"
    LLAMA = "llama-3.3-70b-versatile"


class Repository(StrEnum):
    GLEAN = "glean"
    GRCOV = "grcov"
    NEQO = "neqo"
    RUST_CODE_ANALYSIS = "rust-code-analysis"


class FailureType(StrEnum):
    PRE_PROMPT_FAILURE = "PrePromptError"
    MODEL_QUERY_FAILURE = "ModelQueryError"
    MODEL_RESPONSE_PARSING_FAILURE = "ModelResponseParsingError"
    NO_TEST_NEEDED = "Abstention"
    RESPONSE_FILENAME_NOT_EXISTENT = "FilenameError"
    TEST_PASS_PRE_PR = "Pass2Pass"
    ASSERTION_FAILURE = "AssertionError"


# Test metrics
TOTAL_TESTS = 0
PASSED_TESTS = 0
GPT_4O_PASSED_TESTS = 0
DEEPSEEK_PASSED_TESTS = 0
LLAMA_PASSED_TESTS = 0

# Run metrics
TOTAL_RUNS = 0
GPT_4O_TEST_RUNS = 0
DEEPSEEK_TEST_RUNS = 0
LLAMA_TEST_RUNS = 0

FAILURES_2_COUNT: dict[str, int] = {
    FailureType.PRE_PROMPT_FAILURE: 0,
    FailureType.ASSERTION_FAILURE: 0,
    FailureType.MODEL_QUERY_FAILURE: 0,
    FailureType.MODEL_RESPONSE_PARSING_FAILURE: 0,
    FailureType.NO_TEST_NEEDED: 0,
    FailureType.RESPONSE_FILENAME_NOT_EXISTENT: 0,
    FailureType.TEST_PASS_PRE_PR: 0,
}
PLOTTING_DATA_FAILURE_CUTOFF = 10  # Only show top 10 failure reasons


def main(eval_dir: Path):
    path_to_json_file = Path(Path.cwd(), eval_dir, "plotting_data.json")
    path_to_json_file.touch(exist_ok=True)
    plotting_data = {}
    plotting_data["pie_chart"] = {}
    plotting_data["stacked_bar_chart"] = {}
    plotting_data["horizontal_bar_chart"] = {}

    _write_to_output_file(
        eval_dir,
        "Card Sorting Evaluation Results\n=======================================",
    )

    for s in os.listdir(eval_dir):
        if Path(eval_dir, s).is_dir() and _is_mozilla_repo_dir(s):
            _handle_mozilla_repo_dir(Path(eval_dir, s), eval_dir, plotting_data)
        else:
            continue

    for repo, passed_tests in plotting_data["stacked_bar_chart"].items():
        total_passed_tests = passed_tests["total"]
        plotting_data["pie_chart"][repo] = total_passed_tests
        del plotting_data["stacked_bar_chart"][repo]["total"]

    failure_data = dict(
        sorted(FAILURES_2_COUNT.items(), key=lambda item: item[1], reverse=True)
    )
    _parse_failure_data_to_json(plotting_data, "total", failure_data)

    output_metrics = (
        "\n\n----------------------------------------\n"
        "Overall Metrics\n"
        "----------------------------------------\n"
        f"Total Tests: {TOTAL_TESTS}\n"
        f"Total Passed Tests: {PASSED_TESTS}\n"
        f"- GPT-4o Passed Tests: {GPT_4O_PASSED_TESTS}\n"
        f"- DeepSeek Passed Tests: {DEEPSEEK_PASSED_TESTS}\n"
        f"- Llama Passed Tests: {LLAMA_PASSED_TESTS}\n\n"
        f"Total Runs: {TOTAL_RUNS}\n"
        f"- GPT-4o Test Runs: {GPT_4O_TEST_RUNS}\n"
        f"- DeepSeek Test Runs: {DEEPSEEK_TEST_RUNS}\n"
        f"- Llama Test Runs: {LLAMA_TEST_RUNS}\n\n"
        "Total Failure per Group:\n"
        "----------------------------------------\n"
        + "\n".join(f"{k}: {v}" for k, v in FAILURES_2_COUNT.items())
    )
    _write_to_output_file(eval_dir, output_metrics)
    _write_to_plotting_data_file(eval_dir, plotting_data)


def _is_mozilla_repo_dir(dir_name: str) -> bool:
    dir_parts = dir_name.split("_")
    if len(dir_parts) != 2:
        return False
    owner, repo = dir_parts
    if owner != "mozilla":
        return False
    if repo not in [e.value for e in Repository]:
        return False
    return True


def _handle_mozilla_repo_dir(repo_dir: Path, eval_dir: Path, plotting_data: dict):
    global FAILURES_2_COUNT
    global TOTAL_RUNS
    global GPT_4O_TEST_RUNS
    global DEEPSEEK_TEST_RUNS
    global LLAMA_TEST_RUNS
    global TOTAL_TESTS
    global PASSED_TESTS
    global GPT_4O_PASSED_TESTS
    global DEEPSEEK_PASSED_TESTS
    global LLAMA_PASSED_TESTS

    curr_repo = os.path.basename(repo_dir).split("_")[1]

    # Data structure to hold failure reasons
    # idea here is to have "error_code": [list of pr dirs that failed with this error code]
    fail2pr: dict[str, list[str]] = {
        FailureType.PRE_PROMPT_FAILURE: [],
        FailureType.MODEL_QUERY_FAILURE: [],
        FailureType.MODEL_RESPONSE_PARSING_FAILURE: [],
        FailureType.NO_TEST_NEEDED: [],
        FailureType.RESPONSE_FILENAME_NOT_EXISTENT: [],
        FailureType.TEST_PASS_PRE_PR: [],
        FailureType.ASSERTION_FAILURE: [],
    }
    total_runs: dict[str, int] = {
        "total": 0,
        Model.GPT_4O: 0,
        Model.DEEPSEEK: 0,
        Model.LLAMA: 0,
    }
    erroneus_tests: dict[str, int] = {
        "total": 0,
        Model.GPT_4O: 0,
        Model.DEEPSEEK: 0,
        Model.LLAMA: 0,
    }
    passed_tests: dict[str, int] = {
        "total": 0,
        Model.GPT_4O: 0,
        Model.DEEPSEEK: 0,
        Model.LLAMA: 0,
    }

    for repo_pr in os.listdir(repo_dir):
        if Path(repo_dir, repo_pr).is_dir() and _is_pr_dir(repo_pr):
            _handle_pr_dir(
                Path(repo_dir, repo_pr),
                fail2pr,
                total_runs,
                erroneus_tests,
                passed_tests,
            )

    plotting_data["stacked_bar_chart"][curr_repo] = passed_tests
    fail_2_amount: dict[str, int] = {k: len(v) for k, v in fail2pr.items()}

    fail_2_amount_sorted = dict(
        sorted(fail_2_amount.items(), key=lambda item: item[1], reverse=True)
    )
    _parse_failure_data_to_json(plotting_data, curr_repo, fail_2_amount_sorted)

    total_tests = len(os.listdir(repo_dir))
    repository_metrics = (
        "\n\n----------------------------------------\n"
        f"Repository: {curr_repo}"
        "\n----------------------------------------\n"
        f"Total Tests: {total_tests}\n"
        "Runs:\n"
        + "\n".join(f"- {key}: {value}" for key, value in total_runs.items())
        + "\nPassed Runs (=Tests):\n"
        + "\n".join(f"- {key}: {value}" for key, value in passed_tests.items())
        + "\nErroneus Runs:\n"
        + "\n".join(f"- {key}: {value}" for key, value in erroneus_tests.items())
        + "\n\nFailure Classifications:\n- - - - - - - - - - - - -\n"
        + "\n".join(
            f"[{len(pr_list)}] {failure_type}: {', '.join(pr_list)}"
            for failure_type, pr_list in fail2pr.items()
        )
    )

    _write_to_output_file(eval_dir, repository_metrics)

    TOTAL_TESTS += total_tests
    PASSED_TESTS += passed_tests["total"]
    GPT_4O_PASSED_TESTS += passed_tests[Model.GPT_4O]
    DEEPSEEK_PASSED_TESTS += passed_tests[Model.DEEPSEEK]
    LLAMA_PASSED_TESTS += passed_tests[Model.LLAMA]
    TOTAL_RUNS += total_runs["total"]
    GPT_4O_TEST_RUNS += total_runs[Model.GPT_4O]
    DEEPSEEK_TEST_RUNS += total_runs[Model.DEEPSEEK]
    LLAMA_TEST_RUNS += total_runs[Model.LLAMA]

    for k, v in fail2pr.items():
        if FAILURES_2_COUNT.get(k) is None:
            FAILURES_2_COUNT[k] = 0
        FAILURES_2_COUNT[k] += len(v)


def _is_pr_dir(dir_name: str) -> bool:
    owner, rest = dir_name.split("__")
    pr_repo, _, _ = rest.split("_")
    if owner != "mozilla":
        return False
    if "-" not in pr_repo:
        return False
    repo, pr_number = pr_repo.rsplit("-", 1)
    if repo not in [e.value for e in Repository]:
        return False
    if not pr_number.isdigit():
        return False
    return True


def _handle_pr_dir(
    pr_dir: Path,
    fail2pr: dict[str, list[str]],
    total_runs: dict[str, int],
    erroneus_tests: dict[str, int],
    passed_tests: dict[str, int],
):
    model_attempts = os.listdir(pr_dir)
    if not any(Path(pr_dir, attempt).is_dir() for attempt in model_attempts):
        fail2pr[FailureType.PRE_PROMPT_FAILURE].append(
            pr_dir.name.rsplit("_", 2)[0].split("__")[1]
        )
        return
    for model_attempt in model_attempts:
        model_attempt_path = Path(pr_dir, model_attempt)
        if model_attempt_path.is_dir() and _is_model_dir(model_attempt):
            curr_model = model_attempt.split("_")[1]
            total_runs[curr_model] += 1
            total_runs["total"] += 1
            pr_dir_name = pr_dir.name.rsplit("_", 2)[0].split("__")[1]
            _handle_model_attempt_dir(
                model_attempt_path, pr_dir_name, fail2pr, erroneus_tests, passed_tests
            )
        else:
            continue
    pass


def _is_model_dir(dir_name: str) -> bool:
    dir_parts = dir_name.split("_")
    if not len(dir_parts) == 2:
        return False

    attempt, model = dir_parts
    if not attempt.startswith("i"):
        return False
    if model not in [m.value for m in Model]:
        return False
    return True


def _handle_model_attempt_dir(
    model_dir: Path,
    pr_dir_name: str,
    fail2pr: dict[str, list[str]],
    erroneus_tests: dict[str, int],
    passed_tests: dict[str, int],
):
    files = os.listdir(model_dir)
    if (
        len(files) == 6
    ):  # All files are present, we can check the after.txt file to see if the test passed or failed
        after_content = Path(model_dir, "after.txt").read_text()
        has_test_passed = True
        # Exit code only present if tests were run post 17.09.2025 17:00
        exit_code = re.search(r"Exit Code:(\d+)", after_content)
        if exit_code and exit_code.group(1) != "0":  # Non-zero exit code, test failed
            has_test_passed = False

        for line in after_content.splitlines():
            if line.strip().startswith("error"):
                has_test_passed = False
                error_code = re.search(r"error\[(E\d{4})\]:", line.strip())
                if error_code:  # Line has specific error code defined
                    code = error_code.group(1)
                    if fail2pr.get(code) is None:
                        fail2pr[code] = []
                    fail2pr[code].append(pr_dir_name)
                else:
                    break

            elif line.strip().startswith("test result: FAILED"):
                has_test_passed = False
                fail2pr[FailureType.ASSERTION_FAILURE].append(pr_dir_name)
                break

        # Check that the test actually ran and was not skipped
        matches = re.findall(r"\d passed;", after_content)
        if not matches or all(m == "0 passed;" for m in matches):
            has_test_passed = False

        if has_test_passed:  # Test passed
            passed_tests["total"] += 1
            curr_model = model_dir.name.split("_")[1]
            passed_tests[curr_model] += 1

        else:
            erroneus_tests["total"] += 1
            curr_model = model_dir.name.split("_")[1]
            erroneus_tests[curr_model] += 1

    else:  # We know that an error occurred
        erroneus_tests["total"] += 1
        curr_model = model_dir.name.split("_")[1]
        erroneus_tests[curr_model] += 1
        if not files:  # Empty directory, pre-prompt failure
            fail2pr[FailureType.PRE_PROMPT_FAILURE].append(pr_dir_name)
        elif len(files) == 1:  # Only prompt.txt file is present, model query failure
            fail2pr[FailureType.MODEL_QUERY_FAILURE].append(pr_dir_name)
        elif (
            len(files) == 2
        ):  # Either parsing the model response didn't work or no test is needed
            raw_model_response = Path(model_dir, "raw_model_response.txt").read_text()
            if "<NO>" in raw_model_response:  # Model deemed no fix was needed
                fail2pr[FailureType.NO_TEST_NEEDED].append(pr_dir_name)
            else:  # Model response parsing failure
                fail2pr[FailureType.MODEL_RESPONSE_PARSING_FAILURE].append(pr_dir_name)
        elif (
            len(files) == 3
        ):  # before.txt + prompt.txt + raw_model_response.txt, test passed pre-PR
            fail2pr[FailureType.RESPONSE_FILENAME_NOT_EXISTENT].append(pr_dir_name)
        elif len(files) == 5:  # only after.txt file is missing, test passed pre-PR
            fail2pr[FailureType.TEST_PASS_PRE_PR].append(pr_dir_name)


def _write_to_output_file(eval_dir: Path, content: str):
    output_file = "card_sorting_evaluation.txt"
    path_to_output_file = Path(Path.cwd(), eval_dir, output_file)

    if not path_to_output_file.exists():
        path_to_output_file.touch()

    with open(path_to_output_file, "a") as f:
        f.write(content)


def _parse_failure_data_to_json(
    plotting_data: dict, curr_repo: str, fail_2_amount_sorted: dict[str, int]
):
    """
    Parse the failure data to JSON format for plotting.
    Only keep the top PLOTTING_DATA_FAILURE_CUTOFF failure reasons + ties.
    """
    cutoff_idx = PLOTTING_DATA_FAILURE_CUTOFF - 1
    cutoff_value = [*fail_2_amount_sorted.values()][cutoff_idx]
    while len(fail_2_amount_sorted) > cutoff_idx:
        vals = list(fail_2_amount_sorted.values())
        if vals[cutoff_idx] == cutoff_value:
            cutoff_idx += 1
        else:
            keys = list(fail_2_amount_sorted.keys())
            del fail_2_amount_sorted[keys[cutoff_idx]]

    plotting_data["horizontal_bar_chart"][curr_repo] = fail_2_amount_sorted


def _write_to_plotting_data_file(eval_dir: Path, content: dict):
    path_to_json_file = Path(Path.cwd(), eval_dir, "plotting_data.json")
    path_to_json_file.touch(exist_ok=True)

    with open(path_to_json_file, "a") as jf:
        json.dump(content, jf, indent=2)


def _validate_eval_dir(eval_dir: Path):
    for dir in os.listdir(eval_dir):
        if not Path(eval_dir, dir).is_dir():
            continue
        if dir == "generated_tests":
            continue
        owner, repo = dir.split("_")
        if not owner == "mozilla":
            print(
                f"[!] Error: Unknown directory with repository owner {owner} found in evaluation directory."
            )
            sys.exit(1)
        if repo not in [e.value for e in Repository]:
            print(
                f"[!] Error: Unknown Unknown directory with repository name {dir} found in evaluation directory."
            )
            sys.exit(1)


def _validate_sys_args(args: list[str]) -> Path:
    if len(args) != 1:
        print(f"Usage: python card_sorting_eval.py <evaluation_directory_in_CWD>")
        sys.exit(1)
    eval_dir = args[0]
    path_to_eval_dir = Path(Path.cwd(), eval_dir)
    if not path_to_eval_dir.exists() or not path_to_eval_dir.is_dir():
        print(
            f"[!] Error: Evaluation directory {eval_dir} does not exist in {Path.cwd()}."
        )
        sys.exit(1)
    return path_to_eval_dir


if __name__ == "__main__":
    passed_args = sys.argv
    eval_dir = _validate_sys_args(passed_args[1:])
    _validate_eval_dir(eval_dir)
    main(eval_dir)
