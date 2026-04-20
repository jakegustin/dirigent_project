# Addressing Resource Heterogeneity and Sandbox Placement in Serverless Orchestration
### By: Raotao D., Vladislav E., Jake G., Seungjae L.

## Instructions to Reproduce Experimental Results

Please refer to the `README.md` file within `artifact_evaluation` to start a "Dirigent" (baseline) or Modified cluster, and refer to the individual `INSTRUCTIONS.md` files within the `dirigent` and `modified` subdirectories to run the experiments.

## Directories of Note

- `project_results/`: Experimental data collected and plots produced for this project.
    - NOTE: The contents of this directly are all stored via Git LFS. If cloning the repository locally, you'll need to install and utilize Git LFS to pull the files.
- `artifact_evaluation/`: Modified to include several changes
    - New plotting scripts (e.g. `plot_new_azure_500.py`, `plot_new_utilization.py`, `plot_invocation_node_balance.py`)
    - New `azure_500/modified` subdirectory to handle modified versions of Dirigent for testing purposes
    - Documentation changes throughout this directory, including `README.md` and `INSTRUCTIONS.md` files.
- `internal/control_plane/placement_policy/`: Implementation of Weighted Round Robin and Hierarchical schedulers added here
    - `hierarchical.go` for Hierarchical implementation
    - `weighted_round_robin.go` for WRR implementation
    - Other directories adjusted to incorporate such schedulers.
- `scripts/`: Various scripts created to support experimental efforts
    - `modify_iteration_multiplier.sh` is a convenience script to programmatically adjust the IterationMultiplier of the azure_500 workload.
    - `generate_dirigent_node_classes.sh` is a convenience script producing a CSV to use with other plotting scripts to identify what data corresponds to fast/slow nodes.
    - `set_cpu_freq.sh` is used to disable turbo mode, enable the userspace governor, and lock the frequency of all cores on the target devices to the predefined fast/slow speeds.
    - `disable_pstate.sh` modifies the GRUB bootloader and reboots the target devices to put Intel PState into passive mode, granting the OS/kernel control over CPU frequencies.
        - NOTE: Admittedly, it is far from the cleanest adjustment since rerunning the script for a second time without reloading the nodes in CloudLab will lead to a faulty value in the bootloader configuration, but it was sufficient for our testing purposes.
