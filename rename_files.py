from pathlib import Path
from typing import Literal

type Repo = Literal["grcov", "rust-code-analysis"]

def move_and_rename_files():
    source_folder = Path(Path.cwd(), "scrape_mocks", "code_only").glob("*.json")
    grcov_target_folder = Path(Path.cwd(), "webhook_handler", "test", "test_data", "grcov")
    rust_code_analysis_target_folder = Path(Path.cwd(), "webhook_handler", "test", "test_data", "rust-code-analysis")

    for file in source_folder:
        file_name = file.as_posix().split("/")[-1]
        if "grcov" in file_name:
            identifier: Repo = "grcov"
            target_folder = grcov_target_folder
        elif "rust-code-analysis" in file_name:
            identifier: Repo = "rust-code-analysis"
            target_folder = rust_code_analysis_target_folder
        else: 
            raise Exception("No identifier found")
        
        pr_num = file_name.split(".json")[0].lstrip(f"{identifier}_")
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

            
if __name__ == "__main__":
    print("[*] Moving and renaming files...")
    move_and_rename_files()
    print("[*] Moving and renaming successful.")