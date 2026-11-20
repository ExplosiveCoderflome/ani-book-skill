from __future__ import annotations

import contextlib
import io
import json
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

    def step(self, step: str, filename: str, decision: str | None = None, *, chapter: int = 1, content: str | None = None) -> None:
        relative = f"chapters/chapter-{chapter:03d}/{filename}"
        args = ["--step", step, "--target", f"chapter_{chapter:03d}", "--artifact", relative]
        self.command("start-step", *args)
        path = self.workspace / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content or f"# {filename}\n场景原版本。", encoding="utf-8")
        args += ["--measurement", "unavailable", "--reason", "runtime_usage_not_exposed"]
        if decision:
            args += ["--review-decision", decision]
        self.command("finish-step", *args)

    def prepare_prose(self, review: str | None = "accepted", *, chapter: int = 1) -> None:
        for step, name in (("chapter_plan", "plan.md"), ("context_package", "context.md"),
                           ("chapter_draft", "draft.md"), ("humanization_revision", "draft-humanized.md")):
            self.step(step, name, chapter=chapter)
        if review:
            self.step("chapter_review", "review.md", review, chapter=chapter)

    def test_later_style_changes_preserve_stable_export_and_validation(self) -> None:
        self.prepare_prose()
        self.step("continuity_update", "delta.md")
        style = self.workspace / "writing-style.md"
        style.write_text("使用短句。", encoding="utf-8")
        self.command("reconcile")
        self.prepare_prose(chapter=2)
        before = ctl.read_state(self.workspace)["artifacts"]["chapter_002_review"]["review_inputs"]
        self.assertEqual(ctl.file_sha256(style), before["writing_style"]["sha256"])
        style.write_text("对白随人物而变。", encoding="utf-8")
        self.command("reconcile")
        self.step("continuity_update", "delta.md", chapter=2)
        self.command("validate")
        out = self.root / "export.txt"
        self.command("export", "--output", str(out))
        self.assertEqual(2, out.read_text(encoding="utf-8-sig").count("场景原版本。"))
        state = ctl.read_state(self.workspace)
        self.assertEqual(before, state["artifacts"]["chapter_002_review"]["review_inputs"])
        (self.workspace / "chapters/chapter-001/draft-humanized.md").write_text("未重新验收", encoding="utf-8")
        self.command("export", "--output", str(out))
        self.assertEqual(1, out.read_text(encoding="utf-8-sig").count("场景原版本。"))

    def test_one_sentence_to_verified_book_and_reopening(self) -> None:
        self.workspace = self.root / "paper"
        idea = "修书匠能听到被删去的最后一句话。"
        self.command("init", "--title", "末行", "--idea", idea, "--mode", "auto")
        self.command("set-opening-choices", "--channel", "泛读者", "--publication-format", "单行本",
                     "--primary-reader-reward", "解谜", "--delegated")
        for key, item in ctl.initial_artifacts("auto").items():
            args = ("--step", ctl.step_from_key(key), "--target", key, "--artifact", item["path"])
            self.command("start-step", *args)
            (self.workspace / item["path"]).write_text(idea, encoding="utf-8")
            finished = json.loads(self.command("finish-step", *args, "--measurement", "unavailable", "--reason", "runtime_usage_not_exposed"))
            self.assertEqual(key, finished["finished"])
            self.assertEqual("unavailable", finished["usage"]["event"]["measurement"])
        self.command("set-ending", "--chapter", "2")
        self.command("approve", "--target", "chapter_range", "--range-start", "1", "--range-end", "1")
        self.assertEqual(idea, ctl.read_state(self.workspace)["novel"]["idea"])
        with self.assertRaisesRegex(ValueError, "commit the declared ending"):
            self.command("finish-book", "--check")
        self.prepare_prose(chapter=1)
        self.step("continuity_update", "delta.md")
        self.assertEqual("request_chapter_range", json.loads(self.command("next"))["type"])
        self.command("approve", "--target", "chapter_range", "--range-start", "2", "--range-end", "2")
        self.prepare_prose("repair_required", chapter=2)
        self.step("chapter_repair", "repair.md", chapter=2, content="# 归还\n她把末行抄回母亲的信，纸上第一次安静下来。")
        self.step("chapter_review", "review.md", "accepted", chapter=2)
        self.step("continuity_update", "delta.md", chapter=2)
        self.assertEqual("review_book", json.loads(self.command("next"))["type"])
        with self.assertRaisesRegex(ValueError, "declared ending"):
            self.command("context", "--chapter", "3")
        check = json.loads(self.command("finish-book", "--check"))
        report = self.workspace / check["review"]
        self.assertFalse(report.exists())
        self.assertEqual([], list((self.workspace / "exports").iterdir()))
        with self.assertRaisesRegex(ValueError, "manuscript changed"):
            self.command("finish-book", "--reviewed-version", "out-of-date")
        with self.assertRaisesRegex(ValueError, "record the conclusion"):
            self.command("finish-book", "--reviewed-version", check["version"])
        report.write_text("旧稿的结论。", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "review_marker"):
            self.command("finish-book", "--reviewed-version", check["version"])
        report.write_text(check["review_marker"] + "\n第二章以补回母亲的末行兑现承诺。", encoding="utf-8")
        receipt = json.loads(self.command("finish-book", "--reviewed-version", check["version"]))
        output = self.workspace / receipt["path"]
        body = output.read_text(encoding="utf-8-sig")
        self.assertEqual(1, body.count("场景原版本。"))
        self.assertLess(body.index("场景原版本。"), body.index("纸上第一次安静下来"))
        self.assertEqual(receipt, json.loads(self.command("finish-book", "--reviewed-version", check["version"])))
        self.assertEqual("book_complete", json.loads(self.command("next"))["type"])
        self.command("validate")
        delta = self.workspace / "chapters/chapter-001/delta.md"
        original = delta.read_bytes()
        delta.unlink()
        self.assertNotEqual("book_complete", json.loads(self.command("next"))["type"])
        with self.assertRaisesRegex(ValueError, "chapter_001_delta"):
            self.command("finish-book", "--check")
        delta.write_bytes(original)
        output.write_bytes(b"author's copy")
        with self.assertRaisesRegex(ValueError, "export has been edited"):
            self.command("finish-book", "--reviewed-version", check["version"])
        self.assertEqual(b"author's copy", output.read_bytes())
        self.command("set-ending", "--chapter", "3")
        self.assertEqual("request_chapter_range", json.loads(self.command("next"))["type"])

    def test_revised_historical_chapter_can_recommit_without_rewinding_progress(self) -> None:
        for chapter in (1, 2):
            self.prepare_prose(chapter=chapter)
            self.step("continuity_update", "delta.md", chapter=chapter)
        self.command("approve", "--target", "chapter_001_humanized", "--overwrite")
        self.step("humanization_revision", "draft-humanized.md", content="新结局。")
        with self.assertRaisesRegex(ValueError, "accepted chapter review"):
            self.command("start-step", "--step", "continuity_update", "--target", "chapter_001",
                         "--artifact", "chapters/chapter-001/delta.md")
        self.step("chapter_review", "review.md", "accepted")
        state = ctl.read_state(self.workspace)
        self.assertEqual("chapter_001_delta", state["next_action"]["target"])
        with self.assertRaisesRegex(ValueError, "recommit continuity for chapter_001"):
            self.command("start-step", "--step", "chapter_plan", "--target", "chapter_003",
                         "--artifact", "chapters/chapter-003/plan.md")
        self.step("continuity_update", "delta.md", content="根据新结局更新事实。")
        state = ctl.read_state(self.workspace)
        self.assertEqual("ready", state["artifacts"]["chapter_001_delta"]["status"])
        self.assertEqual("chapter_002", state["continuity"]["last_committed_chapter"])
        self.assertEqual("chapter_003_plan", state["next_action"]["target"])
        self.command("validate")
        out = self.root / "export.txt"
        self.command("export", "--output", str(out))
        self.assertIn("新结局。", out.read_text(encoding="utf-8-sig"))

    def test_hard_book_length_counts_only_accepted_body_and_survives_resume(self) -> None:
        self.command("set-ending", "--chapter", "2", "--min-body-han", "100000")
        self.prepare_prose()
        self.assertEqual(0, json.loads(self.command("status", "--measure-length"))["length"]["body_han"])
        self.step("continuity_update", "delta.md")
        self.command("set-ending", "--chapter", "1")
        length = json.loads(self.command("status", "--measure-length"))["length"]
        self.assertEqual({"1": 5}, length["chapter_body_han"])
        self.assertEqual(99995, length["remaining_body_han"])
        with self.assertRaisesRegex(ValueError, "minimum 100000, short by 99995"):
            self.command("finish-book", "--check")
        self.assertEqual([], list((self.workspace / "exports").iterdir()))
        with self.assertRaisesRegex(ValueError, "positive"):
            self.command("set-ending", "--chapter", "1", "--min-body-han", "0")
        self.command("set-ending", "--chapter", "1", "--min-body-han", "5")
        check = json.loads(self.command("finish-book", "--check"))
        self.assertEqual(5, check["body_han"])
        (self.workspace / check["review"]).write_text(check["review_marker"] + "\n末章已审。", encoding="utf-8")
        self.command("finish-book", "--reviewed-version", check["version"])
        self.command("set-ending", "--chapter", "1", "--min-body-han", "4")
        self.assertEqual("review_book", json.loads(self.command("next"))["type"])
        with self.assertRaisesRegex(ValueError, "manuscript changed"):
            self.command("finish-book", "--reviewed-version", check["version"])

    def test_body_han_count_excludes_headings_punctuation_and_editorial_comments(self) -> None:
        text = "## 卷名\n〇點，𠮷来。123Ａ\n<!-- 不计\n这段 -->\n"
        self.assertEqual(4, ctl.book_completion.body_han_count(text))

    def test_rolling_beats_preserve_committed_prose_and_refresh_the_unwritten_chapter(self) -> None:
        self.prepare_prose()
        self.step("continuity_update", "delta.md")
        self.step("chapter_plan", "plan.md", chapter=2)
        key = "volume_01_beat_sheet"
        sheet = "volumes/volume-01-beat-sheet.md"
        args = ("--step", "beat_sheet", "--target", key, "--artifact", sheet)
        self.command("start-step", *args)
        (self.workspace / sheet).write_text("第一章证物已毁，第二章改找证人。", encoding="utf-8")
        self.command("finish-step", *args, "--measurement", "unavailable", "--reason", "runtime_usage_not_exposed")
        state = ctl.read_state(self.workspace)
        self.assertEqual("ready", state["artifacts"]["chapter_001_delta"]["status"])
        self.assertEqual("stale", state["artifacts"]["chapter_002_plan"]["status"])
        self.step("chapter_plan", "plan.md", chapter=2)
        (self.workspace / sheet).write_text("证人已经离开，第二章必须追赶。", encoding="utf-8")
        result = json.loads(self.command("reconcile"))
        self.assertEqual([], result["protected_conflicts"])
        self.assertEqual(["chapter_002_plan"], result["stale"])
        self.command("validate")

    def test_closure_reopens_committed_final_chapter_for_repair_before_delta(self) -> None:
        self.command("set-ending", "--chapter", "1")
        self.prepare_prose()
        self.step("continuity_update", "delta.md")
        self.assertEqual("review_book", json.loads(self.command("next"))["type"])
        self.step("chapter_review", "review.md", "repair_required")
        self.assertEqual("chapter_001_repair", json.loads(self.command("next"))["target"])
        self.step("chapter_repair", "repair.md", content="第一次补写。")
        self.assertEqual("chapter_001_review", json.loads(self.command("next"))["target"])
        self.step("chapter_review", "review.md", "repair_required")
        self.assertEqual("chapter_001_repair", json.loads(self.command("next"))["target"])
        self.step("chapter_repair", "repair.md", content="她当众叫出了妹妹的名字。")
        self.step("chapter_review", "review.md", "accepted")
        self.assertEqual("chapter_001_delta", json.loads(self.command("next"))["target"])
        self.step("continuity_update", "delta.md", content="当众正名。")
        self.assertEqual("review_book", json.loads(self.command("next"))["type"])

    def test_completed_range_requires_explicit_approval_to_continue(self) -> None:
        self.command("approve", "--target", "chapter_range", "--range-start", "1", "--range-end", "1")
        self.prepare_prose()
        self.step("continuity_update", "delta.md")
        state_path = self.workspace / "novel-state.yaml"
        before = state_path.read_bytes()
        args = ("--step", "chapter_plan", "--target", "chapter_002", "--artifact", "chapters/chapter-002/plan.md")
        with self.assertRaisesRegex(ValueError, "chapter_range"):
            self.command("start-step", *args)
        with self.assertRaisesRegex(ValueError, "chapter_range"):
            self.command("start-step", *args, "--range-start", "2", "--range-end", "3")
        with self.assertRaisesRegex(ValueError, "chapter_range"):
            self.command("context", "--chapter", "2", "--output", "chapter-002.md")
        self.assertFalse((self.workspace / "chapter-002.md").exists())
        self.assertEqual(before, state_path.read_bytes())
        self.command("approve", "--target", "chapter_range", "--range-start", "2", "--range-end", "2")
        self.command("start-step", *args)
        self.command("approve", "--target", "chapter_range", "--range-start", "1", "--range-end", "1")
        with self.assertRaisesRegex(ValueError, "chapter_range"):
            self.command("finish-step", *args, "--measurement", "unavailable", "--reason", "runtime_usage_not_exposed")

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
        (self.workspace / "chapters/chapter-001/repair.md").write_text("作者修订后的结局。", encoding="utf-8")
        self.command("reconcile")
        self.step("chapter_review", "review.md", "accepted")
        state = ctl.read_state(self.workspace)
        self.assertEqual("stale", state["artifacts"]["chapter_001_delta"]["status"])
        self.step("continuity_update", "delta.md", content="登记作者修订的结局。")
        self.assertEqual("chapter_002_plan", ctl.read_state(self.workspace)["next_action"]["target"])

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
