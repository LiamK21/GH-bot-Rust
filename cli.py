import argparse
import os
import shutil
import subprocess
import sys
from enum import Enum, StrEnum
from pathlib import Path
from typing import cast

import requests
from dotenv import load_dotenv, set_key

from payload_generator import PayloadGenerator
from webhook_handler import BotRunner
from webhook_handler.models import LLM
from webhook_handler.services import Config

# List of allowed repositories (or patterns)
ALLOWED_REPOS = ["grcov", "glean", "rust-code-analysis"]

ALLOWED_MODELS = [LLM.GPT4o.value, LLM.LLAMA.value, LLM.QWEN3.value]

ENV_VARIABLES = ["GITHUB_TOKEN", "OPENAI_API_KEY", "GROQ_API_KEY"]

CLI_DESCRIPTION = (
    "TestGen CLI Tool\n\n"
    f"This tool automatically runs test generation for supported repositories: {', '.join(ALLOWED_REPOS)}.\n"
    f"Supported LLM Models include: {', '.join(ALLOWED_MODELS)}.\n"
    "It uses LLM models from +the OpenAI and Groq APIs to generate unit tests based on code changes.\n\n"
    "This is part of our research at the [ZEST](https://www.ifi.uzh.ch/en/zest.html) group of University of Zurich in collaboration with [Mozilla](https://www.mozilla.org).\n"
    "If you have any suggestions, questions, or simply want to learn more, feel free to contact us at konstantinos.kitsios@uzh.ch and mcastelluccio@mozilla.com."
)


class Commands(StrEnum):
    RUN = "run"
    CONFIGURE = "configure"
    DELETE = "delete"
    CLEAR = "clear"


class RunFlags(Enum):
    PULL_REQUEST = ["-pr", "--pull-request"]
    LLMS_USED = ["--llms"]
    NUMBER_INVOCATIONS = ["-n", "--num-invocations"]


def get_git_remote() -> str | None:
    """Retrieves the remote origin URL of the current git repo."""
    try:
        # Get remote URL
        url = (
            subprocess.check_output(["git", "config", "--get", "remote.origin.url"])
            .decode("utf-8")
            .strip()
        )
        return url
    except subprocess.CalledProcessError:
        return None


def is_valid_repo(url):
    """Checks if the remote URL matches one of the target repositories."""
    if not url:
        return False

    if not any(repo in url for repo in ALLOWED_REPOS):
        return False

    try:
        response = requests.get(url)
        if response.status_code != 200:
            return False
    except requests.RequestException:
        return False

    return True


def remove_directory(dir: Path):
    """Removes a directory and all its contents."""
    try:
        if dir.exists():
            shutil.rmtree(dir)
            print(f"✅ Successfully removed directory: {dir}")
        else:
            print(f"⚠️  Directory does not exist: {dir}")
    except Exception as e:
        print(f"❌ Error removing directory: {e}")


def update_env_variables():
    """Updates environment variables from .env file."""
    load_dotenv()  # Reload environment variables from .env file
    dir_path = Path(__file__).parent
    if not dir_path.exists():
        print(f"❌ Directory does not exist: {dir_path}")
        sys.exit(1)

    env_path = dir_path / ".env"
    if not env_path.exists():
        env_path.touch()

    for key in ENV_VARIABLES:
        key_title = key.replace("_", " ").title()
        api_key = input(f"Enter your {key_title}: ").strip()

        if not api_key:
            print(f"❌ Key empty, skipping {key}.")
            continue

        success, _, _ = set_key(env_path, key, api_key, quote_mode="never")

        if success:
            print(f"✅ Successfully updated {key_title}")
        else:
            print(f"❌ Failed to update {key_title}")

def run_bot(repo: str, args: argparse.Namespace): 
    pr_number = args.pull_request[0]
    
    num_invocations = args.num_invocations
    
    llms = args.llms
    if isinstance(llms, str):
        llms = llms.split(",")
    llms = [llm.strip() for llm in llms if llm.strip() and llm.strip() in ALLOWED_MODELS]
    
    config = Config(llm_calls=num_invocations)
    payload_generator = PayloadGenerator(
        repo=repo, pr_number=pr_number
    )
    try:
        pr_payload = payload_generator.generate_payload()
    except Exception as e:
        print(f"❌ Error generating payload: {e}")
        sys.exit(1)
    
    bot_runner = BotRunner(config=config, payload=pr_payload)
    pr_id = bot_runner._pr_data.id
    config.setup_pr_related_dirs(pr_id, pr_payload)
    generation_completed = False
    for model in llms:
        if generation_completed:
            break
        model = cast(LLM, model)
        config.setup_output_dir(0, model)
        generation_completed = bot_runner.execute_runner(0, model)
    
    if generation_completed:
        print("✅ Test generation completed successfully.")
        new_filename = (f"{bot_runner._execution_id}_{config.output_dir.name}.txt") # type: ignore[attr-defined]
        comment_path = Path(config.pass_generation_dir, "comment_incl_coverage.txt") # type: ignore[attr-defined]
        if comment_path.exists():
            comment_content = comment_path.read_text(encoding="utf-8")
            print(f"\nComment with Coverage Info:\n\n{comment_content}\n\n")
        else:
            generated_test = Path(config.gen_test_dir, new_filename).read_text(encoding="utf-8")
            print(f"\nGenerated Test Content:\n\n{generated_test}\n\n")
        print(f"Check out the further information in: {config.pass_generation_dir}")  # type: ignore[attr-defined]
    else:
        print("❌ Test generation did not complete successfully.")   
    bot_runner.teardown()

