## Azure 500 on Knative/K8s

Time required: 15 min to set up environment and 30-60 min for the experiment

Description: This experiment runs the downsampled Azure trace with 500 functions. Do not reuse Knative/K8s cluster if you configured the cluster for cold start sweep experiment. 

Important: Do not reuse Knative/K8s cluster if you previously ran cold start sweep experiments, as the autoscaling configuration was changed and could affect the results severely.

Instructions:
- SSH into `node0` and on that node clone the load generator repo. Then checkout to `rps_mode` branch. The command is `git clone --branch=rps_mode https://github.com/vhive-serverless/invitro`.
- On your local machine, execute `./scripts/disable_pstate.sh knative user@node0 user@node1 ... user@nodeN`. 
  - **This will cause the worker nodes to reboot. Wait here and monitor CloudLab to see when the nodes come back online. Only proceed when all workers show as Ready/Finished**
- On your local machine run `./scripts/set_cpu_freq.sh knative [Num_Fast_Nodes] user@node0 user@node1 ... user@nodeN`
  - For example, if you want 8 worker nodes as fast nodes, you should do `./scripts/set_cpu_freq.sh knative 8 user@node0 user@node1 ... user@nodeN`
- On your local machine run `./scripts/modify_iteration_multiplier.sh knative 500`
  - Note: If you repeat this command, the `dirigent_backup.csv` file will no longer be the original. But it can be recreated by using the script with a value of `155`.
  - For context, the original IterationMultiplier of the artifact evaluation is `155`, but don't use this since it does not stress the CPU.
- On `node0` modify `pkg/metric/record.go` to add the following line to the `ExecutionRecord` struct: **MachineName string \`csv:"machineName"\`**
  - Place this after the line with `MemoryAllocationTimeout bool`
- On `node0` modify `pkg/driver/clients/http_client.go` to add the following line to the `DeserializeDirigentResponse` function: **record.MachineName = deserializedResponse.MachineName**
  - Place this after the line `record.ActualDuration`
- On `node0` create a directory where trace will be stored `cd invitro; mkdir data/traces/azure_500`.
- Copy the trace from folder where this instruction file is located to the folder you previously created on `node0` using the following command `scp azure_500/*.csv user@node0:~/invitro/data/traces/azure_500`. 
- On your local machine run `./scripts/start_resource_monitoring.sh user@node0 user@node1 ... user@nodeN`.
- *If explicitly requested to change the experiment duration*, you can also adjust the ExperimentDuration in `~/invitro/cmd/config_knative.json`. Unless another value is requested, you should confirm it is set to 30.
- On `node0` inside screen/tmux run `cd ~/invitro; go run cmd/loader.go --config cmd/config_knative.json`. Function deployment will take 10-20 minutes, and then experiment will run for additional 30 minutes.
- Gather experiment results. Make sure you do not overwrite data from the other experiment, and you place results in correct folders.
  - Create a folder for storing results with `mkdir -p ./artifact_evaluation/azure_500/knative/results_azure_500`
  - **Make sure to save / back-up, and then remove any existing CSVs in the `results_azure_500/` directory and its `cpu_mem_usage/` subdirectory if applicable!**
  - Copy load generator output with `scp user@node0:~/invitro/data/out/experiment_duration_30.csv results_azure_500/`
  - Copy resource utilization data with `mkdir -p ./artifact_evaluation/azure_500/knative/results_azure_500/cpu_mem_usage && ./scripts/collect_resource_monitoring.sh ./artifact_evaluation/azure_500/knative/results_azure_500/cpu_mem_usage user@node0 user@node1 ... user@nodeN`.