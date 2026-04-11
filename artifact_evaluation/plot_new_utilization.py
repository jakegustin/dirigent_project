import glob
import sys
import os

import matplotlib.pyplot as plt
import pandas as pd


def parse_args():
    if len(sys.argv) < 7:
        print("Usage:")
        print("python plot_util.py <knative_dir> <dirigent_dir> <output_dir> "
              "<num_master> <num_fast> user@node1 user@node2 ... user@nodeN")
        sys.exit(1)

    input_knative = sys.argv[1]
    input_dirigent = sys.argv[2]
    output_folder = sys.argv[3]

    num_master = int(sys.argv[4])
    num_fast = int(sys.argv[5])

    node_order = sys.argv[6:]  # whitespace-separated

    if len(node_order) < num_master + num_fast:
        print("Error: not enough nodes for given master/fast counts")
        sys.exit(1)

    return input_knative, input_dirigent, output_folder, node_order, num_master, num_fast


def build_node_sets(node_order, num_master, num_fast):
    worker_nodes = node_order[num_master:]
    fast_nodes = worker_nodes[:num_fast]
    slow_nodes = worker_nodes[num_fast:]
    return worker_nodes, fast_nodes, slow_nodes


def map_nodes_to_files(input_folder, node_order):
    all_files = sorted(glob.glob(os.path.join(input_folder, "cpu_mem_usage", "*.csv")))
    node_to_file = {}

    for f in all_files:
        for node in node_order:
            if node in f:
                node_to_file[node] = f

    return node_to_file


def load_and_process(file_path, start, end):
    df = pd.read_csv(file_path)

    # Clean column names
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

    # Remove warmup
    df = df[df['minute'] >= 10]

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


def get_time_bounds(input_folder):
    experiment_df = pd.read_csv(os.path.join(input_folder, "experiment_duration_30.csv"))
    start = experiment_df['startTime'][0] / 1e6
    end = experiment_df['startTime'].iloc[-1] / 1e6
    return start, end


def plot_experiment(ax, experiment_name, input_folder,
                    node_order, num_master, num_fast, column):

    _, fast_nodes, slow_nodes = build_node_sets(node_order, num_master, num_fast)
    node_to_file = map_nodes_to_files(input_folder, node_order)

    start, end = get_time_bounds(input_folder)

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
     num_master,
     num_fast) = parse_args()

    os.makedirs(output_folder, exist_ok=True)

    for column in ['CPUUtilization', 'memoryUtilization']:
        fig, ax = plt.subplots(figsize=(8, 5))

        plot_experiment(ax, "Knative", input_knative,
                        node_order, num_master, num_fast, column)

        plot_experiment(ax, "Dirigent", input_dirigent,
                        node_order, num_master, num_fast, column)

        if column == 'CPUUtilization':
            ax.set_ylabel("CPU Utilization [%]")
        else:
            ax.set_ylabel("Memory Utilization [%]")

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