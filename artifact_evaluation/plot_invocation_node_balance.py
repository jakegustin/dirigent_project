#  MIT License
#
#  Copyright (c) 2026 EASL
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.

import argparse
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

MICROSECONDS_PER_MINUTE = 60_000_000


def load_node_classes(path: str) -> dict:
    df = pd.read_csv(path)
    if not {"node_name", "class"}.issubset(df.columns):
        raise ValueError("--node-classes CSV must have 'node_name' and 'class' columns")
    return dict(zip(df["node_name"].str.strip(), df["class"].str.strip()))


def load_dataset(csv_path: str, dataset_name: str, node_classes: dict) -> pd.DataFrame:
    df = pd.read_csv(csv_path, dtype={"machineName": str})

    for col in ("startTime", "machineName"):
        if col not in df.columns:
            raise ValueError(f"{dataset_name}: missing required column '{col}' in '{csv_path}'")

    df["machineName"] = df["machineName"].fillna("").astype(str).str.strip()
    df.loc[df["machineName"] == "", "machineName"] = "<empty>"
    df["minute"] = ((df["startTime"] - df["startTime"].min()) // MICROSECONDS_PER_MINUTE).astype(int)
    df["class"] = df["machineName"].map(node_classes).fillna("unknown")

    return df


def build_per_node_minute_counts(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["minute", "machineName", "class"], as_index=False)
        .size()
        .rename(columns={"size": "invocations"})
        .sort_values(["minute", "machineName"])
    )


def build_per_class_minute_counts(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["minute", "class"], as_index=False)
        .size()
        .rename(columns={"size": "invocations"})
        .sort_values(["minute", "class"])
    )


def plot_per_node(ax: plt.Axes, counts: pd.DataFrame, title: str) -> None:
    class_colors = {"fast": "tab:green", "slow": "tab:red", "unknown": "tab:gray"}

    all_minutes = np.arange(counts["minute"].min(), counts["minute"].max() + 1)
    pivot = (
        counts.pivot(index="minute", columns="machineName", values="invocations")
        .reindex(all_minutes, fill_value=0)
    )

    # Determine class for each node column (stable across minutes)
    node_class = counts.drop_duplicates("machineName").set_index("machineName")["class"]

    for node in pivot.columns:
        cls = node_class.get(node, "unknown")
        ax.step(pivot.index, pivot[node].to_numpy(), where="post",
                color=class_colors[cls], linewidth=1.2, label=f"{node} ({cls})")

    ax.set_title(title)
    ax.set_xlabel("Minute bucket")
    ax.set_ylabel("Invocations")
    ax.grid(True)


def plot_per_class(ax: plt.Axes, dirigent: pd.DataFrame, knative: pd.DataFrame) -> None:
    system_colors = {"dirigent": "tab:green", "knative": "tab:blue"}
    class_styles = {"fast": "solid", "slow": "dashed", "unknown": "dotted"}

    for system_label, df in [("dirigent", dirigent), ("knative", knative)]:
        for cls, grp in df.groupby("class"):
            grp = grp.sort_values("minute")
            ax.step(grp["minute"], grp["invocations"], where="post",
                    color=system_colors[system_label],
                    linestyle=class_styles.get(cls, "dotted"),
                    label=f"{system_label} ({cls})")

    ax.set_title("Invocations by node class")
    ax.set_xlabel("Minute bucket")
    ax.set_ylabel("Invocations")
    ax.grid(True)
    ax.legend(fontsize=8)


def save_plot(fig: plt.Figure, output_dir: str, stem: str) -> None:
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, f"{stem}.png"))
    fig.savefig(os.path.join(output_dir, f"{stem}.pdf"))
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    real_path = os.path.dirname(os.path.realpath(__file__))

    parser = argparse.ArgumentParser(
        description="Plot invocation distribution across worker nodes by fast/slow class."
    )
    parser.add_argument("--dirigent-csv",
        default=os.path.join(real_path, "azure_500/dirigent/results_azure_500/experiment_duration_5.csv"))
    parser.add_argument("--knative-csv",
        default=os.path.join(real_path, "azure_500/knative/results_azure_500/experiment_duration_5.csv"))
    parser.add_argument("--output-dir",
        default=os.path.join(real_path, "azure_500/invocation_node_balance"))
    parser.add_argument("--node-classes", default=None,
        help="CSV with columns 'node_name,class' mapping nodes to fast/slow.")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    node_classes = load_node_classes(args.node_classes) if args.node_classes else {}

    dirigent = load_dataset(args.dirigent_csv, "Dirigent", node_classes)
    knative  = load_dataset(args.knative_csv,  "Knative",  node_classes)

    dirigent_counts = build_per_node_minute_counts(dirigent)
    knative_counts  = build_per_node_minute_counts(knative)

    # Plot 1: per-node lines, Dirigent only (node names are meaningful there)
    fig, ax = plt.subplots(figsize=(10, 5))
    plot_per_node(ax, dirigent_counts, "Dirigent: invocations per node")
    save_plot(fig, args.output_dir, "invocations_per_node")

    # Plot 2: fast vs slow aggregate, both systems
    fig, ax = plt.subplots(figsize=(8, 5))
    plot_per_class(ax, build_per_class_minute_counts(dirigent), build_per_class_minute_counts(knative))
    save_plot(fig, args.output_dir, "invocations_per_class")


if __name__ == "__main__":
    main()