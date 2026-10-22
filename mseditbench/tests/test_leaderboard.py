"""Leaderboard export regressions. Run: python -m unittest mseditbench.tests.test_leaderboard"""

import csv
import json
import runpy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parents[2]
# Load the standalone exporter without importing the optional video/model stack
# pulled in by mseditbench.eval.__init__.
EXPORTER = REPO_ROOT / "mseditbench/eval/leaderboard.py"
_namespace = runpy.run_path(str(EXPORTER))
LEADERBOARD_COLUMNS = _namespace["LEADERBOARD_COLUMNS"]
leaderboard_row = _namespace["leaderboard_row"]


class LeaderboardTests(unittest.TestCase):
    def test_existing_t1_cli_export(self):
        eval_root = REPO_ROOT / "runs/eval_seedance_v2v_v2_10s_v3/T1"
        with (eval_root / "aggregate.json").open() as f:
            aggregate = json.load(f)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "leaderboard.csv"
            subprocess.run(
                [sys.executable, str(EXPORTER),
                 "--eval_root", str(eval_root), "--output_csv", str(output)],
                cwd=REPO_ROOT, check=True, capture_output=True, text=True,
            )
            with output.open(newline="") as f:
                reader = csv.DictReader(f)
                self.assertEqual(reader.fieldnames, LEADERBOARD_COLUMNS)
                rows = list(reader)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["task_id"], "T1")
        self.assertEqual(row["baseline"], "seedance_v2v_pro_v2_10s")
        self.assertEqual(row["snapshot_id"], aggregate["snapshot_id"])
        self.assertEqual(int(row["n"]), 60)
        self.assertAlmostEqual(float(row["ee_mean"]), 0.5233333333333331)
        self.assertAlmostEqual(float(row["csep_mean"]), 0.530958575314458)
        for key in ("psq_mean", "nep_mean", "ses_mean"):
            self.assertEqual(float(row[key]), aggregate[key])

    def test_legacy_fields_with_missing_or_null_current_fields(self):
        legacy = {"n": 12, "ee_mean": 0.2, "csep_mean": 0.3}
        for current in ({}, {"n_prompts": None, "ee_v3_mean": None,
                             "csep_v3_mean": None}):
            with self.subTest(current=current):
                row = leaderboard_row({**legacy, **current})
                for key, value in legacy.items():
                    self.assertEqual(row[key], value)

    def test_current_fields_take_precedence_including_zero(self):
        for value in (0, 0.7):
            with self.subTest(value=value):
                row = leaderboard_row({
                    "n_prompts": value, "n": 99,
                    "ee_v3_mean": value, "ee_mean": 0.9,
                    "csep_v3_mean": value, "csep_mean": 0.9,
                })
                for key in ("n", "ee_mean", "csep_mean"):
                    self.assertEqual(row[key], value)

    def test_unavailable_fields_remain_empty(self):
        self.assertEqual(leaderboard_row({}), dict.fromkeys(LEADERBOARD_COLUMNS))
        self.assertIsNone(leaderboard_row({"ee_v3_mean": None})["ee_mean"])


if __name__ == "__main__":
    unittest.main()
