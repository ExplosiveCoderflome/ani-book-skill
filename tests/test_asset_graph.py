from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "asset_graph.py"


class AssetGraphCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.library = self.root / "libraries"
        self.workspace = self.root / "novel"
        self.workspace.mkdir()
        self.write_workspace()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_cli(self, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, arguments)],
            cwd=ROOT,
            check=check,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def write_workspace(self) -> None:
        data = self.workspace / "continuity/data"
        data.mkdir(parents=True)
        (self.workspace / "chapters/chapter-001").mkdir(parents=True)
        (self.workspace / "chapters/chapter-001/draft.md").write_text("# 第一章\n\n稳定正文。\n", encoding="utf-8")
        (self.workspace / "novel-state.yaml").write_text(
            yaml.safe_dump(
                {
                    "schema_version": 3,
                    "continuity": {"last_committed_chapter": "chapter-001"},
                },
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        payloads = {
            "manifest.yaml": {"schema_version": 1, "revision": 1, "last_committed_chapter": "chapter-001", "created_at": "2026-07-20T00:00:00Z"},
            "baseline.yaml": {"baseline_chapter": "chapter-001", "confirmed_state": ["第一章已定稿"]},
            "facts.yaml": [{"id": "FACT-001", "summary": "主角获得钥匙。", "introduced_in": "chapter-001", "updated_in": "chapter-001", "evidence": {"text": "第一章正文"}, "status": "active", "tags": []}],
            "payoffs.yaml": [],
            "resources.yaml": [],
            "character-state.yaml": [{"id": "CHAR-001", "name": "主角", "current_state": [], "updated_in": "chapter-001", "tags": []}],
            "relationships.yaml": [],
        }
        for name, value in payloads.items():
            (data / name).write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")

    def candidate(self, asset_id: str, *, namespace: str = "reusable", governance: str = "author_approval", relationships: list[dict] | None = None, accepted: bool = True) -> Path:
        path = self.root / f"{asset_id}.yaml"
        value = {
            "id": asset_id,
            "namespace": namespace,
            "kind": "mechanism" if namespace == "reusable" else "world_rule",
            "title": f"{asset_id} 标题",
            "summary": f"{asset_id} 的可复用摘要。",
            "version": 1,
            "status": "active",
            "governance": governance,
            "visibility": "private",
            "source": {
                "workspace": "novels/source",
                "chapter": "chapter-001",
                "artifact": "chapters/chapter-001/draft.md",
                "artifact_sha256": "a" * 64,
                "evidence": "已验收正文中的明确机制。",
                "accepted": accepted,
            },
            "content": {"rule": "只作为创作约束，不替代本书事实。"},
            "relationships": relationships or [],
        }
        path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return path

    def init_library(self) -> None:
        result = self.run_cli("init", self.library)
        self.assertEqual(1, json.loads(result.stdout)["manifest"]["revision"])

    def test_rejects_unaccepted_candidates_and_requires_author_approval(self) -> None:
        self.init_library()
        rejected = self.run_cli("publish", self.library, self.candidate("ASSET-DRAFT", accepted=False), check=False)
        self.assertNotEqual(0, rejected.returncode)
        self.assertIn("source must be accepted", rejected.stderr)
        approval = self.run_cli("publish", self.library, self.candidate("ASSET-ONE"), check=False)
        self.assertNotEqual(0, approval.returncode)
        self.assertIn("author-approved", approval.stderr)
        published = self.run_cli("publish", self.library, self.candidate("ASSET-ONE"), "--author-approved")
        self.assertEqual("ASSET-ONE", json.loads(published.stdout)["published"])

    def test_delegation_import_modes_and_conflict_protection(self) -> None:
        self.init_library()
        self.run_cli("publish", self.library, self.candidate("ASSET-SYNC"), "--author-approved")
        delegated = self.run_cli("delegate", self.library, "ASSET-SYNC", "--enabled")
        self.assertEqual("codex_delegated", json.loads(delegated.stdout)["governance"])
        self.run_cli("import", self.library, self.workspace, "ASSET-SYNC", "--mode", "sync")
        local = self.workspace / "cross-book-assets/ASSET-SYNC.yaml"
        original = local.read_text(encoding="utf-8")

        shared_update = yaml.safe_load(self.candidate("ASSET-SYNC").read_text(encoding="utf-8"))
        shared_update["governance"] = "codex_delegated"
        shared_update["content"]["rule"] = "共享正史的已批准更新。"
        shared_candidate = self.root / "shared-update.yaml"
        shared_candidate.write_text(yaml.safe_dump(shared_update, allow_unicode=True, sort_keys=False), encoding="utf-8")
        self.run_cli("publish", self.library, shared_candidate)
        update_report = json.loads(self.run_cli("reconcile", self.library, self.workspace).stdout)
        self.assertEqual("update_available", update_report["links"][0]["status"])
        self.assertEqual(original, local.read_text(encoding="utf-8"))
        adopted = self.run_cli("resolve", self.library, self.workspace, "ASSET-SYNC", "--action", "adopt-shared")
        self.assertEqual("adopt-shared", json.loads(adopted.stdout)["action"])
        self.assertIn("共享正史的已批准更新", local.read_text(encoding="utf-8"))

        local_asset = yaml.safe_load(local.read_text(encoding="utf-8"))
        local_asset["content"]["rule"] = "本书已定稿的补充。"
        local.write_text(yaml.safe_dump(local_asset, allow_unicode=True, sort_keys=False), encoding="utf-8")
        report = json.loads(self.run_cli("reconcile", self.library, self.workspace).stdout)
        self.assertEqual("conflict", report["links"][0]["status"])
        self.assertIn("本书已定稿的补充", local.read_text(encoding="utf-8"))
        published_local = self.run_cli("resolve", self.library, self.workspace, "ASSET-SYNC", "--action", "publish-local")
        self.assertEqual("publish-local", json.loads(published_local.stdout)["action"])
        self.assertIn("本书已定稿的补充", (self.library / "assets/ASSET-SYNC.yaml").read_text(encoding="utf-8"))

        links = yaml.safe_load((self.workspace / "continuity/data/asset-links.yaml").read_text(encoding="utf-8"))
        self.assertEqual("sync", links[0]["mode"])
        revoked = self.run_cli("delegate", self.library, "ASSET-SYNC")
        self.assertEqual("author_approval", json.loads(revoked.stdout)["governance"])
        local_asset = yaml.safe_load(local.read_text(encoding="utf-8"))
        local_asset["content"]["rule"] = "撤销委托后的本书修改。"
        local.write_text(yaml.safe_dump(local_asset, allow_unicode=True, sort_keys=False), encoding="utf-8")
        rejected = self.run_cli("resolve", self.library, self.workspace, "ASSET-SYNC", "--action", "publish-local", check=False)
        self.assertNotEqual(0, rejected.returncode)
        self.assertIn("author-approved", rejected.stderr)
        retained = self.run_cli("resolve", self.library, self.workspace, "ASSET-SYNC", "--action", "keep-local")
        self.assertEqual("fork", yaml.safe_load((self.workspace / "continuity/data/asset-links.yaml").read_text(encoding="utf-8"))[0]["mode"])
        self.assertEqual("keep-local", json.loads(retained.stdout)["action"])

    def test_builds_isolated_library_and_workspace_graphs_with_bounded_context(self) -> None:
        self.init_library()
        self.run_cli("publish", self.library, self.candidate("ASSET-TARGET"), "--author-approved")
        relation = [{"target": "ASSET-TARGET", "relation": "enables", "evidence": "机制依赖该规则。", "confidence": 0.9}]
        self.run_cli("publish", self.library, self.candidate("ASSET-SOURCE", relationships=relation), "--author-approved")
        library_graph = json.loads(self.run_cli("build", self.library).stdout)
        self.assertEqual(2, library_graph["nodes"])
        self.assertEqual(1, library_graph["edges"])
        neighborhood = json.loads(self.run_cli("neighbors", self.library / "graph", "ASSET-SOURCE", "--depth", "1").stdout)
        self.assertEqual({"ASSET-SOURCE", "ASSET-TARGET"}, {item["id"] for item in neighborhood["nodes"]})
        self.run_cli("import", self.library, self.workspace, "ASSET-SOURCE", "--mode", "fork")
        workspace_graph = json.loads(self.run_cli("build-workspace", self.library, self.workspace).stdout)
        self.assertGreaterEqual(workspace_graph["nodes"], 3)
        context = self.run_cli("context", self.library, self.workspace, "--assets", "ASSET-SOURCE", "--max-depth", "1")
        self.assertIn("ASSET-SOURCE", context.stdout)
        self.assertIn("ASSET-TARGET", context.stdout)

    def test_validates_relationship_endpoints_and_published_fingerprints(self) -> None:
        self.init_library()
        dangling = [{"target": "ASSET-MISSING", "relation": "depends_on", "evidence": "需要对应规则。", "confidence": 0.8}]
        rejected = self.run_cli("publish", self.library, self.candidate("ASSET-DANGLING", relationships=dangling), "--author-approved", check=False)
        self.assertNotEqual(0, rejected.returncode)
        self.assertIn("references missing asset", rejected.stderr)
        self.run_cli("publish", self.library, self.candidate("ASSET-TARGET"), "--author-approved")
        self.run_cli("publish", self.library, self.candidate("ASSET-SOURCE", relationships=[{"target": "ASSET-TARGET", "relation": "depends_on", "evidence": "需要对应规则。", "confidence": 0.8}]), "--author-approved")
        source_path = self.library / "assets/ASSET-SOURCE.yaml"
        published = yaml.safe_load(source_path.read_text(encoding="utf-8"))
        published["content"]["rule"] = "指纹被篡改。"
        source_path.write_text(yaml.safe_dump(published, allow_unicode=True, sort_keys=False), encoding="utf-8")
        invalid = self.run_cli("validate", self.library, check=False)
        self.assertNotEqual(0, invalid.returncode)
        self.assertIn("content_sha256", invalid.stderr)

    def test_rejects_legacy_workspaces(self) -> None:
        self.init_library()
        self.run_cli("publish", self.library, self.candidate("ASSET-ONE"), "--author-approved")
        legacy = self.root / "legacy"
        legacy.mkdir()
        (legacy / "novel-state.yaml").write_text("schema_version: 2\n", encoding="utf-8")
        result = self.run_cli("import", self.library, legacy, "ASSET-ONE", "--mode", "fork", check=False)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("schema v3", result.stderr)


if __name__ == "__main__":
    unittest.main()
