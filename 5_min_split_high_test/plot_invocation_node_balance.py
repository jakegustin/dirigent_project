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

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

MICROSECONDS_PER_MINUTE = 60_000_000


def gini(values: np.ndarray) -> float:
    if values.size == 0:
        return 0.0

    values = values.astype(float)
    total = values.sum()
    if total <= 0:
        return 0.0

    sorted_values = np.sort(values)
    n = sorted_values.size
    idx = np.arange(1, n + 1, dtype=float)

    return float((2.0 * np.sum(idx * sorted_values) / (n * total)) - ((n + 1.0) / n))


def validate_required_columns(df: pd.DataFrame, csv_path: str, dataset_name: str) -> None:
    required_columns = ["startTime", "machineName"]
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(
            f"{dataset_name}: missing required column(s) [{missing}] in '{csv_path}'. "
            f"Expected at least columns: {required_columns}."
        )

    machine_name = df["machineName"].fillna("").astype(str).str.strip()
    if (machine_name == "").all():
        raise ValueError(
            f"{dataset_name}: column 'machineName' is present but entirely empty in '{csv_path}'."
        )


def load_dataset(csv_path: str, dataset_name: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    validate_required_columns(df, csv_path, dataset_name)

    df = df.copy()
    df["machineName"] = df["machineName"].fillna("").astype(str).str.strip()
    df.loc[df["machineName"] == "", "machineName"] = "<empty>"
    df["minute"] = ((df["startTime"] - df["startTime"].min()) // MICROSECONDS_PER_MINUTE).astype(int)
    return df


def build_per_instance_minute_counts(
    df: pd.DataFrame, top_n: int, node_classes: dict
) -> tuple[pd.DataFrame, pd.DataFrame]:
    counts = (
        df.groupby(["minute", "machineName"], as_index=False)
        .size()
        .rename(columns={"size": "invocations"})
        .sort_values(["minute", "machineName"])
    )

    counts["class"] = counts["machineName"].map(node_classes).fillna("unknown")

    top_instances = (
        counts.groupby("machineName", as_index=False)["invocations"]
        .sum()
        .sort_values("invocations", ascending=False)
        .head(top_n)["machineName"]
        .tolist()
    )

    counts_top = counts[counts["machineName"].isin(top_instances)].copy()

    return counts, counts_top


def build_imbalance_per_minute(df: pd.DataFrame, node_classes: dict) -> pd.DataFrame:
    grouped = (
        df.groupby(["minute", "machineName"], as_index=False)
        .size()
        .rename(columns={"size": "invocations"})
    )

    grouped["class"] = grouped["machineName"].map(node_classes).fillna("unknown")

    rows = []
    for (minute, cls), frame in grouped.groupby(["minute", "class"]):
        values = frame["invocations"].to_numpy(dtype=float)
        mean = float(values.mean()) if values.size > 0 else 0.0
        std = float(values.std(ddof=0)) if values.size > 0 else 0.0
        cv = std / mean if mean > 0 else 0.0

        rows.append({
            "minute": int(minute),
            "class": cls,
            "numInstances": int(values.size),
            "totalInvocations": int(values.sum()),
            "cv": cv,
            "gini": gini(values),
        })

    return pd.DataFrame(rows).sort_values(["minute", "class"]).reset_index(drop=True)


def step_plot_per_instance(
    ax: plt.Axes, counts_top: pd.DataFrame, title: str, node_classes: dict
) -> None:
    if counts_top.empty:
        ax.set_title(title)
        ax.set_xlabel("Minute bucket")
        ax.set_ylabel("Invocation count")
        ax.grid(True)
        return

    pivot = (
        counts_top.pivot(index="minute", columns="machineName", values="invocations")
        .fillna(0)
        .sort_index()
    )

    all_minutes = np.arange(int(pivot.index.min()), int(pivot.index.max()) + 1)
    pivot = pivot.reindex(all_minutes, fill_value=0)

    class_colors = {"fast": "tab:green", "slow": "tab:red", "unknown": "tab:gray"}

    for instance in pivot.columns:
        cls = node_classes.get(instance, "unknown")
        color = class_colors[cls]
        ax.step(
            pivot.index,
            pivot[instance].to_numpy(),
            where="post",
            linewidth=1.2,
            color=color,
            label=f"{instance} ({cls})",
        )

    ax.set_title(title)
    ax.set_xlabel("Minute bucket")
    ax.set_ylabel("Invocation count")
    ax.grid(True)


def save_plot(figure: plt.Figure, output_dir: str, stem: str) -> None:
    png_out = os.path.join(output_dir, f"{stem}.png")
    pdf_out = os.path.join(output_dir, f"{stem}.pdf")

    figure.tight_layout()
    figure.savefig(png_out)
    figure.savefig(pdf_out)


def make_plots(
    dirigent_counts_top: pd.DataFrame,
    knative_counts_top: pd.DataFrame,
    dirigent_imbalance: pd.DataFrame,
    knative_imbalance: pd.DataFrame,
    output_dir: str,
    node_classes: dict,
) -> None:
    # --- per-instance count plot ---
    fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
    step_plot_per_instance(ax1, dirigent_counts_top, "Dirigent: per-instance invocation count", node_classes)
    step_plot_per_instance(ax2, knative_counts_top, "Knative: per-instance invocation count", node_classes)

    handles, labels = ax1.get_legend_handles_labels()
    if handles:
        fig1.legend(handles, labels, loc="upper center", ncol=2, fontsize=8)

    save_plot(fig1, output_dir, "invocation_node_balance_per_instance")
    plt.close(fig1)

    # --- imbalance plot, split by class ---
    fig2, (ax_cv, ax_gini) = plt.subplots(1, 2, figsize=(14, 5))

    class_styles = {"fast": "solid", "slow": "dashed", "unknown": "dotted"}
    system_colors = {"dirigent": "tab:green", "knative": "tab:blue"}

    for system_label, imbalance in [("dirigent", dirigent_imbalance), ("knative", knative_imbalance)]:
        color = system_colors[system_label]
        for cls, grp in imbalance.groupby("class"):
            grp = grp.sort_values("minute")
            style = class_styles.get(cls, "dotted")
            label = f"{system_label}-{cls}"
            ax_cv.step(grp["minute"], grp["cv"], where="post",
                       color=color, linestyle=style, label=label)
            ax_gini.step(grp["minute"], grp["gini"], where="post",
                         color=color, linestyle=style, label=label)

    ax_cv.set_title("Imbalance over time (CV)")
    ax_cv.set_xlabel("Minute bucket")
    ax_cv.set_ylabel("CV (population std / mean)")
    ax_cv.grid(True)
    ax_cv.legend(fontsize=8)

    ax_gini.set_title("Imbalance over time (Gini)")
    ax_gini.set_xlabel("Minute bucket")
    ax_gini.set_ylabel("Gini coefficient")
    ax_gini.grid(True)
    ax_gini.legend(fontsize=8)

    save_plot(fig2, output_dir, "invocation_node_balance_imbalance")
    plt.close(fig2)


def parse_args() -> argparse.Namespace:
    real_path = os.path.dirname(os.path.realpath(__file__))

    parser = argparse.ArgumentParser(
        description="Plot invocation distribution balance across worker instances/pods."
    )
    parser.add_argument(
        "--dirigent-csv",
        default=os.path.join(real_path, "azure_500/dirigent/results_azure_500/experiment_duration_30.csv"),
        help="Path to Dirigent experiment CSV.",
    )
    parser.add_argument(
        "--knative-csv",
        default=os.path.join(real_path, "azure_500/knative/results_azure_500/experiment_duration_30.csv"),
        help="Path to Knative experiment CSV.",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join(real_path, "azure_500/invocation_node_balance"),
        help="Directory for output plots and intermediate CSVs.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Number of most-invoked instances to include in per-instance line plots.",
    )
    parser.add_argument(
        "--node-classes",
        default=None,
        help="Path to CSV with columns 'node_name,class' mapping instances to fast/slow.",
    )

    return parser.parse_args()

def load_node_classes(path: str) -> dict:
    df = pd.read_csv(path)
    if not {"node_name", "class"}.issubset(df.columns):
        raise ValueError("--node-classes CSV must have 'node_name' and 'class' columns")
    return dict(zip(df["node_name"].str.strip(), df["class"].str.strip()))

def main() -> None:
    args = parse_args()

    if args.top_n <= 0:
        raise ValueError(f"--top-n must be > 0, got {args.top_n}.")

    os.makedirs(args.output_dir, exist_ok=True)

    node_class = load_node_classes(args.node_classes) if args.node_classes else {}

    dirigent = load_dataset(args.dirigent_csv, "Dirigent")
    knative = load_dataset(args.knative_csv, "Knative")

    dirigent_counts_all, dirigent_counts_top = build_per_instance_minute_counts(dirigent, args.top_n, node_class)
    knative_counts_all, knative_counts_top = build_per_instance_minute_counts(knative, args.top_n, node_class)

    dirigent_imbalance = build_imbalance_per_minute(dirigent, node_class)
    knative_imbalance = build_imbalance_per_minute(knative, node_class)

    dirigent_counts_all.to_csv(
        os.path.join(args.output_dir, "dirigent_per_instance_per_minute.csv"),
        index=False,
    )
    knative_counts_all.to_csv(
        os.path.join(args.output_dir, "knative_per_instance_per_minute.csv"),
        index=False,
    )
    dirigent_imbalance.to_csv(
        os.path.join(args.output_dir, "dirigent_imbalance_per_minute.csv"),
        index=False,
    )
    knative_imbalance.to_csv(
        os.path.join(args.output_dir, "knative_imbalance_per_minute.csv"),
        index=False,
    )

    make_plots(
        dirigent_counts_top,
        knative_counts_top,
        dirigent_imbalance,
        knative_imbalance,
        args.output_dir,
        node_class
    )


if __name__ == "__main__":
    main()
