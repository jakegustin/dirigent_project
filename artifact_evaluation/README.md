## Project Reproduction Instructions

Prerequisites:
- All experiments on a 17-node Cloudlab `xl170` cluster running the `maestro_sosp24ae` profile (`https://www.cloudlab.us/p/faas-sched/maestro_sosp24ae`).
- Chrome Cloudlab extension - install from https://github.com/eth-easl/cloudlab_extension

Notes:
- All experiments run in a mode where Dirigent and Knative/K8s components are not replicated. We also ran experiment in an environment where components run in high-availability mode. Our deployment scripts put load generator on `node0`, control plane on `node1`, data plane on `node2`, whereas all the other nodes serve as worker nodes. In other words, 3 nodes in the cluster are reserved for non-worker-node usage.
- All the plotting scripts are configured to work out of the box provided you placed experiment results and files in correct folders.
- Traces for the experiments described here are stored on Git LFS. Make sure you pull these files before proceeding further.
- Default Cloudlab shell should be `bash`. You can configure when logged in here `https://www.cloudlab.us/myaccount.php`.

Instructions to set up a Dirigent cluster (baseline or modified):
- Make sure the cluster is in a reloaded state, i.e., that neither Dirigent nor Knative is not running. 
- Clone Dirigent locally (`git clone https://github.com/jakegustin/dirigent_project.git`)
- Set sandbox runtime (`containerd`) by editing `WORKER_RUNTIME` in `./scripts/setup.cfg`
- In `scripts/setup.cfg`, also confirm that...
  - `SCHEDULING_MODE` is set to one of three values
    - `existing` for random (baseline) and round robin
    - `hierarchical` for hierarchical
    - `weighted-round-robin` for WRR
  - `NUM_FAST_WORKERS=[numFastWorkers]`, where `[numFastWorkers]` is an integer like `7`.
  - If using hierarchical, set `HIERARCHICAL_THRESHOLD=[value]`, e.g. `70.0`. Controls the max cpu utilization of fast nodes before getting deprioritzed.
- Open Cloudlab experiment, open Cloudlab extension, and copy list of all addresses (RAW) using the extension. This puts the list of all nodes in your clipboard in format requested by the scripts below.
- On your local machine, execute `./scripts/disable_pstate.sh dirigent user@node0 user@node1 ... user@nodeN`. 
  - **This will cause the worker nodes to reboot. Wait here and monitor CloudLab to see when the nodes come back online. Only proceed when all workers show as Ready/Finished**
- Run locally `./scripts/remote_install.sh`. Arguments should be the copied list of addresses from the previous step. For example, `./scripts/remote_install.sh user@node0 user@node1 ... user@nodeN`. This script should be executed only once.
- Run locally `./scripts/remote_start_cluster.sh user@node0 user@node1 ... user@nodeN`. After this step, the cluster should be operational. This script can be executed again to restart Dirigent cluster in case you experience issues without reloading the Cloudlab cluster.

---

*While Knative was not used to produce our final results due to shifted priorities and other technical challenges, we provide the original instructions to start up a Knative cluster below:*

Instructions to set up Knative/K8s baseline cluster:
- Make sure the cluster is in a reloaded state, i.e., that neither Dirigent nor Knative is not running.
- Clone Invitro locally and checkout to `ha_k8s` branch (`git clone --branch=ha_k8s https://github.com/vhive-serverless/invitro`)
- Open Cloudlab experiment, open Cloudlab extension, and copy list of all addresses (RAW) using the extension. This puts the list of all nodes in your clipboard in format requested by the scripts below.
- Set up a Knative/K8s cluster by locally running `./scripts/setup/create_multinode.sh`. Arguments should be the copied list of addresses from the previous step. For example, `./scripts/setup/create_multinode.sh user@node0 user@node1 user@node2`. This script should be executed only once.
- After a couple of minutes, once the script has completed executing, the cluster should be running, and you can ssh into `node0`. Execute `kubectl get pods -A` and verify that installation has completed successfully by checking that all pods are in `Running` or `Completed` state.