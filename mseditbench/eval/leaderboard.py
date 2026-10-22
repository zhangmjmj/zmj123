"""Aggregate eval results across (task, baseline) into a leaderboard CSV.

CLI:
    python -m mseditbench.eval.leaderboard \
        --eval_root runs/eval_aleph_mock \
        --output_csv runs/eval_aleph_mock/leaderboard.csv

Walks <eval_root>/<task>/aggregate.json files written by run_eval.py and
emits one CSV row per (task, baseline) tuple.

The CSV column names and order are kept for compatibility. ``n`` uses
``n_prompts`` when available; ``ee_mean`` and ``csep_mean`` prefer the v3
metrics. Missing or null v3 values fall back to the legacy fields. Thus
EE/CSEP columns contain v3 scores for v3 runs and legacy scores for old runs;
compare runs using the same metric version.
"""

from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

LEADERBOARD_COLUMNS = [
    "snapshot_id", "task_id", "baseline", "n",
    "psq_mean", "ee_mean", "nep_mean", "csep_mean", "ses_mean",
]


# Prefer current aggregate fields without discarding valid zero values.
FIELD_SOURCES = {
    "n": ("n_prompts", "n"),
    "ee_mean": ("ee_v3_mean", "ee_mean"),
    "csep_mean": ("csep_v3_mean", "csep_mean"),
}


def leaderboard_row(aggregate):
    row = {}
    for column in LEADERBOARD_COLUMNS:
        row[column] = next(
            (aggregate[key] for key in FIELD_SOURCES.get(column, (column,))
             if aggregate.get(key) is not None),
            None,
        )
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval_root", required=True)
    ap.add_argument("--output_csv", required=True)
    args = ap.parse_args()

    rows = []
    for agg_path in sorted(Path(args.eval_root).rglob("aggregate.json")):
        with agg_path.open() as f:
            rows.append(leaderboard_row(json.load(f)))

    with open(args.output_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LEADERBOARD_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} leaderboard rows -> {args.output_csv}")


if __name__ == "__main__":
    main()
