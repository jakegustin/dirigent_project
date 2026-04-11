#!/bin/bash

# Confirm if at least 3 arguments exist: experiment type, num fast nodes, and one node
if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <dirigent|knative> <node1> <node2> ..."
  exit 1
fi

# Set config parameters
MODE="$1"

# Shift argument list by 1 to get node list
shift 1

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

# Extract remaining worker nodes
WORKERS=("${NODES[@]:$SKIP}")

# Function to pin frequency
disable_pstate() {
  local node="$1"

  echo "Disabling Intel PState on $node"

  ssh "$node" "sudo sed -i 's|GRUB_CMDLINE_LINUX_DEFAULT=\"|GRUB_CMDLINE_LINUX_DEFAULT=\"intel_pstate=passive |' /etc/default/grub"
  ssh "$node" sudo update-grub

  echo "Rebooting node $node to put PState change into effect"

  ssh "$node" sudo reboot
}

# Disable PState for each worker node
for node in "${WORKERS[@]}"; do
  disable_pstate "$node" &
done

wait

echo "Bootloader configuration files on all worker nodes updated. All workers should be rebooting right now to implement the change."