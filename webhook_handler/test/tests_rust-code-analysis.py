import json
import os

from django.test import TestCase

from webhook_handler.bot_runner import BotRunner
from webhook_handler.constants import USED_MODELS, get_total_attempts
from webhook_handler.models import LLM
from webhook_handler.services.config import Config


def _get_payload(rel_path: str) -> dict:
    abs_path = os.path.join(os.path.dirname(__file__), rel_path)
    with open(abs_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload

def _setup_dirs(config: Config, runner: BotRunner, payload) -> None:
    pr_id = runner._pr_data.id
    config.setup_pr_related_dirs(pr_id, payload)

#
# RUN With: python manage.py test webhook_handler.test.tests_rust-code-analysis.<testname>
#
class TestGeneration56(TestCase):
    def setUp(self) -> None:
        self.payload = _get_payload("test_data/rust-code-analysis/pr_56.json")
        self.config = Config()
        self.runner = BotRunner(self.payload, self.config)
        _setup_dirs(self.config, self.runner, self.payload)

    def tearDown(self) -> None:
        self.config._teardown()
        del self.payload
        del self.config
        del self.runner

    def test_generation56(self):
        generation_completed = False
        for model in USED_MODELS:
            if generation_completed:
                break
            self.config.setup_output_dir(0, model)
            generation_completed = self.runner.execute_runner(0, model)

        self.assertTrue(generation_completed)


class TestGeneration1028(TestCase):
    def setUp(self) -> None:
        self.payload = _get_payload("test_data/rust-code-analysis/pr_1028.json")
        self.config = Config()
        self.runner = BotRunner(self.payload, self.config)
        _setup_dirs(self.config, self.runner, self.payload)

    def tearDown(self) -> None:
        self.config._teardown()
        del self.payload
        del self.config
        del self.runner

    def test_generation1028(self):
        generation_completed = False
        for model in USED_MODELS:
            if generation_completed:
                break
            self.config.setup_output_dir(0, model)
            generation_completed = self.runner.execute_runner(0, model)

        self.assertTrue(generation_completed)


class TestGeneration620(TestCase):
    def setUp(self) -> None:
        self.payload = _get_payload("test_data/rust-code-analysis/pr_620.json")
        self.config = Config()
        self.runner = BotRunner(self.payload, self.config)
        _setup_dirs(self.config, self.runner, self.payload)

    def tearDown(self) -> None:
        self.config._teardown()
        del self.payload
        del self.config
        del self.runner

    def test_generation620(self):
        generation_completed = False
        for model in USED_MODELS:
            if generation_completed:
                break
            self.config.setup_output_dir(0, model)
            generation_completed = self.runner.execute_runner(0, model)

        self.assertTrue(generation_completed)

class TestGeneration1125(TestCase):
    def setUp(self) -> None:
        self.payload = _get_payload("test_data/rust-code-analysis/pr_1125.json")
        self.config = Config()
        self.runner = BotRunner(self.payload, self.config)
        _setup_dirs(self.config, self.runner, self.payload)

    def tearDown(self) -> None:
        self.config._teardown()
        del self.payload
        del self.config
        del self.runner

    def test_generation1125(self):
        generation_completed = False
        for model in USED_MODELS:
            if generation_completed:
                break
            self.config.setup_output_dir(0, model)
            generation_completed = self.runner.execute_runner(0, model)

        self.assertTrue(generation_completed)