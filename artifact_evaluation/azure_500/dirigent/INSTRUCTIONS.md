## Azure 500 on Dirigent

Time required: 15 min to set up environment and 30 min per experiment

Description: This experiment runs the downsampled Azure trace with 500 functions. We recommend you follow the order of experiments as given in the `README.md`. 

Instructions:
- Start Dirigent cluster as per instructions located in the root folder of artifact evaluation instructions.
- On your local machine run `./scripts/set_cpu_freq.sh dirigent [Num_Fast_Nodes] user@node0 user@node1 ... user@nodeN`
  - For example, if you want 7 worker nodes as fast nodes, you should do `./scripts/set_cpu_freq.sh dirigent 7 user@node0 user@node1 ... user@nodeN`
- On your local machine run `./scripts/modify_iteration_multiplier.sh dirigent 500`
  - Note: If you repeat this command, the `dirigent_backup.csv` file will no longer be the original. But it can be recreated by using the script with a value of `155`.
  - For context, the original IterationMultiplier of the artifact evaluation is `155`, but don't use this since it does not stress the CPU.
- On `node0` modify `pkg/metric/record.go` to add the following line to the `ExecutionRecord` struct: **MachineName string \`csv:"machineName"\`**
  - Place this after the line with `MemoryAllocationTimeout bool`
- On `node0` modify `pkg/driver/clients/http_client.go` to add the following line to the `DeserializeDirigentResponse` function: **record.MachineName = deserializedResponse.MachineName**
  - Place this after the line `record.ActualDuration`
- On the `node0` execute `mkdir -p ~/invitro/data/traces/azure_500`.
- Copy traces from this folder on local machine to `node0` using `scp artifact_evaluation/azure_500/dirigent/azure_500/* user@node0:~/invitro/data/traces/azure_500/`.
- Make sure on `node0` you navigate to `~/invitro` directory (`cd ~/invitro`) and confirm the branch is in `rps_mode` (`git branch` should output `rps_mode`). 
- With text editor open `~/invitro/cmd/config_dirigent_trace.json` and confirm TracePath is `data/traces/azure_500`. Change the config file if needed.
  - You can also adjust the ExperimentDuration here if needed, but you should confirm it is set to 30 unless you are requested to change it.
- On your local machine run `./scripts/start_resource_monitoring.sh user@node0 user@node1 ... user@nodeN`. 
- Run the load generator in screen/tmux on `node0` with `cd ~/invitro; go run cmd/loader.go --config cmd/config_dirigent_trace.json`. Wait until the experiment completed (~30 minutes). There should be ~170K invocations, with a negligible failure rate.
- Gather experiment results. Make sure you do not overwrite data from the other experiment, and you place results in correct folders.
  - On your local machine create folders for storing results with `mkdir -p ./artifact_evaluation/azure_500/dirigent/results_azure_500`.
  - **Make sure to save / back-up, and then remove any existing CSVs in the `results_azure_500/` directory and its `cpu_mem_usage/` subdirectory if applicable!**
  - Copy load generator output with `scp user@node0:~/invitro/data/out/experiment_duration_30.csv results_azure_500/`
  - Copy resource utilization data with `mkdir -p ./artifact_evaluation/azure_500/dirigent/results_azure_500/cpu_mem_usage && ./scripts/collect_resource_monitoring.sh ./artifact_evaluation/azure_500/dirigent/results_azure_500/cpu_mem_usage user@node0 user@node1 ... user@nodeN`.
  - Create the node classifications CSV by running `./scripts/generate_dirigent_node_classes.sh [cloudlab-experiment-name] [num_fast_nodes] [num_slow_nodes]`
    - For example, if your CloudLab experiment name is `my-dirigent-exp` and you have 7 fast nodes and 7 slow nodes, use `./scripts/generate_dirigent_node_classes.sh my-dirigent-exp 7 7`
    - This outputs a CSV in your current directory titled `dirigent-classifications.csv`