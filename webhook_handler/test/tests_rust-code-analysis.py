import json
import os
from pathlib import Path

import pytest

from webhook_handler.bot_runner import BotRunner
from webhook_handler.constants import USED_MODELS
from webhook_handler.services.config import Config


def _setup(payload: dict) -> tuple[Config, BotRunner]:
        config = Config()
        runner = BotRunner(payload, config)
        _setup_dirs(config, runner, payload)
        return config, runner

def _teardown(payload: dict, config: Config, runner: BotRunner) -> None:
        runner.teardown()
        del payload
        del config
        del runner


def _get_payload(rel_path: str) -> dict:
    abs_path = os.path.join(os.path.dirname(__file__), "test_data", "rust-code-analysis", rel_path)
    with open(abs_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload

def _setup_dirs(config: Config, runner: BotRunner, payload) -> None:
    pr_id = runner._pr_data.id
    config.setup_pr_related_dirs(pr_id, payload)
    

TEST_DIR = Path(Path.cwd(), "webhook_handler", "test", "test_data", "rust-code-analysis")
payload_files = [f.name for f in TEST_DIR.iterdir() if f.is_file() and f.suffix == ".json"]

payload_files = list(set(payload_files))
payload_files.sort(key=lambda x: int(x.removeprefix("pr_").removesuffix(".json")))

@pytest.mark.parametrize("filename", payload_files)
def test_generate_test(filename: str) -> None:
        payload = _get_payload(filename)
        config, runner = _setup(payload)
        generation_completed_arr: list[bool] = []
        for model in USED_MODELS:
            config.setup_output_dir(0, model)
            generation_completed = runner.execute_runner(0, model)
            generation_completed_arr.append(generation_completed)

        _teardown(payload, config, runner)
        assert True in generation_completed_arr