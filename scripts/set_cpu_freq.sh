#!/bin/bash

# Confirm if at least 3 arguments exist: experiment type, num fast nodes, and one node
if [ "$#" -lt 3 ]; then
  echo "Usage: $0 <dirigent|knative> <num_fast_nodes> <node1> <node2> ..."
  exit 1
fi

# Set config parameters
MODE="$1"
NUM_FAST="$2"

# Shift argument list by 2 to get node list
shift 2

NODES=("$@")

# Determine how many nodes to skip
if [ "$MODE" == "dirigent" ]; then
  SKIP=3 # loader/master, control plane, data plane
elif [ "$MODE" == "knative" ]; then
  SKIP=1 # just loader/master
else
  echo "Error: mode must be 'dirigent' or 'knative'"
  exit 1
fi

# Confirm we still have worker nodes to set
if [ "${#NODES[@]}" -le "$SKIP" ]; then
  echo "Error: Not enough nodes after exclusion"
  exit 1
fi

# Extract remaining worker nodes and the count of workers
WORKERS=("${NODES[@]:$SKIP}")
TOTAL_WORKERS=${#WORKERS[@]}

# Argument checking: if fast nodes exceeds total workers, we have a problem.
if [ "$NUM_FAST" -gt "$TOTAL_WORKERS" ]; then
  echo "Error: num_fast_nodes exceeds available workers"
  exit 1
fi

# Split up nodes into fast vs slow.
FAST_NODES=("${WORKERS[@]:0:$NUM_FAST}")
SLOW_NODES=("${WORKERS[@]:$NUM_FAST}")

echo "Mode: $MODE = Skipping first $SKIP nodes"
echo "Fast nodes (${#FAST_NODES[@]}): ${FAST_NODES[*]}"
echo "Slow nodes (${#SLOW_NODES[@]}): ${SLOW_NODES[*]}"

function RemoteExec() {
    ssh -oStrictHostKeyChecking=no -p 22 "$1" "$2";
}

# Function to pin frequency
set_freq() {
  local node="$1"
  local freq="$2"

  echo "Installing necessary tools on node $node"
  RemoteExec "$node" "sudo apt install cpufrequtils linux-tools-\$(uname -r) -y"

  echo "Disabling turbo on $node"
  RemoteExec "$node" 'echo 1 | sudo tee /sys/devices/system/cpu/intel_pstate/no_turbo'

  echo "Setting userspace governor for $node"
  RemoteExec "$node" "sudo cpupower -c all frequency-set -g userspace > /dev/null"

  echo "Setting $node to $freq"
  RemoteExec "$node" "sudo cpupower -c all frequency-set -d $freq -u $freq > /dev/null"


  echo "Disabling sleep/idle states for $node"
  RemoteExec "$node" "sudo cpupower idle-set -D 0 > /dev/null"
}

# Apply fast nodes (2.4 GHz)
for node in "${FAST_NODES[@]}"; do
  set_freq "$node" "2.4GHz" &
done

# Apply slow nodes (1.2 GHz)
for node in "${SLOW_NODES[@]}"; do
  set_freq "$node" "1.2GHz" &
done

wait

echo "All nodes configured."