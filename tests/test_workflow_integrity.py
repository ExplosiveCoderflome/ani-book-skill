from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import novelctl as ctl


class WorkflowIntegrityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.workspace = self.root / "novel"
        ctl.ensure_workspace_directories(self.workspace)
        state = ctl.initial_state("验证小说", "auto")
        state["opening_choices"] = {"status": "confirmed", "channel": "泛读者", "publication_format": "免费", "primary_reader_reward": "解谜"}
        for key, item in state["artifacts"].items():
            self.ready_file(item, f"# {key}\n已确认。")
        state["next_action"] = ctl.decide_next(state)
        ctl.atomic_write_state(self.workspace, state)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def ready_file(self, item: dict, text: str = "已确认。") -> None:
        path = self.workspace / item["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        item.update(status="ready", approval="not_required", sha256=ctl.file_sha256(path))

    def command(self, name: str, *args: str) -> str:
        parsed = ctl.build_parser().parse_args([name, str(self.workspace), *args])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(0, parsed.handler(parsed))
        return out.getvalue()

    def step(self, step: str, filename: str, decision: str | None = None) -> None:
        relative = "chapters/chapter-001/" + filename
        self.command("start-step", "--step", step, "--target", "chapter_001", "--artifact", relative)
        path = self.workspace / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {filename}\n场景原版本。", encoding="utf-8")
        args = ["--step", step, "--target", "chapter_001", "--artifact", relative,
                "--measurement", "unavailable", "--reason", "runtime_usage_not_exposed"]
        if decision:
            args += ["--review-decision", decision]
        self.command("finish-step", *args)

    def prepare_prose(self, review: str | None = "accepted") -> None:
        for step, name in (("chapter_plan", "plan.md"), ("context_package", "context.md"),
                           ("chapter_draft", "draft.md"), ("humanization_revision", "draft-humanized.md")):
            self.step(step, name)
        if review:
            self.step("chapter_review", "review.md", review)

    def test_accepted_prose_is_protected_and_approved_revision_invalidates_review(self) -> None:
        self.prepare_prose()
        state = ctl.read_state(self.workspace)
        self.assertTrue(state["artifacts"]["chapter_001_humanized"]["protected"])
        args = ("--step", "humanization_revision", "--target", "chapter_001", "--artifact", "chapters/chapter-001/draft-humanized.md")
        with self.assertRaisesRegex(ValueError, "protected"):
            self.command("start-step", *args)
        old = (self.workspace / args[-1]).read_bytes()
        self.command("approve", "--target", "chapter_001_humanized", "--overwrite")
        self.command("start-step", *args)
        backups = list((self.workspace / "production/revisions/chapter_001_humanized").iterdir())
        self.assertEqual(old, backups[0].read_bytes())
        (self.workspace / args[-1]).write_text("未经复审的新结局。", encoding="utf-8")
        self.command("finish-step", *args, "--measurement", "unavailable", "--reason", "runtime_usage_not_exposed")
        review = ctl.read_state(self.workspace)["artifacts"]["chapter_001_review"]
        self.assertEqual("stale", review["status"])
        self.assertNotIn("review_decision", review)
        with self.assertRaisesRegex(ValueError, "accepted chapter review"):
            self.command("start-step", "--step", "continuity_update", "--target", "chapter_001", "--artifact", "chapters/chapter-001/delta.md")

    def test_content_tampering_and_contract_changes_cannot_reuse_acceptance(self) -> None:
        self.prepare_prose()
        for filename in ("plan.md", "context.md", "draft-humanized.md"):
            path = self.workspace / "chapters/chapter-001" / filename
            original = path.read_bytes()
            path.write_text("用户修改内容。", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "review input changed"):
                self.command("start-step", "--step", "continuity_update", "--target", "chapter_001", "--artifact", "chapters/chapter-001/delta.md")
            path.write_bytes(original)

    def test_review_rejects_inputs_changed_during_generation(self) -> None:
        self.prepare_prose(review=None)
        self.command("start-step", "--step", "chapter_review", "--target", "chapter_001", "--artifact", "chapters/chapter-001/review.md")
        (self.workspace / "chapters/chapter-001/review.md").write_text("已检查。", encoding="utf-8")
        (self.workspace / "chapters/chapter-001/draft-humanized.md").write_text("新的正文。", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed"):
            self.command("finish-step", "--step", "chapter_review", "--target", "chapter_001", "--artifact", "chapters/chapter-001/review.md",
                         "--review-decision", "accepted", "--measurement", "unavailable", "--reason", "runtime_usage_not_exposed")

    def test_missing_inputs_and_skipped_chapters_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "required chapter plan"):
            self.command("context", "--chapter", "1")
        with self.assertRaisesRegex(ValueError, "dependency is not ready"):
            self.command("start-step", "--step", "chapter_draft", "--target", "chapter_001", "--artifact", "chapters/chapter-001/draft.md")
        with self.assertRaisesRegex(ValueError, "chapter sequence"):
            self.command("start-step", "--step", "chapter_plan", "--target", "chapter_008", "--artifact", "chapters/chapter-008/plan.md")

    def test_volume_selection_is_explicit_and_persists(self) -> None:
        state = ctl.read_state(self.workspace)
        state["artifacts"]["volume_02_beat_sheet"] = {"path": "volumes/volume-02-beat-sheet.md", "depends_on": []}
        self.ready_file(state["artifacts"]["volume_02_beat_sheet"])
        ctl.atomic_write_state(self.workspace, state)
        args = ("--step", "chapter_plan", "--target", "chapter_001", "--artifact", "chapters/chapter-001/plan.md")
        with self.assertRaisesRegex(ValueError, "volume is ambiguous"):
            self.command("start-step", *args)
        self.command("start-step", *args, "--volume", "2")
        plan = ctl.read_state(self.workspace)["artifacts"]["chapter_001_plan"]
        self.assertEqual(2, plan["volume"])
        self.assertEqual(["volume_02_beat_sheet"], plan["depends_on"])

    def test_repair_requires_new_review_and_then_commits(self) -> None:
        self.prepare_prose(review="repair_required")
        self.step("chapter_repair", "repair.md")
        self.step("chapter_review", "review.md", "accepted")
        self.step("continuity_update", "delta.md")
        state = ctl.read_state(self.workspace)
        self.assertEqual("chapter_001", state["continuity"]["last_committed_chapter"])
        self.assertTrue(state["artifacts"]["chapter_001_repair"]["protected"])

    def test_analysis_conclusion_change_invalidates_handoff_without_source_change(self) -> None:
        root = self.root / "analysis"
        root.mkdir()
        data = {"source": {"fingerprint": "sha256:source", "scope": "第1-3章", "coverage": "sampled"}, "analysis_lens": {"status": "ready"}}
        (root / "analysis-state.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
        lens = root / "analysis-lens.md"
        lens.write_text("最初结论。", encoding="utf-8")
        state = {"novel": {"mode": "fanfic"}, "source_analysis": {"path": str(root)}}
        ctl.validate_fanfic_source(state, refresh=True)
        ctl.validate_fanfic_source(state)
        lens.write_text("作者纠正并确认后的结论。", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "analysis source changed"):
            ctl.validate_fanfic_source(state)


if __name__ == "__main__":
    unittest.main()
