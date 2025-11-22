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
    "It uses LLM models from the OpenAI and Groq APIs to generate unit tests on pull requests.\n\n"
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


class TestGenCLI:
    def __init__(self):
        self.repo_path = Path(__file__).parent
        self.parser = self._setup_parser()
        self.args: argparse.Namespace = argparse.Namespace()
        self.repository_name: str = ""

    def _setup_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            description=CLI_DESCRIPTION,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "command", nargs="?", default="help", help="Command to execute (e.g., run)"
        )
        parser.add_argument(
            RunFlags.PULL_REQUEST.value[0],
            RunFlags.PULL_REQUEST.value[1],
            nargs=1,
            type=int,
            help="Specify pull request number to analyze",
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
        return parser

    def _get_git_remote(self) -> str | None:
        """Retrieves the remote origin URL of the current git repo."""
        try:
            url = (
                subprocess.check_output(["git", "config", "--get", "remote.origin.url"])
                .decode("utf-8")
                .strip()
            )
            return url
        except subprocess.CalledProcessError:
            return None

    def _is_valid_repo(self, url: str) -> bool:
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

    def _remove_directory(self, dir_path: Path):
        """Removes a directory and all its contents."""
        try:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                print(f"✅ Successfully removed directory: {dir_path}")
            else:
                print(f"⚠️  Directory does not exist: {dir_path}")
        except Exception as e:
            print(f"❌ Error removing directory: {e}")

    def _parse_llms(self, llms: list[str] | str) -> list[str]:
        """Parse LLM argument into a list of valid LLMs."""       
        if isinstance(llms, list) and len(llms) == 1 and isinstance(llms[0], str):
            llms_str = llms[0]
            if "," in llms_str:
                llms = llms_str.split(",")
            else:
                llms = [llms_str]
        elif isinstance(llms, str):
            llms = llms.split(",")

        return [
            llm.strip() for llm in llms if llm.strip() and llm.strip() in ALLOWED_MODELS
        ]

    def handle_configure(self):
        """Updates environment variables from .env file."""
        print("⚙️  Starting configuration...")
        load_dotenv()

        if not self.repo_path.exists():
            print(f"❌ Directory does not exist: {self.repo_path}")
            sys.exit(1)

        env_path = self.repo_path / ".env"
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
        sys.exit(0)

    def handle_run(self):
        print("🚀 Starting test generation...")

        if not self.args.pull_request:
            print("❌ Error: --pull-request argument is required for 'run' command.")
            sys.exit(1)

        pr_number = self.args.pull_request[0]

        # Handle num_invocations which might be a list due to nargs=1 or int due to default
        num_invocations = self.args.num_invocations
        if isinstance(num_invocations, list):
            num_invocations = num_invocations[0]

        # Handle llms which might be a list due to nargs=1 or list due to default
        llms = self.args.llms
        llms = self._parse_llms(llms)

        if not llms:
            print(
                f"❌ Error: No valid LLMs specified. Allowed: {', '.join(ALLOWED_MODELS)}"
            )
            sys.exit(1)

        config = Config(llm_calls=num_invocations)
        payload_generator = PayloadGenerator(
            repo=self.repository_name, pr_number=pr_number
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
            new_filename = f"{bot_runner._execution_id}_{config.output_dir.name}.txt"  # type: ignore[attr-defined]
            comment_path = Path(config.pass_generation_dir, "comment_incl_coverage.txt")  # type: ignore[attr-defined]
            if comment_path.exists():
                comment_content = comment_path.read_text(encoding="utf-8")
                print(f"\nComment with Coverage Info:\n\n{comment_content}\n\n")
            else:
                generated_test = Path(config.gen_test_dir, new_filename).read_text(
                    encoding="utf-8"
                )
                print(f"\nGenerated Test Content:\n\n{generated_test}\n\n")
            print(f"Check out the further information in: {config.pass_generation_dir}")  # type: ignore[attr-defined]
        else:
            print("❌ Test generation did not complete successfully.")
        bot_runner.teardown()
        sys.exit(0)

    def handle_delete(self):
        print("🗑️  Deleting CLI tool...")
        confirmation = (
            input(
                "⚠️  This will delete the entire repository and remove the 'testgen' alias. Continue? (y/n): "
            )
            .strip()
            .lower()
        )

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

                new_lines = [line for line in lines if "alias testgen=" not in line]

                if len(new_lines) != len(lines):
                    with open(config_path, "w") as f:
                        f.writelines(new_lines)

                    print(f"✅ Removed 'testgen' alias from {config_path.name}")
                    alias_removed = True

        if not alias_removed:
            print("⚠️  No 'testgen' alias found in shell configuration files")

        self._remove_directory(self.repo_path)
        print("✅ Successfully deleted the CLI tool and repository")
        sys.exit(0)

    def handle_clear(self):
        print("🧹 Clearing cached data...")
        logs_dir = self.repo_path / "bot_logs"
        tests_dir = self.repo_path / "generated_tests"
        self._remove_directory(logs_dir)
        self._remove_directory(tests_dir)
        print("✅ Successfully cleared cached data")
        sys.exit(0)

    def run(self):
        self.args = self.parser.parse_args()

        # Check CWD is inside a git repository and it is an allowed repo
        remote_url = self._get_git_remote()
        if not remote_url:
            print("Error: You must run 'testgen' inside a git repository.")
            sys.exit(1)
        if not self._is_valid_repo(remote_url):
            print(
                f"Error: This repository ({remote_url}) is not linked to grcov, glean, or rust-code-analysis."
            )
            sys.exit(1)

        self.repository_name = next(
            repo for repo in ALLOWED_REPOS if repo in remote_url
        )

        # Execute Bot Logic
        if self.args.command == Commands.RUN:
            self.handle_run()
        elif self.args.command == Commands.CONFIGURE:
            self.handle_configure()
        elif self.args.command == Commands.DELETE:
            self.handle_delete()
        elif self.args.command == Commands.CLEAR:
            self.handle_clear()
        else:
            print("❌ Unrecognized command.")
            self.parser.print_help()
            sys.exit(1)


if __name__ == "__main__":
    cli = TestGenCLI()
    cli.run()
