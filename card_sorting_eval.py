import json
import os
import re
import sys
from dataclasses import dataclass, field
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

RUST_COMMON_ERROR_NON_ERRORS = [
    "error: could not compile",
    "error: test failed",
    "error: process didn't exit successfully",
    "error: build failed",
    "error: aborting due to" "error: linking with",
    "error: package has no library targets",
    "error: no bin target named",
    "error: bench target",
    "error: example target",
    "error: permission denied",
    "error: interrupted",
    "error: connection refused",
    "error: network unreachable",
]


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
    UNSPECIFIC_ERROR = "UnspecifiedError"
    TESTNOTRUN = "TestNotRun"
    TIMEOUT = "Timeout"
    SHARED_OBJECT_NOT_FOUND = "SharedObjectNotFound"
    THREAD_PANIC = "ThreadPanic"


class EvaluationMetrics:
    def __init__(self):
        self.total_tests = 0
        self.passed_tests = 0
        self.total_runs = 0
        self.model_stats = {
            Model.GPT_4O: {"passed": 0, "runs": 0},
            Model.DEEPSEEK: {"passed": 0, "runs": 0},
            Model.LLAMA: {"passed": 0, "runs": 0},
        }
        self.failures_count: dict[str, int] = {
            failure.value: 0 for failure in FailureType
        }
        self.repository_stats = {repo.value: RepositoryStats() for repo in Repository}


@dataclass
class RepositoryStats:
    total_runs: dict[str, int] = field(
        default_factory=lambda: {"total": 0, **{m.value: 0 for m in Model}}
    )
    passed_tests: dict[str, int] = field(
        default_factory=lambda: {"total": 0, **{m.value: 0 for m in Model}}
    )
    erroneous_tests: dict[str, int] = field(
        default_factory=lambda: {"total": 0, **{m.value: 0 for m in Model}}
    )
    fail2pr: dict[str, list[str]] = field(
        default_factory=lambda: {f.value: [] for f in FailureType}
    )


PLOTTING_DATA_FAILURE_CUTOFF = 10  # Only show top 10 failure reasons


