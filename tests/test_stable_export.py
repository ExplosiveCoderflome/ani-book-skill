from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
NOVELCTL = ROOT / "scripts" / "novelctl.py"


class StableExportTests(unittest.TestCase):
    def test_novelctl_exports_only_ready_prose_with_ready_continuity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "novel"
            subprocess.run(
                [sys.executable, str(NOVELCTL), "init", str(workspace), "--title", "测试小说"],
                check=True,
                capture_output=True,
                text=True,
            )
            state_path = workspace / "novel-state.yaml"
            state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
            state["opening_choices"] = {
                "status": "confirmed",
                "channel": "男频",
                "publication_format": "免费连载",
                "primary_reader_reward": "成长与反转",
            }
            for number in (1, 2):
                relative = f"chapters/chapter-{number:03d}/draft-humanized.md"
                path = workspace / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"# 第{number}章\n\n正文{number}\n", encoding="utf-8")
                state["artifacts"][f"chapter_{number:03d}_humanized"] = {
                    "path": relative,
                    "status": "ready",
                    "source": "ai_generated",
                    "protected": False,
                    "depends_on": [],
                    "sha256": "test",
                    "approval": "not_required",
                    "updated_at": None,
                }
            state["artifacts"]["chapter_001_delta"] = {
                "path": "continuity/chapter-deltas/chapter-001.md",
                "status": "ready",
                "source": "ai_generated",
                "protected": False,
                "depends_on": ["chapter_001_humanized"],
                "sha256": "test",
                "approval": "not_required",
                "updated_at": None,
            }
            state_path.write_text(yaml.safe_dump(state, allow_unicode=True, sort_keys=False), encoding="utf-8")
            output = workspace / "exports" / "stable.txt"
            result = subprocess.run(
                [sys.executable, str(NOVELCTL), "export", str(workspace), "--output", str(output)],
                check=True,
                capture_output=True,
                text=True,
            )
            rendered = output.read_text(encoding="utf-8")
            self.assertIn("正文1", rendered)
            self.assertNotIn("正文2", rendered)
            self.assertIn("第002章：连续性尚未稳定提交", result.stdout)


if __name__ == "__main__":
    unittest.main()
