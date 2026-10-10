from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "estimate_analysis_tokens.py"


class EstimateAnalysisTokensTest(unittest.TestCase):
    def test_cjk_range_and_segment_count(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "novel.txt"
            source.write_text("汉" * 10050 + "，" * 10 + " abc", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(source), "--format", "json"],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
        data = json.loads(result.stdout)
        self.assertEqual(data["measurement"], "length_estimate")
        self.assertEqual(data["cjk_chars"], 10050)
        self.assertEqual(data["punctuation_chars"], 10)
        self.assertEqual(data["planned_segments"], 2)
        self.assertLess(data["source_tokens_low"], data["source_tokens_high"])
        self.assertEqual(data["source_tokens_low"], 10050 + 10)
        self.assertFalse(data["confirm_required"])

    def test_confirm_required_when_segments_meet_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "novel.txt"
            source.write_text("汉" * 80000, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(source), "--format", "json"],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
        data = json.loads(result.stdout)
        self.assertGreaterEqual(data["planned_segments"], 8)
        self.assertTrue(data["confirm_required"])

    def test_rejects_analysis_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            (workspace / "analysis-state.yaml").write_text("schema_version: 1\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(workspace)],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
        self.assertEqual(result.returncode, 2)
        self.assertIn("analyses", result.stderr)


if __name__ == "__main__":
    unittest.main()
