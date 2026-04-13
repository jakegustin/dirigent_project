#!/bin/bash

if [ $# -lt 2 ]; then
	echo "Usage: $0 <num_fast> user@node0 user@node1 ... user@nodeN"
	exit 1
fi

# Get the number of fast nodes
num_fast=$1
shift

# Remove the master node from consideration
master_node=$1
shift

count=0
for node in "$@"; do
	# Extract the node name (after the @)
	node_name="${node#*@}"
	if [ $count -lt $num_fast ]; then
		class="fast"
	else
		class="slow"
	fi
	echo "Labeling $node_name as $class"
	# Label the node using kubectl
	kubectl label node "$node_name" node-class=$class --overwrite
	count=$((count + 1))
done

