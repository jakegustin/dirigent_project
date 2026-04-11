#!/bin/bash

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <dirigent|knative> <iteration_multiplier>"
  exit 1
fi

# Fetch variables
system="$1"
multiplier="$2"

# Confirm system selection is valid
if [[ "${system}" != "dirigent" && "${system}" != "knative" ]]; then
  echo "Invalid first argument: ${system}. Expected 'dirigent' or 'knative'." >&2
  exit 0
fi

# Get paths
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source_file="${script_dir}/../artifact_evaluation/azure_500/${system}/azure_500/dirigent.csv"
output_file="${script_dir}/../artifact_evaluation/azure_500/${system}/azure_500/dirigent_modified.csv"
backup_file="${script_dir}/../artifact_evaluation/azure_500/${system}/azure_500/dirigent_original.csv"

# Confirm source file exists
if [[ ! -f "${source_file}" ]]; then
  echo "Source file not found: ${source_file}"
  exit 1
fi

# Creates backup of dirigent.csv and replaces the IterationMultipler column with specified value in dirigent.csv
cp $source_file $backup_file
awk -v multiplier="${multiplier}" 'BEGIN { FS = OFS = "," }
NR == 1 { print; next }
{ $NF = multiplier; print }
' "${source_file}" > "${output_file}"

echo "Created ${output_file}"
