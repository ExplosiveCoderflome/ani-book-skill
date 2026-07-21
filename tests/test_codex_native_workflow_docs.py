from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CodexNativeWorkflowDocsTests(unittest.TestCase):
    def test_required_architecture_documents_and_routes_exist(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for relative in (
            "docs/plans/codex-native-novel-production-system.md",
            "references/generation-contracts.md",
            "references/auto-director-and-recovery.md",
            "references/cross-book-asset-graph.md",
            "scripts/novelctl.py",
            "scripts/asset_graph.py",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)
        self.assertIn("references/generation-contracts.md", skill)
        self.assertIn("references/auto-director-and-recovery.md", skill)
        self.assertIn("scripts/novelctl.py", skill)
        self.assertIn("references/cross-book-asset-graph.md", skill)

    def test_complete_serial_generation_chain_is_documented(self) -> None:
        contract = (ROOT / "references" / "generation-contracts.md").read_text(encoding="utf-8")
        steps = (
            "novel_brief",
            "story_bible",
            "world_and_cast",
            "volume_strategy",
            "volume_skeleton",
            "beat_sheet",
            "chapter_plan",
            "context_package",
            "chapter_draft",
            "humanization_revision",
            "chapter_review",
            "chapter_repair",
            "continuity_update",
        )
        positions = [contract.index(step) for step in steps]
        self.assertEqual(sorted(positions), positions)

    def test_project_keeps_the_codex_only_boundary(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
        self.assertIn("Codex is the only creative", agents)
        self.assertIn("Codex is the only engine for creative", skill)
        self.assertIn("Codex 本身是唯一的创作理解", readme)
        for forbidden in ("openai==", "anthropic", "litellm", "langchain"):
            self.assertNotIn(forbidden, requirements)

    def test_skill_currency_check_is_required_before_runs_and_sync(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("first Skill run", agents)
        self.assertIn("sync_skill_mirror.py check", agents)
        self.assertIn("sync_skill_mirror.py sync", agents)
        self.assertIn("Do not hardcode a machine-specific", agents)
        self.assertNotIn("G:\\documents\\ani-book-skill", agents)
        self.assertIn("Before the first production action", skill)
        self.assertIn("sync_skill_mirror.py check", skill)
        self.assertIn("Do not silently continue with a stale installed copy", skill)
        self.assertIn("Do not assume or hardcode a machine-specific", skill)

    def test_opening_inspiration_and_two_brief_previews_are_documented(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        brief = (ROOT / "references" / "novel-brief.md").read_text(encoding="utf-8")
        routing = (ROOT / "references" / "workflow-routing.md").read_text(encoding="utf-8")
        self.assertIn("exactly five", skill)
        self.assertIn("exactly two", skill)
        for document in (brief, routing):
            self.assertIn("五条", document)
            self.assertIn("两份", document)
        self.assertIn("strong hook, character growth, setting wonder, relationship pull, and mystery investigation", skill)
        self.assertIn("不得写入 `novel-brief.md`", brief)
        self.assertNotIn("第一响应固定只问三项", brief)


if __name__ == "__main__":
    unittest.main()
