import json
import re
import sys
from enum import StrEnum
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# The idea here is to have a script that can be run to evaluate an offline evaluation run (directory)
# It should probably create a couple of files that contain the major data points we want to track
# From there, it should be easy to create graphs and such

# The metrics should be taken from the card sorting evaluation

type PieChartData = dict[str, int]
type StackedBarChartData = dict[str, dict[str, int]]
type HorizontalBarChartData = dict[str, dict[str, int]]


class Model(StrEnum):
    GPT_4O = "gpt-4o"
    DEEPSEEK = "deepseek-r1-distill-llama-70b"
    LLAMA = "llama-3.3-70b-versatile"


class Repository(StrEnum):
    GLEAN = "glean"
    GRCOV = "grcov"
    NEQO = "neqo"
    RCA = "rust-code-analysis"


def main(eval_dir: Path, plot_dir: Path):
    plotting_data_file = Path(eval_dir, "plotting_data.json")
    content: dict = {}
    with open(plotting_data_file, "r") as f:
        content = json.load(f)

    # Pie Chart
    pie_chart_data: PieChartData = content.get("pie_chart", {})
    if pie_chart_data:
        _plot_pie_chart(pie_chart_data, plot_dir)

    # Stacked Bar Chart
    stacked_bar_chart_data: StackedBarChartData = content.get("stacked_bar_chart", {})
    if stacked_bar_chart_data:
        _plot_stacked_bar_chart(stacked_bar_chart_data, plot_dir)

    # Horizontal Bar Chart
    horizontal_bar_chart_data: HorizontalBarChartData = content.get(
        "horizontal_bar_chart", {}
    )
    if horizontal_bar_chart_data:
        _plot_horizontal_bar_chart(horizontal_bar_chart_data, plot_dir)


def _plot_pie_chart(data: PieChartData, plot_dir: Path):
    labels, sizes = zip(*data.items())
    fig, ax = plt.subplots()
    ax.title.set_text("Distribution of Fail-to-Pass Tests by Repository")
    colors = ["#45B7D1", "#96CEB4", "#FECA57", "#FF9FF3"]
    ax.pie(
        sizes,
        labels=labels,
        autopct="%1.1f%%",
        startangle=90,
        colors=colors[: len(labels)],
        textprops={"color": "white", "fontweight": "400"},
    )
    ax.legend(bbox_to_anchor=(1.22, 1.0), loc="upper right")
    plt.tight_layout()
    fig.savefig(fname=plot_dir / "pie_chart.png", bbox_inches="tight")


def _plot_stacked_bar_chart(data: StackedBarChartData, plot_dir: Path):
    labels = list(data.keys())
    model_to_test: dict[str, list[int]] = {}
    for _, tests in data.items():
        for model, count in tests.items():
            capitalize_model = model.capitalize()
            if capitalize_model not in model_to_test:
                model_to_test[capitalize_model] = []
            model_to_test[capitalize_model].append(count)

    weight_counts = {}
    for model, counts in model_to_test.items():
        weight_counts[model] = np.array(counts)

    fig, ax = plt.subplots()
    bottom = np.zeros(len(labels))
    colors = ["#96CEB4", "#FF9FF3", "#45B7D1"]
    color_index = 0

    for model, counts in weight_counts.items():
        bars = ax.bar(
            labels,
            counts,
            bottom=bottom,
            label=model,
            color=colors[color_index % len(colors)],
        )
        color_index += 1

        # Add text labels with exact numbers inside the bars
        for i, (bar, count) in enumerate(zip(bars, counts)):
            if count > 0:  # Only show label if count is greater than 0
                height = count / 2  # Position text in the middle of the bar segment
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    bottom[i] + height,
                    str(count),
                    ha="center",
                    va="center",
                    fontweight="400",
                    color="white",
                )

        bottom += counts
    ax.legend(loc="upper right", bbox_to_anchor=(1.15, 1))
    ax.title.set_text("Distribution of Fail-to-Pass Tests by Model and Repository")
    plt.tight_layout()
    fig.savefig(fname=plot_dir / "stacked_bar_chart.png", bbox_inches="tight")


def _plot_horizontal_bar_chart(data: HorizontalBarChartData, plot_dir: Path):
    for identifier, failure_data in data.items():
        labels, sizes = zip(*failure_data.items())
        y_pos = np.arange(len(labels))
        error = np.random.rand(len(labels))
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.barh(y_pos, sizes, xerr=error, align="center")
        ax.set_yticks(y_pos, labels=labels)
        ax.set_yticklabels(labels)
        ax.invert_yaxis()  # labels read top-to-bottom
        ax.title.set_text(f"Failure Types for {identifier}")
        fig.savefig(
            fname=plot_dir / f"horizontal_bar_chart_{identifier}.png",
        )


def _setup_dirs(eval_dir_name: str) -> Path:
    plots_dir = Path(Path.cwd(), "plots")
    if not plots_dir.exists():
        plots_dir.mkdir(parents=True, exist_ok=True)

    plot_eval_dir = Path(plots_dir, eval_dir_name)
    if not plot_eval_dir.exists():
        plot_eval_dir.mkdir(parents=True, exist_ok=True)
    return plot_eval_dir


def _validate_cli_input(args: list[str]) -> Path:
    if not args or len(args) != 1:
        print("[!] Error: Use python specific_eval.py <Evaluation directory name>")
        sys.exit(1)
    evaluation_dir = args[0]
    evaluation_dir_path = Path(Path.cwd(), evaluation_dir)

    if not evaluation_dir_path.exists():
        print(f"[!] Error: Evaluation directory {evaluation_dir} does not exist.")
        sys.exit(1)
    return evaluation_dir_path


if __name__ == "__main__":
    sys_args = sys.argv[1:]
    path_to_evaluation_dir = _validate_cli_input(sys_args)
    path_to_plotting_dir = _setup_dirs(path_to_evaluation_dir.name)
    main(path_to_evaluation_dir, path_to_plotting_dir)
