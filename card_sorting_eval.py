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
    PRE_PROMPT_FAILURE = "Pre Prompt Failure"
    MODEL_QUERY_FAILURE = "Model Query Failure"
    MODEL_RESPONSE_PARSING_FAILURE = "Model Response Parsing Failure"
    NO_TEST_NEEDED = "No Test Needed"
    RESPONSE_FILENAME_NOT_EXISTENT = "Response Filename Not Existent"
    TEST_PASS_PRE_PR = "Pass 2 Pass Test"
    ASSERTION_FAILURE = "Assertion Failure"


# Directories
EVALUATION_DIR = "off_eval_10092025"
GEN_TESTS_DIR = "generated_tests_10092025"
OUTPUT_FILE = Path(Path.cwd(), "card_sorting_evaluation.txt")

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


def main(eval_dir: Path):
    
    with open(OUTPUT_FILE, "w") as f:
                f.write("Card Sorting Evaluation Results\n")
                f.write("=======================================\n\n")
    
    for s in os.listdir(eval_dir):
        if Path(eval_dir, s).is_dir() and _is_mozilla_repo_dir(s):
            _handle_mozilla_repo_dir(Path(eval_dir, s))
        else:
            continue
    
    with open(OUTPUT_FILE, "a") as f:
        f.write("\n\nOverall Metrics\n")
        f.write("----------------------------------------\n")
        f.write(f"Total Tests: {TOTAL_TESTS}\n")
        f.write(f"Total Passed Tests: {PASSED_TESTS}\n")
        f.write(f"- GPT-4o Passed Tests: {GPT_4O_PASSED_TESTS}\n")
        f.write(f"- DeepSeek Passed Tests: {DEEPSEEK_PASSED_TESTS}\n")
        f.write(f"- Llama Passed Tests: {LLAMA_PASSED_TESTS}\n\n")
        
        f.write(f"Total Runs: {TOTAL_RUNS}\n")
        f.write(f"- GPT-4o Test Runs: {GPT_4O_TEST_RUNS}\n")
        f.write(f"- DeepSeek Test Runs: {DEEPSEEK_TEST_RUNS}\n")
        f.write(f"- Llama Test Runs: {LLAMA_TEST_RUNS}\n\n")
        
        f.write("Total Failure per Group:\n")
        f.write("----------------------------------------\n")
        for k, v in FAILURES_2_COUNT.items():
            f.write(f"{k}: {v}\n")

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
 
def _handle_mozilla_repo_dir(repo_dir: Path):
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
    with open(OUTPUT_FILE, "a") as f:
        f.write(f"Repository: {curr_repo}\n")
        f.write("----------------------------------------\n")

    # Data structure to hold failure reasons
    # idea here is to have "error_code": [list of pr dirs that failed with this error code]
    fail2pr: dict[str, list[str]] = {
        FailureType.PRE_PROMPT_FAILURE: [],
        FailureType.MODEL_QUERY_FAILURE: [],
        FailureType.MODEL_RESPONSE_PARSING_FAILURE: [],
        FailureType.NO_TEST_NEEDED: [],
        FailureType.RESPONSE_FILENAME_NOT_EXISTENT: [],
        FailureType.TEST_PASS_PRE_PR: [],
        FailureType.ASSERTION_FAILURE: []
    }
    total_runs: dict[str, int] = {
        "total": 0,
        Model.GPT_4O: 0,
        Model.DEEPSEEK: 0,
        Model.LLAMA: 0
    }
    erroneus_tests: dict[str, int] = {
        "total": 0,
        Model.GPT_4O: 0,
        Model.DEEPSEEK: 0,
        Model.LLAMA: 0
    }
    passed_tests: dict[str, int] = {
        "total": 0,
        Model.GPT_4O: 0,
        Model.DEEPSEEK: 0,
        Model.LLAMA: 0
    } 

    for repo_pr in os.listdir(repo_dir):
        if Path(repo_dir, repo_pr).is_dir() and _is_pr_dir(repo_pr):
            _handle_pr_dir(Path(repo_dir, repo_pr), fail2pr, total_runs, erroneus_tests, passed_tests)
    
    total_tests = len(os.listdir(repo_dir))
    with open(OUTPUT_FILE, "a") as f:
        f.write(f"Total Tests: {total_tests}\n")
        f.write("Runs:\n")
        f.write("\n".join(f"- {key}: {value}" for key, value in total_runs.items()))
        f.write("\nPassed Runs (=Tests):\n")
        f.write("\n".join(f"- {key}: {value}" for key, value in passed_tests.items()))
        f.write("\nErroneus Runs:\n")
        f.write("\n".join(f"- {key}: {value}" for key, value in erroneus_tests.items()))
        f.write("\n\nFailure Classifications:\n- - - - - - - - - - - - -\n")
        for failure_type, pr_list in fail2pr.items():
            f.write(f"[{len(pr_list)}] {failure_type}: {", ".join(pr_list)}\n")
        f.write("\n----------------------------------------\n")
    
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


