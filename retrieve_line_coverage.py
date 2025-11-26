import json
import os
import sys
import time
from pathlib import Path


def main(rel_filename) -> float:
    path_to_json = Path(Path.cwd(), "coverage.json")
    timeout = 10
    while not path_to_json.exists() and timeout > 0:
        timeout -= 1
        time.sleep(1)
    if not path_to_json.exists():
        raise Exception("Coverage file not found")
    with open(path_to_json, "r") as f:
        data = json.load(f)

    # First "data" entry contains coverage results
    coverage_data = data["data"][0]

    if rel_filename:
        for file in coverage_data["files"]:
            fname = file["filename"]
            if rel_filename not in fname:
                continue

            lines = file["summary"]["lines"]
            percent: float = lines["percent"]
            return percent
        raise Exception(f"File {rel_filename} not found in coverage data")

    total_lines = coverage_data["totals"]["lines"]
    percent: float = total_lines["percent"]
    return percent


if __name__ == "__main__":
    if len(sys.argv) > 2:
        print("Usage: python retrieve_line_coverage.py (<filename>)")
        print(
            " <filename>: is the relative path to a file; optional; if not provided, the script will return total line coverage"
        )
        sys.exit(1)

    filename = sys.argv[1] if len(sys.argv) == 2 else None
    val = main(filename)
    print(f"{val:.2f}")
