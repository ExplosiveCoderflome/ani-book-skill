from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "asset_graph.py"
NOVELCTL = ROOT / "scripts" / "novelctl.py"


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

    @staticmethod
    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def run_cli(self, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, arguments)],
            cwd=ROOT,
            check=check,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def run_novelctl(self, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(NOVELCTL), *map(str, arguments)],
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

    def candidate(self, asset_id: str, *, namespace: str = "reusable", governance: str = "author_approval", relationships: list[dict] | None = None, accepted: bool = True, kind: str | None = None, content: dict | None = None) -> Path:
        path = self.root / f"{asset_id}.yaml"
        value = {
            "id": asset_id,
            "namespace": namespace,
            "kind": kind or ("mechanism" if namespace == "reusable" else "world_rule"),
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
            "content": content or {"rule": "只作为创作约束，不替代本书事实。"},
            "relationships": relationships or [],
        }
        path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return path

    def event_candidate(self, asset_id: str, sequence: int, participants: list[str], *, precedes: list[str] | None = None, follows: list[str] | None = None, governance: str = "author_approval") -> Path:
        return self.candidate(
            asset_id,
            namespace="universe",
            kind="event",
            governance=governance,
            content={
                "canon": {
                    "sequence": sequence,
                    "participants": participants,
                    "effects": f"{asset_id} 对共享宇宙造成的已定稿影响。",
                    "precedes": precedes or [],
                    "follows": follows or [],
                },
            },
        )

    def init_library(self) -> None:
        result = self.run_cli("init", self.library)
        self.assertEqual(1, json.loads(result.stdout)["manifest"]["revision"])

    def write_selection(self, asset_id: str, *, purpose: str = "本章必须遵守该机制。", constraints: list[str] | None = None) -> Path:
        link = yaml.safe_load((self.workspace / "continuity/data/asset-links.yaml").read_text(encoding="utf-8"))[0]
        selection = {
            "schema_version": 1,
            "chapter": "chapter-001",
            "assets": [{
                "asset_id": asset_id,
                "purpose": purpose,
                "constraints": constraints or ["不得改变既有规则。"],
                "mode": link["mode"],
                "library_version": link["library_version"],
                "library_hash": link["library_hash"],
                "local_path": link["local_path"],
                "local_hash": link["local_hash"],
            }],
        }
        path = self.workspace / "context-packages/chapter-001.assets.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(selection, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return path

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

    def test_selection_context_is_pinned_bounded_and_blocks_conflicts(self) -> None:
        self.init_library()
        self.run_cli("publish", self.library, self.candidate("ASSET-SYNC"), "--author-approved")
        self.run_cli("import", self.library, self.workspace, "ASSET-SYNC", "--mode", "sync")
        selection = self.write_selection("ASSET-SYNC")
        validated = json.loads(self.run_cli("validate-selection", self.library, self.workspace, selection).stdout)
        self.assertEqual(1, validated["assets"])
        context = self.run_novelctl(
            "context", self.workspace, "--chapter", "1", "--max-chars", "1000",
            "--asset-library", self.library, "--asset-selection", selection.relative_to(self.workspace),
        )
        self.assertLessEqual(len(context.stdout), 1000)
        self.assertIn("ASSET-SYNC", context.stdout)
        self.assertIn("固定版本", context.stdout)
        self.assertIn("cross-book-assets/ASSET-SYNC.yaml", context.stdout)

        local = self.workspace / "cross-book-assets/ASSET-SYNC.yaml"
        local.write_text(local.read_text(encoding="utf-8") + "# 本书冲突\n", encoding="utf-8")
        self.run_cli("reconcile", self.library, self.workspace)
        status = json.loads(self.run_novelctl("status", self.workspace).stdout)
        self.assertEqual(1, status["cross_book_assets"]["conflict"])
        invalid = self.run_cli("validate-selection", self.library, self.workspace, selection, check=False)
        self.assertNotEqual(0, invalid.returncode)
        self.assertIn("sync conflict", invalid.stderr)
        blocked = self.run_novelctl(
            "start-step", self.workspace, "--step", "context_package", "--target", "chapter_001",
            "--artifact", "context-packages/chapter-001.md", check=False,
        )
        self.assertEqual(2, blocked.returncode)
        self.assertIn("sync conflict", blocked.stderr)
        self.assertIn("本书冲突", local.read_text(encoding="utf-8"))

    def test_selection_rejects_unimported_assets_and_keeps_update_available_snapshot(self) -> None:
        self.init_library()
        self.run_cli("publish", self.library, self.candidate("ASSET-SYNC"), "--author-approved")
        self.run_cli("import", self.library, self.workspace, "ASSET-SYNC", "--mode", "sync")
        selection = self.write_selection("ASSET-SYNC")
        original = (self.workspace / "cross-book-assets/ASSET-SYNC.yaml").read_text(encoding="utf-8")
        updated = yaml.safe_load(self.candidate("ASSET-SYNC").read_text(encoding="utf-8"))
        updated["content"]["rule"] = "共享版本已更新。"
        update_path = self.root / "updated.yaml"
        update_path.write_text(yaml.safe_dump(updated, allow_unicode=True, sort_keys=False), encoding="utf-8")
        self.run_cli("publish", self.library, update_path, "--author-approved")
        self.run_cli("reconcile", self.library, self.workspace)
        context = self.run_cli("selection-context", self.library, self.workspace, selection, "--max-chars", "800")
        self.assertIn("共享库有新版本", context.stdout)
        self.assertEqual(original, (self.workspace / "cross-book-assets/ASSET-SYNC.yaml").read_text(encoding="utf-8"))

        selection_data = yaml.safe_load(selection.read_text(encoding="utf-8"))
        selection_data["assets"][0]["asset_id"] = "ASSET-NOT-IMPORTED"
        selection.write_text(yaml.safe_dump(selection_data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        rejected = self.run_cli("validate-selection", self.library, self.workspace, selection, check=False)
        self.assertNotEqual(0, rejected.returncode)
        self.assertIn("unimported", rejected.stderr)

    def test_post_commit_candidate_requires_staging_evidence_and_source_fingerprint(self) -> None:
        self.init_library()
        source = self.workspace / "chapters/chapter-001/draft.md"
        staged = self.workspace / "production/asset-candidates/chapter-001/ASSET-FINAL.yaml"
        staged.parent.mkdir(parents=True)
        candidate = yaml.safe_load(self.candidate("ASSET-FINAL").read_text(encoding="utf-8"))
        candidate["source"].update({
            "workspace": self.workspace.name,
            "artifact": "chapters/chapter-001/draft.md",
            "artifact_sha256": self.digest(source),
            "continuity_committed": True,
        })
        staged.write_text(yaml.safe_dump(candidate, allow_unicode=True, sort_keys=False), encoding="utf-8")
        verified = json.loads(self.run_cli("verify-candidate", self.workspace, staged).stdout)
        self.assertTrue(verified["valid"])
        published = self.run_cli("publish", self.library, staged, "--source-workspace", self.workspace, "--author-approved")
        self.assertEqual("ASSET-FINAL", json.loads(published.stdout)["published"])
        source.write_text("# 第一章\n\n被改动的正文。\n", encoding="utf-8")
        rejected = self.run_cli("verify-candidate", self.workspace, staged, check=False)
        self.assertNotEqual(0, rejected.returncode)
        self.assertIn("source artifact changed", rejected.stderr)

    def test_rejects_legacy_workspaces(self) -> None:
        self.init_library()
        self.run_cli("publish", self.library, self.candidate("ASSET-ONE"), "--author-approved")
        legacy = self.root / "legacy"
        legacy.mkdir()
        (legacy / "novel-state.yaml").write_text("schema_version: 2\n", encoding="utf-8")
        result = self.run_cli("import", self.library, legacy, "ASSET-ONE", "--mode", "fork", check=False)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("schema v3", result.stderr)

    def test_universe_delegation_is_revocable_and_does_not_change_reusable_governance(self) -> None:
        self.init_library()
        legacy_manifest = yaml.safe_load((self.library / "library.yaml").read_text(encoding="utf-8"))
        legacy_manifest.pop("universe_id")
        legacy_manifest.pop("universe_governance")
        (self.library / "library.yaml").write_text(yaml.safe_dump(legacy_manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")
        delegated = json.loads(self.run_cli("delegate-universe", self.library, "--enabled").stdout)
        self.assertEqual("libraries", delegated["universe_id"])
        self.assertEqual("codex_delegated", delegated["governance"])

        self.run_cli("publish", self.library, self.candidate("CHAR-ONE", namespace="universe", kind="character"))
        reusable = self.run_cli("publish", self.library, self.candidate("REUSE-ONE"), check=False)
        self.assertNotEqual(0, reusable.returncode)
        self.assertIn("author-approved", reusable.stderr)

        revoked = json.loads(self.run_cli("delegate-universe", self.library).stdout)
        self.assertEqual("author_approval", revoked["governance"])
        blocked = self.run_cli("publish", self.library, self.event_candidate("EVENT-ONE", 10, ["CHAR-ONE"]), check=False)
        self.assertNotEqual(0, blocked.returncode)
        self.assertIn("author-approved", blocked.stderr)
        published = json.loads(self.run_cli("publish", self.library, self.event_candidate("EVENT-ONE", 10, ["CHAR-ONE"]), "--author-approved").stdout)
        self.assertEqual("EVENT-ONE", published["published"])

    def test_canon_timeline_rejects_invalid_endpoints_and_preserves_same_sequence_order(self) -> None:
        self.init_library()
        missing = self.run_cli("publish", self.library, self.event_candidate("EVENT-MISSING", 1, ["CHAR-MISSING"]), "--author-approved", check=False)
        self.assertNotEqual(0, missing.returncode)
        self.assertIn("unpublished asset", missing.stderr)
        self.run_cli("publish", self.library, self.candidate("CHAR-ONE", namespace="universe", kind="character"), "--author-approved")
        self.run_cli("publish", self.library, self.event_candidate("EVENT-B", 10, ["CHAR-ONE"]), "--author-approved")
        self.run_cli("publish", self.library, self.event_candidate("EVENT-A", 10, ["CHAR-ONE"]), "--author-approved")
        reversed_order = self.run_cli("publish", self.library, self.event_candidate("EVENT-C", 5, ["CHAR-ONE"], follows=["EVENT-A"]), "--author-approved", check=False)
        self.assertNotEqual(0, reversed_order.returncode)
        self.assertIn("sequence contradicts precedence", reversed_order.stderr)
        checked = json.loads(self.run_cli("canon-check", self.library).stdout)
        self.assertTrue(checked["valid"])
        timeline = json.loads(self.run_cli("timeline", self.library).stdout)
        self.assertEqual(["EVENT-A", "EVENT-B"], [item["event_id"] for item in timeline["events"]])
        graph = json.loads(self.run_cli("build", self.library).stdout)
        self.assertEqual(2, graph["edges"])

    def test_impact_reports_only_explicit_workspace_links_selections_and_timeline_neighbors(self) -> None:
        self.init_library()
        self.run_cli("publish", self.library, self.candidate("CHAR-ONE", namespace="universe", kind="character"), "--author-approved")
        self.run_cli("publish", self.library, self.event_candidate("EVENT-ONE", 10, ["CHAR-ONE"]), "--author-approved")
        self.run_cli("import", self.library, self.workspace, "CHAR-ONE", "--mode", "sync")
        selection = self.write_selection("CHAR-ONE")
        before_link = (self.workspace / "continuity/data/asset-links.yaml").read_bytes()
        before_selection = selection.read_bytes()
        candidate = yaml.safe_load(self.candidate("CHAR-ONE", namespace="universe", kind="character").read_text(encoding="utf-8"))
        candidate["content"]["rule"] = "候选中的共享角色更新，必须先审查影响。"
        update = self.root / "CHAR-ONE-update.yaml"
        update.write_text(yaml.safe_dump(candidate, allow_unicode=True, sort_keys=False), encoding="utf-8")
        report = json.loads(self.run_cli("impact", self.library, update, "--workspace", self.workspace).stdout)
        self.assertTrue(report["review_required"])
        self.assertTrue(report["writes"] is False)
        self.assertEqual(["EVENT-ONE"], [entry["event_id"] for entry in report["timeline_events"]])
        self.assertEqual("CHAR-ONE", report["workspaces"][0]["links"][0]["asset_id"])
        self.assertEqual("requires_canon_review", report["workspaces"][0]["chapter_selections"][0]["risk"])
        self.assertEqual(before_link, (self.workspace / "continuity/data/asset-links.yaml").read_bytes())
        self.assertEqual(before_selection, selection.read_bytes())
        event_report = json.loads(self.run_cli("impact", self.library, self.event_candidate("EVENT-TWO", 20, ["CHAR-ONE"]), "--workspace", self.workspace).stdout)
        self.assertEqual("CHAR-ONE", event_report["workspaces"][0]["links"][0]["asset_id"])
        self.assertEqual("CHAR-ONE", event_report["workspaces"][0]["chapter_selections"][0]["assets"][0])


if __name__ == "__main__":
    unittest.main()
