from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "skill_sources.py"
COMMIT = "0123456789abcdef0123456789abcdef01234567"


class SkillSourcesTests(unittest.TestCase):
    def run_cli(self, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *arguments],
            check=check,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    @staticmethod
    def write_config(workspace: Path, payload: dict) -> None:
        path = workspace / "production/skill-sources.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")

    def test_missing_config_is_valid_and_offline(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = self.run_cli("validate", temporary)
        data = json.loads(result.stdout)
        self.assertFalse(data["configured"])
        self.assertTrue(data["valid"])

    def test_valid_sources_render_candidate_and_enabled_plans(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            self.write_config(
                workspace,
                {
                    "schema_version": 1,
                    "policy": {"enabled": True, "update_policy": "manual", "require_confirmation": True},
                    "sources": [
                        {
                            "id": "anti-ai-methods",
                            "purpose": "anti-ai",
                            "repo": "owner/repository",
                            "path": "skills/anti-ai",
                            "requested_ref": "main",
                            "status": "candidate",
                            "approval": "pending",
                        },
                        {
                            "id": "style-engine",
                            "purpose": "writing-style",
                            "repo": "owner/repository",
                            "path": "skills/style-engine",
                            "requested_ref": "v1",
                            "resolved_commit": COMMIT,
                            "content_sha256": "a" * 64,
                            "status": "enabled",
                            "approval": "confirmed",
                        },
                    ],
                },
            )
            candidate_path = workspace / "production/remote-skill-candidates/style-engine"
            candidate_path.mkdir(parents=True)
            (candidate_path / "SKILL.md").write_text("# 写法规则\n只处理表达。", encoding="utf-8")
            config = workspace / "production/skill-sources.yaml"
            data = yaml.safe_load(config.read_text(encoding="utf-8"))
            data["sources"][1].update(status="candidate", content_sha256="")
            self.write_config(workspace, data)
            report = json.loads(self.run_cli("candidate-report", str(workspace), "--source-id", "style-engine").stdout)
            data["sources"][1].update(status="enabled", content_sha256=report["content_sha256"])
            self.write_config(workspace, data)
            checked = json.loads(self.run_cli("validate", str(workspace)).stdout)
            candidate = json.loads(self.run_cli("plan", str(workspace), "--source-id", "anti-ai-methods").stdout)
            enabled = json.loads(self.run_cli("plan", str(workspace), "--source-id", "style-engine").stdout)
        self.assertEqual(2, checked["source_count"])
        self.assertEqual("candidate", candidate["plans"][0]["phase"])
        self.assertEqual("main", candidate["plans"][0]["install_ref"])
        self.assertIn("remote-skill-candidates", candidate["plans"][0]["candidate_directory"])
        self.assertEqual("enable", enabled["plans"][0]["phase"])
        self.assertEqual(COMMIT, enabled["plans"][0]["install_ref"])

    def test_rejects_untrusted_path_and_unpinned_enabled_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            self.write_config(
                workspace,
                {
                    "schema_version": 1,
                    "policy": {"enabled": True, "update_policy": "manual", "require_confirmation": True},
                    "sources": [
                        {
                            "id": "bad-source",
                            "purpose": "anti-ai",
                            "repo": "https://github.com/owner/repository",
                            "path": "../outside",
                            "status": "enabled",
                            "approval": "pending",
                        }
                    ],
                },
            )
            result = self.run_cli("validate", str(workspace), check=False)
        self.assertEqual(2, result.returncode)
        self.assertIn("owner/repository", result.stderr)
        self.assertIn("relative path", result.stderr)
        self.assertIn("resolved_commit", result.stderr)

    def test_update_plan_discovers_new_ref_without_replacing_current_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            self.write_config(workspace, {"schema_version": 1, "policy": {"enabled": True}, "sources": [{
                "id": "methods", "purpose": "anti-ai", "repo": "owner/repository", "path": "skills/methods",
                "requested_ref": "next-release", "resolved_commit": COMMIT,
                "status": "update_available", "approval": "pending",
            }]})
            path = workspace / "production/skill-sources.yaml"
            before = path.read_bytes()
            plan = json.loads(self.run_cli("plan", str(workspace)).stdout)["plans"][0]
            self.assertEqual("next-release", plan["install_ref"])
            self.assertEqual(COMMIT, plan["current_commit"])
            self.assertIn("/tree/next-release/", plan["github_tree_url"])
            self.assertEqual(before, path.read_bytes())

    def test_enabled_sources_require_real_unchanged_and_bounded_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            source = {"id": "methods", "purpose": "anti-ai", "repo": "owner/repository", "path": "skills/methods",
                      "status": "candidate", "approval": "pending", "resolved_commit": COMMIT, "max_bytes": 100}
            data = {"schema_version": 1, "policy": {"enabled": True}, "sources": [source]}
            self.write_config(workspace, data)
            missing = self.run_cli("candidate-report", str(workspace), "--source-id", "methods", check=False)
            self.assertIn("directory missing", missing.stderr)
            path = workspace / "production/remote-skill-candidates/methods/SKILL.md"
            path.parent.mkdir(parents=True)
            path.write_text("# Rules\nSmall changes only.\n", encoding="utf-8")
            snapshot = json.loads(self.run_cli("candidate-report", str(workspace), "--source-id", "methods").stdout)
            source.update(status="enabled", approval="confirmed", content_sha256=snapshot["content_sha256"])
            self.write_config(workspace, data)
            self.run_cli("validate", str(workspace))
            path.write_text("# Different rules\n", encoding="utf-8")
            changed = self.run_cli("validate", str(workspace), check=False)
            self.assertIn("does not match", changed.stderr)
            path.write_text("x" * 101, encoding="utf-8")
            oversized = self.run_cli("validate", str(workspace), check=False)
            self.assertIn("exceeds max_bytes", oversized.stderr)


if __name__ == "__main__":
    unittest.main()
