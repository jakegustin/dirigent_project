#!/bin/bash
OUTPUT=$1
echo "timestamp,pod_name,node_name" > "$OUTPUT"

while true; do
    timestamp=$(date +%s)
    kubectl get pods -A -o wide --no-headers \
        -l serving.knative.dev/service \
    | awk -v ts="$timestamp" '{print ts "," $2 "," $8}' \
    >> "$OUTPUT"
    sleep 30
done

# tmux new -s podwatch
# ./scripts/collect_pod_node_mapping.sh results_azure_500/pod_to_node.csv