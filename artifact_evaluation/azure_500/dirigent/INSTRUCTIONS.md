## Azure 500 on Dirigent

Time required: 15 min to set up environment and 30 min per experiment

Description: This experiment runs the downsampled Azure trace with 500 functions. We recommend you follow the order of experiments as given in the `README.md`. 

Instructions:
- Start Dirigent cluster as per instructions located in the root folder of artifact evaluation instructions.
- On your local machine, execute `./scripts/disable_pstate.sh dirigent user@node0 user@node1 ... user@nodeN`. 
  - **This will cause the worker nodes to reboot. Wait here and monitor CloudLab to see when the nodes come back online. Only proceed when all workers show as Ready/Finished**
- On your local machine run `./scripts/set_cpu_freq.sh dirigent [Num_Fast_Nodes] user@node0 user@node1 ... user@nodeN`
  - For example, if you want 7 worker nodes as fast nodes, you should do `./scripts/set_cpu_freq.sh dirigent 7 user@node0 user@node1 ... user@nodeN`
- On the `node0` execute `mkdir -p ~/invitro/data/traces/azure_500`.
- Copy traces from this folder on local machine to `node0` using `scp azure_500/* user@node0:~/invitro/data/traces/azure_500/`.
- Make sure on `node0` you navigate to `~/invitro` directory (`cd ~/invitro`) and confirm the branch is in `rps_mode` (`git branch` should output `rps_mode`). 
- With text editor open `~/invitro/cmd/config_dirigent_trace.json` and confirm TracePath is `data/traces/azure_500`. Change the config file if needed.
  - You can also adjust the ExperimentDuration here if needed, but you should confirm it is set to 30 unless you are requested to change it.
- On `node0`, you should copy the modified dirigent CSV file to overwrite the existing dirigent.csv file with `cp ~/invitro/data/traces/azure_500/dirigent_modified.csv ~/invitro/data/traces/azure_500/dirigent.csv`
  - The values in the last column should ***not*** be 155 after the `cp` command completes.
- On your local machine run `./scripts/start_resource_monitoring.sh user@node0 user@node1 ... user@nodeN`. 
- Run the load generator in screen/tmux on `node0` with `cd ~/invitro; go run cmd/loader.go --config cmd/config_dirigent_trace.json`. Wait until the experiment completed (~30 minutes). There should be ~170K invocations, with a negligible failure rate.
- Gather experiment results. Make sure you do not overwrite data from the other experiment, and you place results in correct folders.
  - Create folders for storing results with `mkdir -p ./artifact_evaluation/azure_500/dirigent/results_azure_500`.
  - Copy load generator output with `scp user@node0:~/invitro/data/out/experiment_duration_30.csv results_azure_500/`
  - Copy resource utilization data with `mkdir -p ./artifact_evaluation/azure_500/dirigent/results_azure_500/cpu_mem_usage && ./scripts/collect_resource_monitoring.sh ./artifact_evaluation/azure_500/dirigent/results_azure_500/cpu_mem_usage user@node0 user@node1 ... user@nodeN`.
