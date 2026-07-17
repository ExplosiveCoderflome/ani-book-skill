import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "trend_snapshot.py"


def record(rank, title, author, captured_at="2026-07-01", platform="示例平台", chart="男频畅销榜"):
    return {
        "platform": platform,
        "chart": chart,
        "window": "weekly",
        "captured_at": captured_at,
        "rank": rank,
        "title": title,
        "author": author,
        "source_url": "https://example.com/chart",
        "access_level": "metadata_only",
        "tags": ["玄幻", "升级"],
        "synopsis": "小镇少年借助规则面板成长。",
        "signals": [
            {
                "dimension": "genre",
                "value": "玄幻",
                "confidence": "high",
                "evidence_fields": ["tags"],
            },
            {
                "dimension": "core_mechanism",
                "value": "规则面板升级",
                "confidence": "medium",
                "evidence_fields": ["synopsis"],
            },
        ],
    }


class TrendSnapshotTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, args)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def write_snapshot(self, directory, name, records):
        path = Path(directory) / name
        path.write_text(
            "\n".join(json.dumps(item, ensure_ascii=False) for item in records) + "\n",
            encoding="utf-8",
        )
        return path

    def test_validate_accepts_valid_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_snapshot(temp, "valid.jsonl", [record(1, "甲书", "甲作者"), record(2, "乙书", "乙作者")])
            result = self.run_cli("validate", path)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertTrue(data["valid"])
            self.assertEqual(data["entry_count"], 2)

    def test_validate_rejects_contract_violations(self):
        cases = []
        missing = record(1, "甲书", "甲作者")
        del missing["author"]
        cases.append(("missing", [missing], "missing required fields"))
        invalid_date = record(1, "甲书", "甲作者", captured_at="2026/07/01")
        cases.append(("date", [invalid_date], "invalid captured_at"))
        access = record(1, "甲书", "甲作者")
        access["access_level"] = "full_text"
        cases.append(("access", [access], "metadata_only"))
        dimension = record(1, "甲书", "甲作者")
        dimension["signals"][0]["dimension"] = "whole_book_pacing"
        cases.append(("dimension", [dimension], "unsupported dimension"))
        duplicate = [record(1, "甲书", "甲作者"), record(2, "甲书", "甲作者")]
        cases.append(("duplicate", duplicate, "duplicate work"))
        with tempfile.TemporaryDirectory() as temp:
            for name, rows, message in cases:
                with self.subTest(name=name):
                    path = self.write_snapshot(temp, f"{name}.jsonl", rows)
                    result = self.run_cli("validate", path)
                    self.assertEqual(result.returncode, 2)
                    self.assertIn(message, result.stderr)

    def test_summarize_outputs_facts_without_trend_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_snapshot(temp, "snapshot.jsonl", [record(1, "甲书", "甲作者"), record(3, "乙书", "乙作者")])
            result = self.run_cli("summarize", path, "--format", "json")
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertFalse(data["supports_trend_claims"])
            genre = next(item for item in data["signals"] if item["dimension"] == "genre")
            self.assertEqual(genre["work_count"], 2)
            self.assertEqual(genre["platform_count"], 1)
            self.assertEqual(genre["average_rank"], 2.0)
            self.assertAlmostEqual(genre["rank_weight"], 1.5, places=6)
            self.assertNotIn("上升趋势", result.stdout)

    def test_compare_identifies_entry_exit_and_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            older = self.write_snapshot(
                temp,
                "older.jsonl",
                [record(1, "甲书", "甲作者"), record(3, "乙书", "乙作者")],
            )
            newer = self.write_snapshot(
                temp,
                "newer.jsonl",
                [
                    record(2, "甲书", "甲作者", captured_at="2026-07-08"),
                    record(1, "丙书", "丙作者", captured_at="2026-07-08"),
                ],
            )
            result = self.run_cli("compare", older, newer, "--format", "json")
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertFalse(data["interpretation_included"])
            self.assertEqual(data["entrants"][0]["title"], "丙书")
            self.assertEqual(data["exits"][0]["title"], "乙书")
            self.assertEqual(data["rank_changes"][0]["rank_change"], -1)
            self.assertTrue(data["signal_weight_changes"])

    def test_compare_rejects_different_chart_or_platform(self):
        with tempfile.TemporaryDirectory() as temp:
            older = self.write_snapshot(temp, "older.jsonl", [record(1, "甲书", "甲作者")])
            newer_chart = self.write_snapshot(
                temp,
                "newer-chart.jsonl",
                [record(1, "甲书", "甲作者", captured_at="2026-07-08", chart="女频新书榜")],
            )
            result = self.run_cli("compare", older, newer_chart)
            self.assertEqual(result.returncode, 2)
            self.assertIn("different chart", result.stderr)

            newer_platform = self.write_snapshot(
                temp,
                "newer-platform.jsonl",
                [record(1, "甲书", "甲作者", captured_at="2026-07-08", platform="另一平台")],
            )
            result = self.run_cli("compare", older, newer_platform)
            self.assertEqual(result.returncode, 2)
            self.assertIn("different platform", result.stderr)


if __name__ == "__main__":
    unittest.main()