def _handle_pr_dir(pr_dir: Path, fail2pr: dict[str, list[str]], total_runs: dict[str, int], erroneus_tests: dict[str, int], passed_tests: dict[str, int]):
    model_attempts = os.listdir(pr_dir)
    if not any(Path(pr_dir, attempt).is_dir() for attempt in model_attempts):
        fail2pr[FailureType.PRE_PROMPT_FAILURE].append(pr_dir.name.rsplit("_", 2)[0].split("__")[1])
        return
    for model_attempt in model_attempts:
        model_attempt_path = Path(pr_dir, model_attempt)
        if model_attempt_path.is_dir() and _is_model_dir(model_attempt):
            curr_model = model_attempt.split("_")[1]
            total_runs[curr_model] += 1
            total_runs["total"] += 1
            pr_dir_name = pr_dir.name.rsplit("_", 2)[0].split("__")[1]
            _handle_model_attempt_dir(model_attempt_path, pr_dir_name, fail2pr, erroneus_tests, passed_tests)
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


def _handle_model_attempt_dir(model_dir: Path, pr_dir_name: str, fail2pr: dict[str, list[str]], erroneus_tests: dict[str, int], passed_tests: dict[str, int]):
    files = os.listdir(model_dir)
    if len(files) == 6: # All files are present, we can check the after.txt file to see if the test passed or failed
        after_content = Path(model_dir, "after.txt").read_text()
        has_test_passed = True
        # Exit code only present if tests were run post 17.09.2025 17:00
        exit_code = re.search(r"Exit Code:(\d+)", after_content)
        if exit_code and exit_code.group(1) != "0": # Non-zero exit code, test failed
            has_test_passed = False
        
        
        for line in after_content.splitlines():
            if line.strip().startswith("error"):
                has_test_passed = False
                error_code = re.search(r"error\[(E\d{4})\]:", line.strip())
                if error_code: # Line has specific error code defined
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
            
        if has_test_passed: # Test passed
            passed_tests["total"] += 1
            curr_model = model_dir.name.split("_")[1]
            passed_tests[curr_model] += 1
            
        else:
            erroneus_tests["total"] += 1
            curr_model = model_dir.name.split("_")[1]
            erroneus_tests[curr_model] += 1
            
        
    else: # We know that an error occurred
        erroneus_tests["total"] += 1
        curr_model = model_dir.name.split("_")[1]
        erroneus_tests[curr_model] += 1
        erroneus_tests[curr_model] += 1
        if not files: # Empty directory, pre-prompt failure
            fail2pr[FailureType.PRE_PROMPT_FAILURE].append(pr_dir_name)
        elif len(files) == 1: # Only prompt.txt file is present, model query failure
            fail2pr[FailureType.MODEL_QUERY_FAILURE].append(pr_dir_name)
        elif len(files) == 2: # Either parsing the model response didn't work or no test is needed
            raw_model_response = Path(model_dir, "raw_model_response.txt").read_text()
            if "<NO>" in raw_model_response: # Model deemed no fix was needed
                fail2pr[FailureType.NO_TEST_NEEDED].append(pr_dir_name)
            else: # Model response parsing failure
                fail2pr[FailureType.MODEL_RESPONSE_PARSING_FAILURE].append(pr_dir_name)
        elif len(files) == 3: # before.txt + prompt.txt + raw_model_response.txt, test passed pre-PR    
            fail2pr[FailureType.RESPONSE_FILENAME_NOT_EXISTENT].append(pr_dir_name)
        elif len(files) == 5: # only after.txt file is missing, test passed pre-PR
            fail2pr[FailureType.TEST_PASS_PRE_PR].append(pr_dir_name)

def _validate_eval_dir(eval_dir: Path):
    if not eval_dir.exists() or not eval_dir.is_dir():
        print(
            f"[!] Error: Evaluation directory {eval_dir} does not exist or is not a directory."
        )
        sys.exit(1)
    
    for dir in os.listdir(eval_dir):
        if not Path(eval_dir, dir).is_dir():
            continue
        owner, repo = dir.split("_")
        if not owner == "mozilla":
            print(
                f"[!] Error: Unknown repository owner {owner} found in evaluation directory."
            )
            sys.exit(1)
        if repo not in [e.value for e in Repository]:
            print(
                f"[!] Error: Unknown repository directory {dir} found in evaluation directory."
            )
            sys.exit(1)


if __name__ == "__main__":
    eval_dir = Path(Path.cwd(), EVALUATION_DIR)
    _validate_eval_dir(eval_dir)
    main(eval_dir)
