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
    QWEN3 = "qwen/qwen3-32b"
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

    # Pass per LLM Call Chart
    pass_per_llm_call_data = content.get("pass_per_llm_call", {})
    if pass_per_llm_call_data:
        _plot_pass_per_llm_call(pass_per_llm_call_data, plot_dir)

    # Pass per LLM Call by Repository Chart
    pass_per_llm_call_by_repo_data = content.get("pass_per_llm_call_by_repo", {})
    if pass_per_llm_call_by_repo_data:
        _plot_llm_call_stacked_bar_chart(pass_per_llm_call_by_repo_data, plot_dir)

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

        
        for i, (bar, count) in enumerate(zip(bars, counts)):
            if count > 0: 
                height = count / 2
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
        ax.set_xlabel("Number of failures", fontweight=500, fontsize=11)
        ax.invert_yaxis()  # labels read top-to-bottom
        fig.savefig(
            fname=plot_dir / f"horizontal_bar_chart_{identifier}.png",
        )


def _plot_pass_per_llm_call(data: dict[str, list[int]], plot_dir: Path):
    """
    Plot a vertical bar chart showing the number of passed tests per LLM call iteration.
    
    Args:
        data: Dictionary mapping model names to arrays of 5 integers representing
              pass counts for LLM calls 1-5
        plot_dir: Directory to save the plot
    """
    llm_calls = ["Call 1", "Call 2", "Call 3", "Call 4", "Call 5"]
    x = np.arange(len(llm_calls))
    
    width = 0.25
    multiplier = 0
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    colors = {
        Model.GPT_4O: "#96CEB4",
        Model.LLAMA: "#FF9FF3",
        Model.QWEN3: "#45B7D1"
    }
    
    # Plot bars for each model
    for model_name, pass_counts in data.items():
        offset = width * multiplier
        bars = ax.bar(x + offset, pass_counts, width, 
                     label=model_name, 
                     color=colors.get(model_name, "#FECA57"))
        
        # Add value labels on top of each bar
        for bar in bars:
            height = bar.get_height()
            if height > 0:  # Only show label if count is greater than 0
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height + 0.5,
                    str(int(height)),
                    ha="center",
                    va="bottom",
                    fontweight="400",
                    fontsize=9
                )
        
        multiplier += 1
    
    # Customize the plot
    ax.set_xlabel("LLM Call Iteration", fontweight=500, fontsize=11)
    ax.set_ylabel("Number of F2PTs generated", fontweight=500, fontsize=11)
    ax.set_xticks(x + width)
    ax.set_xticklabels(llm_calls)
    ax.legend(loc="upper right", bbox_to_anchor=(1.0, 1.0))
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    fig.savefig(fname=plot_dir / "pass_per_llm_call.png", 
               bbox_inches="tight", dpi=300)
    plt.close(fig)


def _plot_llm_call_stacked_bar_chart(data: dict[str, list[int]], plot_dir: Path):
    """
    Plot a stacked bar chart showing tests passed at each LLM call iteration by repository.
    
    Args:
        data: Dictionary mapping repository names to arrays of 5 integers representing
              pass counts for LLM calls 1-5
        plot_dir: Directory to save the plot
    """
    repositories = list(data.keys())
    x = np.arange(len(repositories))
    
    call_colors = ["#bfdbfe", "#93c5fd", "#60a5fa", "#3b82f6", "#1e3a8a"]
    call_labels = ["Call 1", "Call 2", "Call 3", "Call 4", "Call 5"]
    
    fig, ax = plt.subplots(figsize=(10, 7))
    
    # Initialize bottom array for stacking
    bottom = np.zeros(len(repositories))
    
    # Plot each LLM call as a stack segment
    for call_idx in range(5):
        counts = np.array([data[repo][call_idx] for repo in repositories])
        
        bars = ax.bar(
            x,
            counts,
            bottom=bottom,
            label=call_labels[call_idx],
            color=call_colors[call_idx]
        )
        
        # Add text labels inside bars
        for i, (bar, count) in enumerate(zip(bars, counts)):
            if count > 0: 
                height = count / 2 
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    bottom[i] + height,
                    str(int(count)),
                    ha="center",
                    va="center",
                    fontweight="400",
                    color="white",
                    fontsize=10
                )
        
        bottom += counts
    
    # Customize the plot
    ax.set_xlabel("Repository", fontweight=500, fontsize=11)
    ax.set_ylabel("Number of F2PTs generated", fontweight=500, fontsize=11)
    ax.set_xticks(x)
    ax.set_xticklabels([repo for repo in repositories])
    ax.legend(loc="upper right", bbox_to_anchor=(1.0, 1.0))
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    fig.savefig(fname=plot_dir / "llm_call_stacked_bar_chart.png", 
               bbox_inches="tight", dpi=300)
    plt.close(fig)


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
