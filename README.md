# GH-Bot Rust

This project represents a tool for automated regression test generation for Rust. It does so by analyzing a pull request along its accompanying issue and querying an LLM to produce a regression test to ensure that the issue has been resolved. It is inspired by prior versions for [JavaScript](https://github.com/maettuu/Thesis-on-Test-Generation-Using-LLMs) and [Python](https://github.com/maettuu/Thesis-on-Test-Generation-Using-LLMs/tree/6e3d8a2be3be19a24efaae3742848d726653d073). Currently, there is support for automated test generation using a webhook and manual generation using the CLI-tool.

## Overview

The bot automates the process of generating unit tests for Rust pull requests by:

1. **Analyzing PR Context**: Fetches PR data, linked issues, and code changes
2. **Building Docker Environments**: Creates isolated testing environments for each repository
3. **Generating Tests with LLMs**: Uses multiple LLM models to generate test code
4. **Validating Tests**: Compiles, runs, and verifies test correctness
5. **Measuring Coverage**: Calculates line coverage improvements
6. **Iterative Refinement**: Automatically fixes compilation errors and assertion failures

## Prerequisites

- **Python ≥ 3.12**
- **Git**
- **Docker & Docker Engine**
- **GitHub Token** with repo read/write permissions
- **API Keys** for `openai` and `groq`

To set up a GitHub Token follow these steps.

1. **Create new Token**
   1. In GitHub, open your profile settings.
   2. In the left sidebar, select **Developer Settings**.
   3. In the left sidebar, expand **Personal access tokens**.
   4. In the left sidebar, select **Tokens (classic)**.
   5. Click **Generate new token** and select **Generate new token (classic)**.
2. **Configure Token**
   1. Give your token a name.
   2. Set an expiration date.
3. **Configure Scope**
   1. Select only the scope **public_repo** under **repo**.
4. **Save and verify**
   1. Click **Generate token**.
   2. The setup is completed. In the tokens list you will now find the entry: `<NAME>` — _public_repo_

---

## Local Setup

1. **Clone the repo**
   ```bash
   git clone --branch main --single-branch https://github.com/LiamK21/GH-bot-Rust.git ~/main
   cd main
   ```
   _Hint:_ To always pull from the same branch, configure git upstream as follows:
   ```bash
   git branch --set-upstream-to=origin/main main
   ```
   Now you can run `git pull` to simply update the single branch. You can verify this configuration with:
   ```bash
    git branch -vv
   ```
2. **Environment file**

   ```bash
   cp .env.example .env
   ```

   Populate all environment variables: `GITHUB_WEBHOOK_SECRET`, `GITHUB_TOKEN`, `OPENAI_API_KEY`, `GROQ_API_KEY`.

3. **Install dependencies**
   ```bash
   python -m venv .main-venv
   source .main-venv/bin/activate
   pip install -r requirements.txt
   ```

---

## Server Setup

1. **Connect to your server (e.g., using SSH)**
   ```bash
   ssh -i ~/.ssh/<PUBLIC_KEY> <USER>@<SERVER_IP>
   ```
2. **(Optional) Install `DeadSnakes` to manage multiple `Python` versions**
   ```bash
   sudo apt update && sudo apt install software-properties-common
   sudo add-apt-repository ppa:deadsnakes/ppa
   ```
3. **Install `Python3.12` and `nginx`**
   ```bash
   sudo apt install python3.12 python3.12-venv python3.12-dev
   sudo apt install nginx
   ```
4. **Clone the repo**
   ```bash
   git clone --branch main --single-branch https://github.com/maettuu/Thesis-on-Test-Generation-Using-LLMs.git ~/main
   cd main
   ```
   _Hint:_ To always pull from the same branch, configure git upstream as follows:
   ```bash
   git branch --set-upstream-to=origin/main main
   ```
   Now you can run `git pull` to simply update the single branch. You can verify this configuration with:
   ```bash
    git branch -vv
   ```
5. **Environment file**

   ```bash
   cp .env.example .env
   ```

   Populate all environment variables: `GITHUB_WEBHOOK_SECRET`, `GITHUB_TOKEN`, `OPENAI_API_KEY`, `GROQ_API_KEY`.

6. **Install dependencies & migrate**
   ```bash
   python3.12 -m venv .main-venv
   source .main-venv/bin/activate
   pip install -r requirements.txt
   python manage.py migrate
   deactivate
   ```
7. **Configure `nginx`**

   Create a configuration file:

   ```bash
   sudo nano /etc/nginx/sites-available/django_github_bot.conf
   ```

   Paste the following contents:

   ```text
   server {
     listen 80;
     server_name <SERVER_IP>;

     location /webhook-js/ {
       proxy_pass http://127.0.0.1:8000;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
     }

     location /healthz-js/ {
       proxy_pass http://127.0.0.1:8000/healthz-js/;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
     }
   }
   ```

   _Hint:_ If you already have proxies configured you can use that configuration file and simply add the new locations. \
   Next, enable the proxy and restart `nginx`:

   ```bash
   sudo ln -s /etc/nginx/sites-available/django_github_bot /etc/nginx/sites-enabled/
   sudo systemctl restart nginx
   ```

   Requests to `http://<SERVER_IP>/webhook-js/` are now served on `http://127.0.0.1:8000` on your server.
   We can now bind a `systemd` service to port `8000` using `Gunicorn` to connect the `Django` bot.

8. **Configure `systemd` service**

   Create a new service file:

   ```bash
   sudo nano /etc/systemd/system/django_github_bot_js.service
   ```

   Paste the following contents:

   ```text
   [Unit]
   Description=Django GitHub-Bot Javascript
   After=network.target

   [Service]
   User=<USER>
   Group=<GROUP>
   WorkingDirectory=<PATH/TO/main/>
   EnvironmentFile=<PATH/TO/main/.env>
   ExecStart=<PATH/TO/main/.main-venv/bin/gunicorn> \
     --workers 3 \
     --timeout 1800 \
     --bind 0.0.0.0:8000 \
     --capture-output  \
     github_bot.wsgi
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

   Reload the daemon, enable and start the service:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable django_github_bot_js
   sudo systemctl start django_github_bot_js
   ```

   If not done already open the following firewall ports:

   ```bash
   sudo ufw allow OpenSSH
   sudo ufw allow 80/tcp
   sudo ufw enable
   ```

   Any requests are now successfully forwarded and processed. \
   _Hint:_ Remember to restart your service whenever you `git pull` any changes to
   have your `Gunicorn` workers run the updated code.

   ```bash
   sudo systemctl restart django_github_bot_js
   ```

   _Hint:_ You can follow the logs of your service as follows:

   ```bash
   sudo journalctl -u django_github_bot_js --follow
   ```

   _Hint:_ You can follow the log file `bootstrap.log` as follows:

   ```bash
   tail -f bootstrap.log
   ```

   _Hint:_ Test your setup as follows:

   ```bash
   curl -i http://<SERVER_IP>/webhook-js/
   curl -i http://<SERVER_IP>/healthz-js/
   ```

9. **Disconnect from your server**
   ```bash
   exit
   ```

---

## Webhook Setup

1. **Add webhook to repository**

   1. In GitHub, open the target repository.
   2. Open the tab **Settings**.
   3. In the left sidebar, select **Webhooks**.
   4. Click **Add webhhook**.

2. **Configure webhook**

| Field                | Value                         |
| -------------------- | ----------------------------- |
| **Payload URL**      | `http://<SERVER_IP>/webhook/` |
| **Content type**     | `application/json`            |
| **Secret**           | `<WEBHOOK_SECRET>`            |
| **SSL verification** | _Keep enabled_                |

3. **Configure triggers**

   1. Select **Let me select individual events.**
   2. Tick only **Pull requests**, leave everything else unchecked.

4. **Save and verify**
   1. Keep the checkbox **Active** ticked.
   2. Click **Add webhook**.
   3. The setup is completed. In the webhooks list you will now find the entry: \
      `http://<SERVER_IP>/webhook-js/` _(pull_request)_

---

## TestGen CLI Tool

The CLI tool enables locally running the bot to generate a test.

### Installation

1. Clone the repository: See Local Setup

2. Setup a Python3.12 virtual environment named `.venv`

   ```bash
   python3.12 -m venv .venv
   ```

3. Install the required dependencies

   ```bash
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. Run the installation script:

   ```bash
   ./install.sh
   ```

   The installer will:

   - Check for Python 3.12
   - Check for a virtual environment named `.venv`
   - Prompt you to configure API keys

5. Restart your shell or source your config file:
   ```bash
   source ~/.zshrc  # for zsh
   source ~/.bashrc # for bash
   ```

### Configuration

Configure your API keys using:

```bash
testgen configure
```

You'll be prompted to enter:

- GitHub Token
- OpenAI API Key
- Groq API Key

### Usage

#### Generate Tests for a Pull Request

Navigate to one of the supported repositories and run:

```bash
testgen run -pr <PR_NUMBER> [OPTIONS]
```

**Options:**

- `-pr, --pull-request <NUMBER>` (required): Pull request number to analyze
- `--llms <MODEL>`: Specify which LLMs to use (comma-separated). Default: all models
  - Available: `gpt-4o`, `llama-3.3-70b-versatile`, `qwen3-32b`
- `-n, --num-invocations <NUMBER>`: Number of invocations per LLM model. Default: 3

**Examples:**

```bash
# Generate tests for PR #1180 using all models
testgen run -pr 1180

# Use only GPT-4o with 5 invocations
testgen run -pr 1180 --llms gpt-4o -n 5

# Use multiple specific models
testgen run -pr 1180 --llms gpt-4o,llama-3.3-70b-versatile
```

#### Clear Cached Data

Remove generated tests and logs:

```bash
testgen clear
```

This removes:

- `bot_logs/` directory
- `generated_tests/` directory

#### Reconfigure API Keys

Update your API credentials:

```bash
testgen configure
```

### Uninstall

Remove the CLI tool and repository:

```bash
testgen delete
```

This will:

- Remove the `testgen` alias from your shell configuration
- Delete the entire repository directory

### Output

After successful test generation, the tool will:

1. Display the generated test content in the terminal
2. Save detailed information in `bot_logs/<repo>/<pr_number>_<timestamp>/`
3. Store generated tests in `generated_tests/`

## Build Independently

### Build Docker Image

Head of repository (latest commit)

```bash
docker build -f dockerfiles/Dockerfile_<repository> -t gh-bot_<repository>_img .
```

Specific commit

```bash
docker build -f dockerfiles/Dockerfile_<repository> --build-arg commit_hash=<commit_hash> -t gh-bot_<repository>_img .
```

### Run in Detached Mode

```bash
docker run -dit --name gh-bot_<repository>_ctn gh-bot_<repository>_img bash
```

### Connect to Container with Bash

```bash
docker exec -it gh-bot_<repository>_ctn bash
```

### Stop & Restart the Container

```bash
docker stop gh-bot_<repository>_ctn
docker start -ai gh-bot_<repository>_ctn
```

---

## Webhook Explained

- **Endpoint:** `POST /webhook-js/`
- **Signature:** Verifies `X-Hub-Signature-256` with `GITHUB_WEBHOOK_SECRET`.
- **Events:** Listens to PR events (`opened`, `synchronize`, etc.).
- **Flow:**
  1. Parse PR metadata.
  2. Fetch linked issue.
  3. Clone the repo.
  4. Slice golden code around diffs.
  5. Fetch file for test injection.
  6. Build a Docker container.
  7. Execute `TestGenerator` → LLM.
  8. Post review comments containing generated test.

---

## Key Components

- **Django App (`github_bot/`)**

  - Exposes `POST /webhook/` for GitHub PR events, verifies signatures, and dispatches to the pipeline.

- **Webhook (`webhook.py`)**

  - Entry point for any request sent to the server.

- **Pipeline (`bot_runner.py`)**

  - Coordinates every step in the flow.

- **Tests (`test/`)**
  - Mock PR payloads and assertions on generated test output.

### helper/

- **`custom_errors.py`**: Custom exception classes for pipeline error handling (ExecutionError, DockerError, etc.)
- **`general.py`**: General utility functions for file operations and common tasks
- **`git_diff.py`**: Git diff parsing and manipulation utilities
- **`logger.py`**: Custom logging configuration with marker/success level methods
- **`templates.py`**: Prompt templates for LLM interactions and GitHub PR comments

### models/

- **`llm_enum.py`**: Enum defining available LLM models (GPT4o, LLAMA, QWEN3)
- **`llm_response.py`**: Structure for LLM API responses with parsed test code
- **`pipeline_inputs.py`**: Compact schema aggregating all pipeline input data
- **`pr_data.py`**: Schema for GitHub Pull Request webhook payloads and metadata
- **`pr_file_diff.py`**: Representation of file changes (before/after) in a PR
- **`prompt_type_enum.py`**: Enum for different prompt types (INITIAL, COMPILATION_ERROR, LINTING_ISSUE, ASSERTION_ERROR)
- **`test_coverage.py`**: Data structure for line coverage metrics and improvements

### services/

- **`config.py`**: Centralizes configuration (API keys, directories, LLM settings, Tree-sitter parser)
- **`cst_builder.py`**: Concrete Syntax Tree operations using Tree-sitter for Rust code parsing and test insertion
- **`docker_service.py`**: Docker operations for building images, running containers, executing tests, and measuring coverage
- **`gh_service.py`**: GitHub API client for fetching PR data, files, commits, and posting comments
- **`llm_handler.py`**: LLM client management for OpenAI and Groq APIs with prompt building
- **`pr_diff_context.py`**: Context manager for PR file diffs with filtering and patch generation
- **`test_generator.py`**: Main pipeline orchestrator for test generation, validation, compilation, execution, and coverage measurement

---

## Possible Configurations

- **`self.parse_language`**  
  The Tree-sitter language to use for parsing source files (e.g. `"javascript"`, `"typescript"`, `"python"`, etc.).

- **`self.MAX_LLM_CALLS`**  
  The maximum number of LLM calls until the bot stops entering the refinement process.

- **`self.bot_log_dir`**  
  Filesystem path where the bot should write its execution logs.

- **`self.gen_test_dir`**  
  Filesystem path where generated test files should be saved.

---

## Adding a New Test Payload

1. **Mock Payload**  
   Place your PR JSON under:

   ```text
   webhook_handler/test/test_data/<repo>_<pr_id>.json
   ```

2. **Test Case**  
   In `webhook_handler/test/tests_<repository>.py`:

   ```python
   class TestGeneration<PR_ID>(TestCase):
    def setUp(self):
        self.payload = _get_payload("test_data/<repository>/_<pr_id>.json")
        self.config = Config()
        self.runner = BotRunner(self.payload, self.config)
        _setup_dirs(self.config, self.runner, self.payload)

    def tearDown(self):
        self.runner.teardown()
        del self.payload
        del self.config
        del self.pipeline

    def test_generation<pr_id>(self):
       generation_completed = False
       for model in USED_MODELS:
            if generation_completed:
                break
            self.config.setup_output_dir(0, model)
            generation_completed = self.runner.execute_runner(0, model)

       self.assertTrue(generation_completed)
   ```

3. **Run**
   ```bash
   python manage.py test webhook_handler.test.tests_<repository>:TestGeneration<PR_ID>
   ```

---

## Models Used

- **OpenAI from openai:** GPT-4o
- **Groq from groq:** llama-3.3-70b-versatile, qwen3-32b

_With this setup, every Pull Request triggers automated, AI-driven regression tests—helping catch regressions early and reducing manual QA overhead._

---

## Supported Repositories

- [grcov](https://github.com/mozilla/grcov)
- [glean](https://github.com/mozilla/glean)
- [rust-code-analysis](https://github.com/mozilla/rust-code-analysis)

## License

This project is released under the MIT License. Upon usage in any way include the original copyright and license notice in all copies or substantial portions of the software. The software is provided "as is", without warranty of any kind.