def delete_bot_from_system(repo: Path):
    confirmation = input(
        "⚠️  This will delete the entire repository and remove the 'testgen' alias. Continue? (y/n): "
    ).strip().lower()
    
    if confirmation != "y":
        print("❌ Deletion cancelled.")
        sys.exit(0)
    
    # Remove shell alias from both .zshrc and .bashrc
    home = Path.home()
    shell_configs = [home / ".zshrc", home / ".bashrc"]
    
    alias_removed = False
    for config_path in shell_configs:
        if config_path.exists():
            with open(config_path, "r") as f:
                lines = f.readlines()
            
            # Filter out the testgen alias
            new_lines = [line for line in lines if "alias testgen=" not in line]
            
            # Only write if changes were made
            if len(new_lines) != len(lines):
                with open(config_path, "w") as f:
                    f.writelines(new_lines)
                
                print(f"✅ Removed 'testgen' alias from {config_path.name}")
                alias_removed = True
    
    if not alias_removed:
        print("⚠️  No 'testgen' alias found in shell configuration files")
    
    # Remove the repository directory
    remove_directory(repo)
        
    
def main():
    parser = argparse.ArgumentParser(
        description=CLI_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "command", nargs="?", default="help", help="Command to execute (e.g., run)"
    )
    parser.add_argument(
        Commands.RUN, nargs="?", help="Command to execute (e.g., run)"
    )
    parser.add_argument(
        RunFlags.PULL_REQUEST.value[0],
        RunFlags.PULL_REQUEST.value[1],
        nargs=1,
        type=int,
        help="Specify pull request number to analyze",
    )
    parser.add_argument(
        Commands.DELETE,
        nargs="?",
        help="Delete the CLI tool from the system",
    )
    parser.add_argument(
        Commands.CLEAR,
        nargs="?",
        help="Remove all cached data from previous runs",
    )
    parser.add_argument(
        Commands.CONFIGURE, nargs="?", help="Reconfigure API keys and settings"
    )
    parser.add_argument(
        RunFlags.LLMS_USED.value[0],
        nargs=1,
        type=str,
        default=ALLOWED_MODELS,
        help="Specify which LLMs to use (comma-separated)",
    )
    parser.add_argument(
        RunFlags.NUMBER_INVOCATIONS.value[0],
        RunFlags.NUMBER_INVOCATIONS.value[1],
        nargs=1,
        type=int,
        default=3,
        help="Number of invocations per LLM model",
    )

    args = parser.parse_args()
    repo = Path(__file__).parent

    # 1. Check Git Context
    remote_url = get_git_remote()

    if not remote_url:
        print("Error: You must run 'testgen' inside a git repository.")
        sys.exit(1)

    # 2. Validate Repository Link
    if not is_valid_repo(remote_url):
        print(
            f"Error: This repository ({remote_url}) is not linked to grcov, glean, or rust-code-analysis."
        )
        sys.exit(1)
        
    repository_name = next(repo for repo in ALLOWED_REPOS if repo in remote_url)

    print(f"✅ Verified repository: {remote_url}")

    # 3. Execute Bot Logic
    if args.command == "run":
        print("🚀 Starting test generation...")
        run_bot(repository_name, args)
        sys.exit(0)

    # create .env and prompt user for API keys
    elif args.command == "configure":
        print("⚙️  Starting configuration...")
        update_env_variables()
        sys.exit(0)

    # Remove entire directory where cli.py is located
    elif args.command == "delete":
        print("🗑️  Deleting CLI tool...")
        delete_bot_from_system(repo)
        print("✅ Successfully deleted the CLI tool and repository")
        sys.exit(0)

    # Remove bot_logs and generated_tests directories
    elif args.command == "clear":
        print("🧹 Clearing cached data...")
        logs_dir = Path(repo, "bot_logs")
        tests_dir = Path(repo, "generated_tests")
        remove_directory(logs_dir)
        remove_directory(tests_dir)
        print("✅ Successfully cleared cached data")
        sys.exit(0)

    # Unrecognized command
    else:
        print("❌ Unrecognized command.")
        parser.print_help()
        sys.exit(1)
        


if __name__ == "__main__":
    main()
