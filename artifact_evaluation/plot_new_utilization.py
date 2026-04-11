import glob
import sys
import os

import matplotlib.pyplot as plt
import pandas as pd


def parse_args():
    if len(sys.argv) < 8:
        print("Usage:")
        print("python plot_new_utilization.py <knative_cpu_mem_usage_dir> <dirigent_cpu_mem_usage_dir> <output_dir> "
              "<experiment_duration> <num_non_workers> <node_classification_csv> user@node1 user@node2 ... user@nodeN")
        sys.exit(1)

    input_knative = sys.argv[1]
    input_dirigent = sys.argv[2]
    output_folder = sys.argv[3]
    experiment_duration = int(sys.argv[4])
    num_non_workers = int(sys.argv[5])
    classification_csv = sys.argv[6]
    node_order = sys.argv[7:]

    return input_knative, input_dirigent, output_folder, node_order, num_non_workers, classification_csv, experiment_duration


def build_node_sets(node_order, num_non_workers, classification_csv):
    """
    Classify worker nodes as fast/slow using the CSV.
    The CSV rows are matched positionally to node_order[num_non_workers:].
    """
    worker_nodes = node_order[num_non_workers:]

    class_df = pd.read_csv(classification_csv)
    class_df.columns = class_df.columns.str.strip()

    if len(class_df) != len(worker_nodes):
        print(
            f"Warning: classification CSV has {len(class_df)} rows but there are "
            f"{len(worker_nodes)} worker nodes. Matching by position up to the shorter length.",
            file=sys.stderr,
        )

    fast_nodes, slow_nodes = [], []
    for i, node in enumerate(worker_nodes):
        if i >= len(class_df):
            print(f"Warning: no classification for worker node '{node}' (index {i}), skipping", file=sys.stderr)
            continue
        node_class = str(class_df['class'].iloc[i]).strip().lower()
        csv_name = str(class_df['node_name'].iloc[i]).strip()
        if node_class == 'fast':
            fast_nodes.append(node)
        elif node_class == 'slow':
            slow_nodes.append(node)
        else:
            print(f"Warning: unknown class '{node_class}' for CSV row {i} ('{csv_name}'), skipping", file=sys.stderr)

    return worker_nodes, fast_nodes, slow_nodes


def map_nodes_to_files(input_folder, node_order):
    all_files = sorted(glob.glob(os.path.join(input_folder, "*.csv")))
    node_to_file = {}

    for f in all_files:
        for node in node_order:
            if node in f:
                node_to_file[node] = f

    return node_to_file


def load_and_process(file_path, start, end):
    df = pd.read_csv(file_path, dtype={"machineName": str})
    df.columns = df.columns.str.strip()

    if 'Timestamp' not in df.columns:
        raise ValueError(f"Missing Timestamp column in {file_path}")

    if df['Timestamp'].max() < start or df['Timestamp'].min() > end:
        print(
            f"Warning: {file_path} has no overlap with experiment bounds; using full file range",
            file=sys.stderr,
        )
    else:
        df = df[(df['Timestamp'] > start) & (df['Timestamp'] < end)]

    df = df.reset_index(drop=True)

    if df.empty:
        print(
            f"Warning: no data in {file_path} after time filtering; leaving file unfiltered",
            file=sys.stderr,
        )
        df = pd.read_csv(file_path)
        df.columns = df.columns.str.strip()
        df = df.reset_index(drop=True)

    print(file_path)
    df['time'] = df['Timestamp'] - df['Timestamp'].iloc[0]
    df['minute'] = df['time'] / 60
    df['minute'] = df['minute'].round(0).astype(int)
    df = df.groupby('minute', as_index=False).mean()

    return df


def aggregate_nodes(node_files, start, end):
    df_all = pd.DataFrame()

    for idx, f in enumerate(node_files):
        df = load_and_process(f, start, end)
        df['id'] = idx
        df_all = pd.concat([df_all, df], ignore_index=True)

    if df_all.empty:
        return df_all

    return df_all.groupby('minute', as_index=False).mean()


def get_time_bounds(input_folder, experiment_duration):
    experiment_path = os.path.join(input_folder, f"experiment_duration_{experiment_duration}.csv")
    experiment_path = experiment_path.replace("/cpu_mem_usage", "")
    experiment_df = pd.read_csv(experiment_path, dtype={"machineName": str})
    start = experiment_df['startTime'][0] / 1e6
    end = experiment_df['startTime'].iloc[-1] / 1e6
    return start, end


def plot_experiment(ax, experiment_name, input_folder,
                    node_order, num_non_workers, classification_csv, column, experiment_duration):

    _, fast_nodes, slow_nodes = build_node_sets(node_order, num_non_workers, classification_csv)
    node_to_file = map_nodes_to_files(input_folder, node_order)

    start, end = get_time_bounds(input_folder, experiment_duration)

    fast_files = [node_to_file[n] for n in fast_nodes if n in node_to_file]
    slow_files = [node_to_file[n] for n in slow_nodes if n in node_to_file]

    fast_df = aggregate_nodes(fast_files, start, end)
    slow_df = aggregate_nodes(slow_files, start, end)

    if not fast_df.empty:
        ax.step(fast_df['minute'], fast_df[column],
                label=f"{experiment_name} (fast)", where='post')

    if not slow_df.empty:
        ax.step(slow_df['minute'], slow_df[column],
                label=f"{experiment_name} (slow)", where='post')


def main():
    (input_knative,
     input_dirigent,
     output_folder,
     node_order,
     num_non_workers,
     classification_csv,
     experiment_duration) = parse_args()

    os.makedirs(output_folder, exist_ok=True)

    for column in ['CPUUtilization', 'memoryUtilization']:
        fig, ax = plt.subplots(figsize=(8, 5))

        plot_experiment(ax, "Knative", input_knative,
                        node_order, num_non_workers, classification_csv, column, experiment_duration)

        plot_experiment(ax, "Dirigent", input_dirigent,
                        node_order, num_non_workers, classification_csv, column, experiment_duration)

        ax.set_ylabel("CPU Utilization [%]" if column == 'CPUUtilization' else "Memory Utilization [%]")
        ax.set_xlabel("Time [min]")
        ax.set_ylim(0, 100)
        ax.set_title(f"Worker Nodes ({column})")
        ax.grid()
        ax.legend()

        plt.tight_layout()
        plt.savefig(f"{output_folder}/{column}.png")
        plt.savefig(f"{output_folder}/{column}.pdf", bbox_inches='tight')
        plt.close()


if __name__ == "__main__":
    main()