def main(eval_dir: Path):
    evaluation_metrics = EvaluationMetrics()
    plotting_data = {}
    plotting_data["pie_chart"] = {}
    plotting_data["stacked_bar_chart"] = {}
    plotting_data["horizontal_bar_chart"] = {}

    _write_to_output_file(
        eval_dir,
        "Card Sorting Evaluation Results\n=======================================",
        "w",
    )

    for s in os.listdir(eval_dir):
        if Path(eval_dir, s).is_dir() and _is_mozilla_repo_dir(s):
            _handle_mozilla_repo_dir(Path(eval_dir, s), eval_dir, evaluation_metrics)
        else:
            continue

    _aggregate_data(evaluation_metrics)

    _create_plotting_data(plotting_data, evaluation_metrics)

    output_metrics = (
        "\n\n----------------------------------------\n"
        "Overall Metrics\n"
        "----------------------------------------\n"
        f"Total Tests: {evaluation_metrics.total_tests}\n"
        f"Total Passed Tests: {evaluation_metrics.passed_tests}\n"
        f"- GPT-4o Passed Tests: {evaluation_metrics.model_stats[Model.GPT_4O]["passed"]}\n"
        f"- DeepSeek Passed Tests: {evaluation_metrics.model_stats[Model.DEEPSEEK]["passed"]}\n"
        f"- Llama Passed Tests: {evaluation_metrics.model_stats[Model.LLAMA]["passed"]}\n\n"
        f"Total Runs: {evaluation_metrics.total_runs}\n"
        f"- GPT-4o Test Runs: {evaluation_metrics.model_stats[Model.GPT_4O]["runs"]}\n"
        f"- DeepSeek Test Runs: {evaluation_metrics.model_stats[Model.DEEPSEEK]["runs"]}\n"
        f"- Llama Test Runs: {evaluation_metrics.model_stats[Model.LLAMA]["runs"]}\n\n"
        "Total Failure per Group:\n"
        "----------------------------------------\n"
        + "\n".join(f"{k}: {v}" for k, v in evaluation_metrics.failures_count.items())
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


def _handle_mozilla_repo_dir(
    repo_dir: Path, eval_dir: Path, evaluation_metrics: EvaluationMetrics
):
    curr_repo = os.path.basename(repo_dir).split("_")[1]

    for repo_pr in os.listdir(repo_dir):
        if Path(repo_dir, repo_pr).is_dir() and _is_pr_dir(repo_pr):
            _handle_pr_dir(
                Path(repo_dir, repo_pr), Repository(curr_repo), evaluation_metrics
            )

    repo_stats = evaluation_metrics.repository_stats[curr_repo]

    total_tests = len(os.listdir(repo_dir))
    repository_metrics = (
        "\n\n----------------------------------------\n"
        f"Repository: {curr_repo}"
        "\n----------------------------------------\n"
        f"Total Tests: {total_tests}\n"
        "Runs:\n"
        + "\n".join(f"- {key}: {value}" for key, value in repo_stats.total_runs.items())
        + "\nPassed Runs (=Tests):\n"
        + "\n".join(
            f"- {key}: {value}" for key, value in repo_stats.passed_tests.items()
        )
        + "\nErroneus Runs:\n"
        + "\n".join(
            f"- {key}: {value}" for key, value in repo_stats.erroneous_tests.items()
        )
        + "\n\nFailure Classifications:\n- - - - - - - - - - - - -\n"
        + "\n".join(
            f"[{len(pr_list)}] {failure_type}: {', '.join(pr_list)}"
            for failure_type, pr_list in repo_stats.fail2pr.items()
        )
    )

    _write_to_output_file(eval_dir, repository_metrics)


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
    pr_dir: Path, curr_repo: Repository, evaluation_metrics: EvaluationMetrics
):
    model_attempts = os.listdir(pr_dir)
    repo_stats = evaluation_metrics.repository_stats[curr_repo.value]
    evaluation_metrics.total_tests += 1

    if not any(Path(pr_dir, attempt).is_dir() for attempt in model_attempts):
        repo_stats.fail2pr[FailureType.PRE_PROMPT_FAILURE].append(
            pr_dir.name.rsplit("_", 2)[0].split("__")[1]
        )
        return
    for model_attempt in model_attempts:
        model_attempt_path = Path(pr_dir, model_attempt)
        if model_attempt_path.is_dir() and _is_model_dir(model_attempt):
            curr_model = model_attempt.split("_")[1]
            repo_stats.total_runs[curr_model] += 1
            repo_stats.total_runs["total"] += 1
            pr_dir_name = pr_dir.name.rsplit("_", 2)[0].split("__")[1]
            _handle_model_attempt_dir(
                model_attempt_path, pr_dir_name, curr_repo, evaluation_metrics
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
    repo: Repository,
    evaluation_metrics: EvaluationMetrics,
):
    repo_stats = evaluation_metrics.repository_stats[repo.value]
    model = Model(model_dir.name.split("_")[1])

    def _add_to_failure_count(failure_type: FailureType | str):
        if failure_type not in repo_stats.fail2pr and type(failure_type) is str:
            repo_stats.fail2pr[failure_type] = []
        repo_stats.fail2pr[failure_type].append(pr_dir_name)

    files = os.listdir(model_dir)

    failure_type = _categorize_failure_by_file_count(files, model_dir, pr_dir_name)

    if type(failure_type) is str or type(failure_type) is FailureType:
        _add_to_failure_count(failure_type)
        repo_stats.erroneous_tests[model] += 1
        repo_stats.erroneous_tests["total"] += 1
    elif type(failure_type) is list:
        for ft in failure_type:
            _add_to_failure_count(ft)
        repo_stats.erroneous_tests[model] += 1
        repo_stats.erroneous_tests["total"] += 1
    elif failure_type is None:
        repo_stats.passed_tests[model] += 1
        repo_stats.passed_tests["total"] += 1


def _categorize_failure_by_file_count(
    files: list, model_dir: Path, pr_dir_name: str
) -> None | FailureType | list[str]:
    file_count = len(files)

    if file_count == 0:
        return FailureType.PRE_PROMPT_FAILURE
    elif file_count == 1:
        return FailureType.MODEL_QUERY_FAILURE
    elif file_count == 2:
        raw_response = Path(model_dir, "raw_model_response.txt").read_text()
        return (
            FailureType.NO_TEST_NEEDED
            if "<NO>" in raw_response
            else FailureType.MODEL_RESPONSE_PARSING_FAILURE
        )
    elif file_count == 3:
        return FailureType.RESPONSE_FILENAME_NOT_EXISTENT
    elif file_count == 5:
        return FailureType.TEST_PASS_PRE_PR
    elif file_count == 6:
        after_content = Path(model_dir, "after.txt").read_text()
        if after_content:
            test_passed, error_codes = _analyze_test_results(after_content)
            if test_passed is True:
                return None
            elif test_passed is False:
                return error_codes
    elif file_count == 7:
        return None

    raise Exception(
        f"Unexpected number of files in model attempt directory: {file_count}"
    )


