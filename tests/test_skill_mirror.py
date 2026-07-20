from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "sync_skill_mirror.py"


class SkillMirrorTests(unittest.TestCase):
    def test_sync_copies_skill_surface_without_deleting_extras(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            mirror = root / "mirror"
            (source / "scripts").mkdir(parents=True)
            mirror.mkdir()
            (source / "SKILL.md").write_text("source", encoding="utf-8")
            (source / "scripts/tool.py").write_text("print('ok')", encoding="utf-8")
            (mirror / "SKILL.md").write_text("old", encoding="utf-8")
            (mirror / "personal.txt").write_text("keep", encoding="utf-8")

            before = subprocess.run(
                [sys.executable, str(SCRIPT), "check", str(source), str(mirror)],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(1, before.returncode)
            self.assertIn("SKILL.md", json.loads(before.stdout)["changed"])

            subprocess.run(
                [sys.executable, str(SCRIPT), "sync", str(source), str(mirror)],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            after = subprocess.run(
                [sys.executable, str(SCRIPT), "check", str(source), str(mirror)],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertTrue(json.loads(after.stdout)["in_sync"])
            self.assertEqual("keep", (mirror / "personal.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
