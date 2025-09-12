import sys
from pathlib import Path
from typing import Literal

type Repo = Literal["grcov", "rust-code-analysis", "glean", "neqo"]

grcov_target_folder = Path(Path.cwd(), "webhook_handler", "test", "test_data", "grcov")
rust_code_analysis_target_folder = Path(Path.cwd(), "webhook_handler", "test", "test_data", "rust-code-analysis")
glean_target_folder = Path(Path.cwd(), "webhook_handler", "test", "test_data", "glean")
neqo_target_folder = Path(Path.cwd(), "webhook_handler", "test", "test_data", "neqo")

def move_and_rename_files(repos: list[Repo]):
    source_folder = Path(Path.cwd(), "scrape_mocks", "code_only").glob("*.json")
    for file in source_folder:
        file_name = file.stem
        repository = file_name.split("_")[0]
        if repository in repos:
            target_folder = next((v for k, v in globals().copy().items() if k.startswith(f"{repository}")), None)
            if not target_folder: raise Exception("No target folder found")
        else: 
            print(f"[!] Skipping file {file_name} as its repository {repository} is not in the provided list.")
            continue
        
        pr_num = file_name.split(".json")[0].lstrip(f"{repository}_")
        pr_num_int = int(pr_num)
        if not pr_num_int:
            raise Exception("No pr number found")
        new_name = f"pr_{pr_num_int}.json"

        file_content: str = ""

        with open(file, mode="r", encoding="utf-8") as f:
            file_content = f.read()

        if not file_content:
            raise Exception("No file content")

        absolute_file_path = Path(target_folder, new_name)
        absolute_file_path.touch(exist_ok=True)

        with open(absolute_file_path, mode="w") as f:
            f.write(file_content)

def _validate_passed_args(args: list[str]) -> bool:
    if len(args) == 0:
        print("Usage: python rename_files.py [repository, repository...]")
        print("Available repositories: grcov, rust-code-analysis, glean, neqo")
        sys.exit(1)
   
    valid_repos = ["grcov", "rust-code-analysis", "glean", "neqo"]
    for arg in args:
        if arg not in valid_repos:
            print(f"[!] Invalid repository: {arg}")
            print("Usage: python python rename_files.py [repository, repository...]")
            print("Available repositories: grcov, rust-code-analysis, glean, neqo")
            sys.exit(1)
    return True
  
            
if __name__ == "__main__":
    repos: list[Repo] = []
    cli_args = sys.argv[1:]
    _validate_passed_args(cli_args)
    
    if "grcov" in cli_args:
        repos.append("grcov")
    if "rust-code-analysis" in cli_args:
        repos.append("rust-code-analysis")
    if "glean" in cli_args:
        repos.append("glean")
    if "neqo" in cli_args:
        repos.append("neqo")
    print("[*] Moving and renaming files...")
    move_and_rename_files(repos)
    print("[*] Moving and renaming successful.")