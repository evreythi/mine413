#!/usr/bin/env bash
# Demonstrates the Task 8 update workflow: build a model with the data available
# on 22 March, then update it with everything received afterwards and compare.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf outputs_demo
python -m spbm run --fast --until "2026-03-22 23:59" --out outputs_demo
python -m spbm run --fast --out outputs_demo
echo "---- change report ----"
cat outputs_demo/audit/change_report.md
