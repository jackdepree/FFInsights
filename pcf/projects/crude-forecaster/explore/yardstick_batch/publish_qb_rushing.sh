#!/usr/bin/env bash
# QB rushing joins the published yardstick (I67; the CEO, 2026-11-23: "Yes qb rushing should be a
# yardstick table"): the lasso champion's three backtests (as the 12 others were run, decision
# 0037), then the yardstick table (the ladder, methods A and C, its noise). One at a time.
# Run from pcf/ with PCF_DATA_DIR set. Progress: data/logs/crude-forecaster-validate.txt.
set -u
LOG="$PCF_DATA_DIR/logs/crude-forecaster-validate.txt"
PY=.venv/Scripts/python.exe
for v in qb_rushing_next_lasso qb_rushing_next3_lasso qb_rushing_rest_lasso; do
  echo "$(date +%T) start $v" >> "$LOG"
  $PY -m pcf.cli backtest crude-forecaster --variant "$v" --seasons 2019 2020 2021 2022 2023 2024 --shuffles 20 --refit season \
    > "$PCF_DATA_DIR/logs/backtest-$v.txt" 2>&1
  echo "$(date +%T) end $v exit $?" >> "$LOG"
done
echo "$(date +%T) start yardstick qb_rushing" >> "$LOG"
$PY projects/crude-forecaster/build/yardstick_run.py qb_rushing next,next3,rest \
  > projects/crude-forecaster/build/yardstick_qb_rushing.txt 2> "$PCF_DATA_DIR/logs/crude-forecaster-yardstick-qb.err"
echo "$(date +%T) end yardstick qb_rushing exit $?" >> "$LOG"
echo "publish qb_rushing all done" >> "$LOG"
