from pathlib import Path

grcov_folder = Path("scrape_mocks", "code_only").glob("*.json")
grcov_target_folder = Path(Path.cwd(), "webhook_handler", "test", "test_data", "grcov")

for file in grcov_folder:
    file_name = file.as_posix().split("/")[-1]
    pr_num = file_name.split(".json")[0].lstrip("grcov_")[1]
    pr_num_int = int(pr_num)
    if not pr_num_int:
        raise Exception("No pr number found")
    new_name = f"pr_{pr_num_int}.json"

    file_content = ""

    with open(file, mode="r", encoding="utf-8") as f:
        file_content = f.read()

    if not file_content:
        raise Exception("No file content")

    absolute_file_path = Path(grcov_target_folder, new_name)
    absolute_file_path.touch(exist_ok=True)

    with open(absolute_file_path, mode="w") as f:
        f.write(file_content)
        
        
rust_code_analysis_folder = Path("scrape_mocks", "code_only").glob("*.json")
rust_code_analysis_target_folder = Path(Path.cwd(), "webhook_handler", "test", "test_data", "rust_code_analysis")

for file in grcov_folder:
    file_name = file.as_posix().split("/")[-1]
    pr_num = file_name.split(".json")[0].lstrip("rust-code-analysis_")[1]
    pr_num_int = int(pr_num)
    if not pr_num_int:
        raise Exception("No pr number found")
    new_name = f"pr_{pr_num_int}.json"

    file_content = ""

    with open(file, mode="r", encoding="utf-8") as f:
        file_content = f.read()

    if not file_content:
        raise Exception("No file content")

    absolute_file_path = Path(grcov_target_folder, new_name)
    absolute_file_path.touch(exist_ok=True)

    with open(absolute_file_path, mode="w") as f:
        f.write(file_content)
