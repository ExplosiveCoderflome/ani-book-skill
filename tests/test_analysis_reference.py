from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


class AnalysisReferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.analysis = self.root / "analysis"
        self.novel = self.root / "novel"
        (self.analysis / "notes").mkdir(parents=True)
        self.note = self.analysis / "notes/segment-001.md"
        self.note.write_text("# 已读笔记\n\n原始片段内容不应进入小说上下文。", encoding="utf-8")
        self.source = {"fingerprint": "sha256:" + "a" * 64, "scope": "第1-50章", "coverage": "sampled"}
        self.analysis_state = {"schema_version": 1, "source": self.source.copy(), "artifacts": {"note": {"path": "notes/segment-001.md", "status": "ready", "sha256": self.digest(self.note)}}}
        self.write(self.analysis / "analysis-state.yaml", self.analysis_state)
        self.card = {"id": "PATTERN-001", "title": "主动验证", "status": "ready", "scope": "第1-2章", "core_promise": "持续获得关系真相与失控风险", "stimulus_object": "被隐瞒的关系选择", "viewing_position": "主角主动核验并承担看见后的代价", "psychological_progression": "从好奇推进到羞耻与失去控制", "return_attachment": "核验后必须重新选择是否留在关系中", "problem": "揭示缺少行动", "mechanism": "让主角选择带来验证代价", "prerequisites": ["有可行动线索"], "payoff": "答案与压力", "failure_modes": ["没有代价"], "forbidden_elements": ["独特源作设定"], "evidence": [{"path": "notes/segment-001.md", "sha256": self.digest(self.note)}]}
        self.data = {"schema_version": 1, "source": self.source.copy(), "cards": [self.card]}
        self.call("novelctl.py", "init", str(self.novel), "--title", "原创作品")
        (self.novel / "novel-brief.md").write_text("# 本书定位\n必须保留原创约束。", encoding="utf-8")
        plan = self.novel / "chapters/chapter-001/plan.md"
        plan.parent.mkdir(parents=True, exist_ok=True)
        plan.write_text("# 本章计划\n先核对证据，再选择行动。", encoding="utf-8")
        self.selection = {"schema_version": 1, "chapter": 1, "max_chars": 2200, "items": [{"analysis_workspace": str(self.analysis), "pattern_id": "PATTERN-001", "registry_sha256": "", "use_for": "推动本章主角目标", "adaptation": "主角承担公开证据的风险", "avoid": ["源作场景组合"], "success_check": "选择是否产生新代价"}]}
        self.refresh_registry()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def write(path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")

    def refresh_registry(self) -> None:
        self.write(self.analysis / "pattern-cards.yaml", self.data)
        self.selection["items"][0]["registry_sha256"] = self.digest(self.analysis / "pattern-cards.yaml")
        self.write(self.novel / "context-packages/chapter-001.references.yaml", self.selection)

    def call(self, script: str, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / script), *arguments], capture_output=True, text=True, encoding="utf-8")
        if check:
            self.assertEqual(0, result.returncode, result.stderr)
        return result

    def test_bounded_context_uses_mechanism_and_adaptation_preserving_authority(self) -> None:
        files = [self.analysis / "analysis-state.yaml", self.note, self.novel / "novel-state.yaml"]
        before = [path.read_bytes() for path in files]
        inspected = json.loads(self.call("analysis_reference.py", "inspect", str(self.analysis)).stdout)
        self.assertTrue(inspected["cards"][0]["usable"])
        self.call("analysis_reference.py", "validate", str(self.novel), "--chapter", "1")
        result = self.call("novelctl.py", "context", str(self.novel), "--chapter", "1", "--output", "context-packages/chapter-001.md")
        report = json.loads(result.stdout)
        self.assertIn("context-packages/chapter-001.references.yaml", report["sources"])
        content = (self.novel / "context-packages/chapter-001.md").read_text(encoding="utf-8")
        self.assertIn("必须保留原创约束", content)
        self.assertIn("PATTERN-001", content)
        self.assertIn("主角承担公开证据的风险", content)
        self.assertIn("持续获得关系真相与失控风险", content)
        self.assertIn("主角主动核验并承担看见后的代价", content)
        self.assertIn("第1-2章", content)
        self.assertIn("选择是否产生新代价", content)
        self.assertNotIn("原始片段内容不应进入小说上下文", content)
        self.assertEqual(before, [path.read_bytes() for path in files])
        state_path = self.novel / "novel-state.yaml"
        state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
        state["continuity"]["last_committed_chapter"] = "chapter-001"
        self.write(state_path, state)
        for name in ("baseline", "fact-ledger", "payoff-ledger", "resource-ledger"):
            path = self.novel / "continuity" / f"{name}.md"
            path.parent.mkdir(exist_ok=True)
            path.write_text(f"# {name}\n\n基线章节：chapter-001\n\n| ID |\n| --- |\n", encoding="utf-8")
        self.call("continuity_store.py", "migrate", str(self.novel))
        structured = self.call("novelctl.py", "context", str(self.novel), "--chapter", "1").stdout
        self.assertIn("连续性上下文", structured)
        self.assertIn("PATTERN-001", structured)

    def test_changed_evidence_blocks_start_and_finish_before_state_write(self) -> None:
        state_path = self.novel / "novel-state.yaml"
        state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
        state["artifacts"]["chapter_001_plan"] = {"path": "chapters/chapter-001/plan.md", "status": "in_progress"}
        self.write(state_path, state)
        before = state_path.read_bytes()
        self.note.write_text("# 用户修改了证据", encoding="utf-8")
        for command, extra in [("start-step", []), ("finish-step", ["--measurement", "unavailable", "--reason", "runtime_usage_not_exposed"])]:
            result = self.call("novelctl.py", command, str(self.novel), "--step", "chapter_plan", "--target", "chapter_001", "--artifact", "chapters/chapter-001/plan.md", *extra, check=False)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("evidence changed", result.stderr)
            self.assertEqual(before, state_path.read_bytes())
        context = self.call("novelctl.py", "context", str(self.novel), "--chapter", "1", check=False)
        self.assertNotEqual(0, context.returncode)
        self.assertIn("evidence changed", context.stderr)

    def test_scope_registry_readiness_and_budget_require_explicit_review(self) -> None:
        self.analysis_state["source"]["scope"] = "第1-60章"
        self.write(self.analysis / "analysis-state.yaml", self.analysis_state)
        result = self.call("analysis_reference.py", "validate", str(self.novel), "--chapter", "1", check=False)
        self.assertIn("scope changed", result.stderr)
        self.write(self.analysis / "analysis-state.yaml", {**self.analysis_state, "source": self.source.copy()})
        self.card["status"] = "stale"
        self.refresh_registry()
        result = json.loads(self.call("analysis_reference.py", "inspect", str(self.analysis)).stdout)
        self.assertFalse(result["cards"][0]["usable"])
        self.card["status"] = "ready"
        self.selection["max_chars"] = 120
        self.refresh_registry()
        result = self.call("novelctl.py", "context", str(self.novel), "--chapter", "1", check=False)
        self.assertIn("exceeds 120", result.stderr)
        self.selection["max_chars"] = 4000
        self.refresh_registry()
        self.call("analysis_reference.py", "validate", str(self.novel), "--chapter", "1")
        self.card["payoff"] = "修改后的回报"
        self.write(self.analysis / "pattern-cards.yaml", self.data)
        result = self.call("analysis_reference.py", "validate", str(self.novel), "--chapter", "1", check=False)
        self.assertIn("registry changed", result.stderr)

    def test_traversal_missing_application_and_chapter_mismatch_are_rejected(self) -> None:
        self.card["evidence"][0]["path"] = "../outside.md"
        self.refresh_registry()
        result = self.call("analysis_reference.py", "validate", str(self.novel), "--chapter", "1", check=False)
        self.assertNotEqual(0, result.returncode)
        self.card["evidence"][0]["path"] = "notes/segment-001.md"
        self.selection["items"][0]["adaptation"] = ""
        self.refresh_registry()
        result = self.call("analysis_reference.py", "validate", str(self.novel), "--chapter", "1", check=False)
        self.assertIn("adaptation", result.stderr)
        self.selection["chapter"] = 2
        self.refresh_registry()
        result = self.call("analysis_reference.py", "validate", str(self.novel), "--chapter", "1", check=False)
        self.assertIn("chapter mismatch", result.stderr)

    def test_core_contract_is_required_for_mechanism_cards(self) -> None:
        self.card.pop("core_promise")
        self.refresh_registry()
        result = self.call("analysis_reference.py", "inspect", str(self.analysis))
        inspected = json.loads(result.stdout)
        self.assertFalse(inspected["cards"][0]["usable"])
        self.assertIn("core_promise", inspected["cards"][0]["error"])

    def test_genre_specific_dimensions_are_optional(self) -> None:
        for key in ("stimulus_object", "viewing_position", "psychological_progression", "return_attachment"):
            self.card.pop(key)
        self.refresh_registry()
        self.call("analysis_reference.py", "validate", str(self.novel), "--chapter", "1")
        context = self.call("analysis_reference.py", "context", str(self.novel), "--chapter", "1").stdout
        self.assertIn("核心阅读承诺", context)
        self.assertNotIn("回归/依恋", context)

    def test_stale_registry_and_unconfirmed_lens_block_ready_cards(self) -> None:
        self.analysis_state["artifacts"]["patterns"] = {"path": "pattern-cards.yaml", "status": "stale"}
        self.write(self.analysis / "analysis-state.yaml", self.analysis_state)
        result = self.call("analysis_reference.py", "validate", str(self.novel), "--chapter", "1", check=False)
        self.assertIn("registry is not ready", result.stderr)
        self.analysis_state["artifacts"]["patterns"]["status"] = "ready"
        self.analysis_state["analysis_lens"] = {"status": "pending_confirm"}
        self.write(self.analysis / "analysis-state.yaml", self.analysis_state)
        result = self.call("novelctl.py", "context", str(self.novel), "--chapter", "1", check=False)
        self.assertIn("lens is not ready", result.stderr)


if __name__ == "__main__":
    unittest.main()