def _analyze_test_results(after_content: str) -> tuple[bool, list[str]]:
    """Analyze test results and return (passed, error_codes)"""
    has_test_passed = True
    error_codes = []

    # Check exit code
    exit_code = re.search(r"Exit Code:(\d+)", after_content)
    if exit_code and exit_code.group(1) != "0":
        has_test_passed = False

    compilation_error = re.search(r"error: could not compile", after_content)
    if compilation_error:
        has_test_passed = False
    # Check for errors and test failures
    for line in after_content.splitlines():
        if line.strip().startswith("error"):
            has_test_passed = False
            error_code = re.search(r"error\[(E\d{4})\]:", line.strip())
            if error_code:
                error_codes.append(error_code.group(1))
                continue
            elif line.strip().startswith("error[timeout]:"):
                error_codes.append(FailureType.TIMEOUT)
                continue
            elif any(error in line for error in RUST_COMMON_ERROR_NON_ERRORS):
                continue
            error_codes.append(FailureType.UNSPECIFIC_ERROR)
        elif line.strip().startswith("test result: FAILED"):
            return False, [FailureType.ASSERTION_FAILURE]

    # Check if tests actually ran
    matches = re.findall(r"\d passed;", after_content)
    if has_test_passed and (not matches or all(m == "0 passed;" for m in matches)):
        return False, [FailureType.TESTNOTRUN]

    if not has_test_passed and not error_codes:
        if exit_code and exit_code.group(1) == "127":
            has_test_passed = False
            error_codes.append(FailureType.SHARED_OBJECT_NOT_FOUND)
        elif exit_code and (exit_code.group(1) == "1" or exit_code.group(1) == "101"):
            has_test_passed = False
            error_codes.append(FailureType.THREAD_PANIC)

    return has_test_passed, error_codes


def _write_to_output_file(eval_dir: Path, content: str, mode: str = "a"):
    output_file = "card_sorting_evaluation.txt"
    path_to_output_file = Path(Path.cwd(), eval_dir, output_file)

    if not path_to_output_file.exists():
        path_to_output_file.touch()

    with open(path_to_output_file, mode) as f:
        f.write(content)


def _create_plotting_data(plotting_data: dict, evaluation_metrics: EvaluationMetrics):
    """
    Parse the failure data to JSON format for plotting.
    Only keep the top PLOTTING_DATA_FAILURE_CUTOFF failure reasons + ties.
    """

    for curr_repo, repo_stats in evaluation_metrics.repository_stats.items():
        # Stacked bar chart & Pie chart data
        passed_tests = repo_stats.passed_tests.copy()
        plotting_data["stacked_bar_chart"][curr_repo] = passed_tests
        plotting_data["pie_chart"][curr_repo] = passed_tests["total"]
        del plotting_data["stacked_bar_chart"][curr_repo]["total"]

        # Horizontal Bar Chart data per repository
        fail_2_amount = {k: len(v) for k, v in repo_stats.fail2pr.items() if len(v) > 0}
        repo_data = _compute_horizontal_bar_chart_data(fail_2_amount)

        plotting_data["horizontal_bar_chart"][curr_repo] = repo_data

    total_data = _compute_horizontal_bar_chart_data(evaluation_metrics.failures_count)
    plotting_data["horizontal_bar_chart"]["total"] = total_data


def _compute_horizontal_bar_chart_data(fail_2_amount: dict[str, int]):
    fail_2_amount_sorted = dict(
        sorted(fail_2_amount.items(), key=lambda item: item[1], reverse=True)
    )

    cutoff_idx = PLOTTING_DATA_FAILURE_CUTOFF - 1
    cutoff_value = [*fail_2_amount_sorted.values()][cutoff_idx]
    while len(fail_2_amount_sorted) > cutoff_idx:
        vals = list(fail_2_amount_sorted.values())
        if vals[cutoff_idx] == cutoff_value:
            cutoff_idx += 1
        else:
            keys = list(fail_2_amount_sorted.keys())
            del fail_2_amount_sorted[keys[cutoff_idx]]

    return fail_2_amount_sorted


def _write_to_plotting_data_file(eval_dir: Path, content: dict):
    path_to_json_file = Path(Path.cwd(), eval_dir, "plotting_data.json")
    path_to_json_file.touch(exist_ok=True)

    with open(path_to_json_file, "w") as jf:
        json.dump(content, jf, indent=2)


def _aggregate_data(evaluation_metrics: EvaluationMetrics):
    for _, repo_stats in evaluation_metrics.repository_stats.items():
        evaluation_metrics.total_runs += repo_stats.total_runs["total"]
        evaluation_metrics.model_stats[Model.GPT_4O][
            "passed"
        ] += repo_stats.passed_tests[Model.GPT_4O]
        evaluation_metrics.model_stats[Model.GPT_4O]["runs"] += repo_stats.total_runs[
            Model.GPT_4O
        ]
        evaluation_metrics.model_stats[Model.DEEPSEEK][
            "passed"
        ] += repo_stats.passed_tests[Model.DEEPSEEK]
        evaluation_metrics.model_stats[Model.DEEPSEEK]["runs"] += repo_stats.total_runs[
            Model.DEEPSEEK
        ]
        evaluation_metrics.model_stats[Model.LLAMA][
            "passed"
        ] += repo_stats.passed_tests[Model.LLAMA]
        evaluation_metrics.model_stats[Model.LLAMA]["runs"] += repo_stats.total_runs[
            Model.LLAMA
        ]
        evaluation_metrics.passed_tests += repo_stats.passed_tests["total"]
        for failure_type, pr_list in repo_stats.fail2pr.items():
            if evaluation_metrics.failures_count.get(failure_type) is None:
                evaluation_metrics.failures_count[failure_type] = 0
            evaluation_metrics.failures_count[failure_type] += len(pr_list)


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
