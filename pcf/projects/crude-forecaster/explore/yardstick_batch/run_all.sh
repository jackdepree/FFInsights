#!/usr/bin/env bash
# The yardstick batch, one idea after another (one heavy run at a time). Run from pcf/.
export PYTHONUTF8=1 MLFLOW_DISABLE_AGENT_HINT=1
D=projects/crude-forecaster/explore/yardstick_batch
for idea in "$@"; do
  .venv/Scripts/python.exe -W ignore $D/run_batch.py "$idea" > "$D/$idea.txt" 2> "$D/$idea.err"
  echo "$idea exit $?" >> "$PCF_DATA_DIR/logs/yardstick-batch-progress.txt"
done
