from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "token_usage.py"


class TokenUsageCliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, args)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def test_records_and_summarizes_exact_and_estimated_usage(self):
        with tempfile.TemporaryDirectory() as temp:
            exact = self.run_cli(
                "record", temp, "--route", "novel", "--step", "chapter_draft",
                "--measurement", "exact", "--provider", "openai", "--model", "example-model",
                "--input-tokens", "100", "--cached-input-tokens", "40",
                "--output-tokens", "50", "--reasoning-tokens", "10",
                "--artifact", "chapters/chapter-001/draft.md",
            )
            self.assertEqual(exact.returncode, 0, exact.stderr)
            estimated = self.run_cli(
                "record", temp, "--route", "novel", "--step", "chapter_review",
                "--measurement", "estimated", "--input-tokens", "30", "--output-tokens", "20",
            )
            self.assertEqual(estimated.returncode, 0, estimated.stderr)
            summary = self.run_cli("summarize", temp, "--write")
            self.assertEqual(summary.returncode, 0, summary.stderr)
            data = json.loads(summary.stdout)
            self.assertEqual(data["totals"]["exact_tokens"], 150)
            self.assertEqual(data["totals"]["estimated_tokens"], 50)
            self.assertEqual(data["by_step"]["novel.chapter_draft"]["exact_events"], 1)
            self.assertTrue((Path(temp) / "production" / "token-summary.json").is_file())

    def test_unavailable_usage_requires_reason_and_rejects_counts(self):
        with tempfile.TemporaryDirectory() as temp:
            missing_reason = self.run_cli(
                "record", temp, "--route", "novel", "--step", "novel_brief",
                "--measurement", "unavailable",
            )
            self.assertNotEqual(missing_reason.returncode, 0)
            with_counts = self.run_cli(
                "record", temp, "--route", "novel", "--step", "novel_brief",
                "--measurement", "unavailable", "--reason", "runtime_usage_not_exposed",
                "--total-tokens", "10",
            )
            self.assertNotEqual(with_counts.returncode, 0)
            valid = self.run_cli(
                "record", temp, "--route", "novel", "--step", "novel_brief",
                "--measurement", "unavailable", "--reason", "runtime_usage_not_exposed",
            )
            self.assertEqual(valid.returncode, 0, valid.stderr)

    def test_rejects_inconsistent_totals_and_unsafe_artifact_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            total = self.run_cli(
                "record", temp, "--route", "novel", "--step", "chapter_draft",
                "--measurement", "exact", "--input-tokens", "100",
                "--output-tokens", "50", "--total-tokens", "999",
            )
            self.assertNotEqual(total.returncode, 0)
            artifact = self.run_cli(
                "record", temp, "--route", "novel", "--step", "chapter_draft",
                "--measurement", "exact", "--total-tokens", "150", "--artifact", "../outside.md",
            )
            self.assertNotEqual(artifact.returncode, 0)

    def test_validate_reports_corrupt_lines(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "production" / "token-usage.jsonl"
            path.parent.mkdir()
            path.write_text("not-json\n", encoding="utf-8")
            result = self.run_cli("validate", temp)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(json.loads(result.stdout)["valid"])


if __name__ == "__main__":
    unittest.main()
