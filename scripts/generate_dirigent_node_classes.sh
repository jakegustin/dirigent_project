#!/bin/bash

# Basic argument checking to see if enough values exist
if [[ $# -ne 3 ]]; then
  echo "Usage: $0 <cloudlab_exp_name> <num_fast_nodes> <num_slow_nodes>"
  exit 1
fi

# Assign variables & shift argument list to get nodes only
exp_name="$1"
num_fast="$2"
num_slow="$3"

# Ensure the specified number of fast nodes is actually a valid number
if ! [[ "$num_fast" =~ ^[0-9]+$ ]]; then
  echo "Error: num_fast_nodes must be a non-negative integer."
  exit 1
fi

# Ensure the specified number of fast nodes is actually a valid number
if ! [[ "$num_slow" =~ ^[0-9]+$ ]]; then
  echo "Error: num_slow_nodes must be a non-negative integer."
  exit 1
fi

# Write CSV to a file in the current working directory
output_file="dirigent_classes.csv"
{
  printf 'node_name,class\n'
  for (( i=0; i < num_fast + num_slow; i++ )); do    
    fqdn="node-$((i+3)).${exp_name}.gt-8803-dns-pg0.utah.cloudlab.us"
    if (( i < num_fast )); then
      printf '%s,fast\n' "$fqdn"
    else
      printf '%s,slow\n' "$fqdn"
    fi
  done
} > "$output_file"

echo "Wrote $output_file"
