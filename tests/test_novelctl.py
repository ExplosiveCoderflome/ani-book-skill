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
SCRIPT = ROOT / "scripts" / "novelctl.py"
sys.path.insert(0, str(ROOT / "scripts"))
import novelctl as control


class NovelCtlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.workspace = self.root / "novel"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_cli(self, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *arguments],
            check=check,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def init_workspace(self, mode: str = "milestone_approval", confirm_choices: bool = True) -> dict:
        self.run_cli("init", str(self.workspace), "--title", "测试小说", "--mode", mode)
        if confirm_choices:
            self.run_cli(
                "set-opening-choices",
                str(self.workspace),
                "--channel",
                "男频",
                "--publication-format",
                "免费连载",
                "--primary-reader-reward",
                "成长与反转",
            )
        return self.read_state()

    def read_state(self) -> dict:
        return yaml.safe_load((self.workspace / "novel-state.yaml").read_text(encoding="utf-8"))

    def write_state(self, state: dict) -> None:
        (self.workspace / "novel-state.yaml").write_text(
            yaml.safe_dump(state, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    @staticmethod
    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def attach_review_inputs(self, state: dict) -> None:
        for kind in ("plan", "context", "draft"):
            relative = f"chapters/chapter-001/{kind}.md"
            path = self.workspace / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# {kind}\n审校输入。", encoding="utf-8")
            state["artifacts"][f"chapter_001_{kind}"] = {"path": relative, "status": "ready", "sha256": self.digest(path),
                                                         "approval": "not_required", "depends_on": []}
        state["artifacts"]["chapter_001_review"]["review_inputs"] = control.review_snapshot(self.workspace, state, "chapter_001")

    def test_init_status_next_and_validate(self) -> None:
        state = self.init_workspace(confirm_choices=False)
        self.assertEqual(3, state["schema_version"])
        self.assertEqual("milestone_approval", state["director"]["mode"])
        self.assertTrue((self.workspace / "production/recovery.md").is_file())
        self.assertTrue((self.workspace / "production/token-usage.jsonl").is_file())

        next_result = json.loads(self.run_cli("next", str(self.workspace)).stdout)
        self.assertEqual("opening_choices", next_result["target"])
        blocked = self.run_cli(
            "start-step",
            str(self.workspace),
            "--step",
            "novel_brief",
            "--target",
            "novel_brief",
            "--artifact",
            "novel-brief.md",
            check=False,
        )
        self.assertNotEqual(0, blocked.returncode)
        self.run_cli(
            "set-opening-choices",
            str(self.workspace),
            "--channel",
            "男频",
            "--publication-format",
            "免费连载",
            "--primary-reader-reward",
            "成长与反转",
        )
        checked = json.loads(self.run_cli("validate", str(self.workspace)).stdout)
        self.assertTrue(checked["valid"])

    def prepare_fanfic_handoff(self) -> None:
        analysis = self.root / "analysis"
        analysis.mkdir()
        (analysis / "analysis-state.yaml").write_text(
            'source:\n  fingerprint: "sha256:TEST"\n', encoding="utf-8"
        )
        self.run_cli(
            "init", str(self.workspace), "--title", "测试同人", "--novel-mode", "fanfic",
            "--source-analysis", str(analysis), "--fanfic-mode", "new_story_with_canon",
            "--read-scope", "第1-3章", "--branch-chapter", "第3章",
        )
        state = self.read_state()
        self.assertEqual("fanfic_handoff", state["next_action"]["target"])
        self.assertNotIn("opening_choices", state)
        self.assertTrue(json.loads(self.run_cli("validate", str(self.workspace)).stdout)["valid"])
        blocked = self.run_cli(
            "start-step", str(self.workspace), "--step", "novel_brief",
            "--target", "novel_brief", "--artifact", "novel-brief.md", check=False,
        )
        self.assertNotEqual(0, blocked.returncode)
        self.run_cli(
            "start-step", str(self.workspace), "--step", "fanfic_handoff",
            "--target", "fanfic_handoff", "--artifact", "fanfic-handoff.md",
        )
        (self.workspace / "fanfic-handoff.md").write_text("# 同人交接\n已读范围：第1-3章\n", encoding="utf-8")
        self.run_cli(
            "finish-step", str(self.workspace), "--step", "fanfic_handoff",
            "--target", "fanfic_handoff", "--artifact", "fanfic-handoff.md",
            "--measurement", "unavailable", "--reason", "runtime_usage_not_exposed",
        )
        self.assertEqual("novel_brief", json.loads(self.run_cli("next", str(self.workspace)).stdout)["target"])
        plan = self.workspace / "chapters/chapter-001/plan.md"
        plan.parent.mkdir(parents=True, exist_ok=True)
        plan.write_text("# 本章计划\n承接交接。", encoding="utf-8")
        (self.workspace / "novel-brief.md").write_text("# 同人简报\n方向已确认。", encoding="utf-8")
        self.assertIn("fanfic-handoff.md", self.run_cli("context", str(self.workspace), "--chapter", "1").stdout)

    def test_fanfic_requires_handoff_before_novel_brief(self) -> None:
        self.prepare_fanfic_handoff()

    def test_finish_records_usage_before_ready_and_waits_for_approval(self) -> None:
        self.init_workspace()
        relative = "novel-brief.md"
        self.run_cli(
            "start-step",
            str(self.workspace),
            "--step",
            "novel_brief",
            "--target",
            "novel_brief",
            "--artifact",
            relative,
        )
        (self.workspace / relative).write_text("# 小说简报\n\n测试。\n", encoding="utf-8")
        self.run_cli(
            "finish-step",
            str(self.workspace),
            "--step",
            "novel_brief",
            "--target",
            "novel_brief",
            "--artifact",
            relative,
            "--measurement",
            "unavailable",
            "--reason",
            "runtime_usage_not_exposed",
        )
        state = self.read_state()
        self.assertEqual("ready", state["artifacts"]["novel_brief"]["status"])
        self.assertEqual("waiting_approval", state["director"]["status"])
        self.assertEqual(1, state["usage"]["unavailable_events"])
        self.assertEqual(1, len((self.workspace / "production/token-usage.jsonl").read_text(encoding="utf-8").splitlines()))

        self.run_cli("approve", str(self.workspace), "--target", "novel_brief")
        state = self.read_state()
        self.assertEqual("approved", state["artifacts"]["novel_brief"]["approval"])
        self.assertEqual("story_bible", state["next_action"]["target"])

    def test_missing_artifact_does_not_record_usage_or_finish(self) -> None:
        self.init_workspace()
        self.run_cli(
            "start-step",
            str(self.workspace),
            "--step",
            "novel_brief",
            "--target",
            "novel_brief",
            "--artifact",
            "novel-brief.md",
        )
        failed = self.run_cli(
            "finish-step",
            str(self.workspace),
            "--step",
            "novel_brief",
            "--target",
            "novel_brief",
            "--artifact",
            "novel-brief.md",
            "--measurement",
            "unavailable",
            "--reason",
            "runtime_usage_not_exposed",
            check=False,
        )
        self.assertEqual(2, failed.returncode)
        state = self.read_state()
        self.assertEqual("in_progress", state["artifacts"]["novel_brief"]["status"])
        self.assertEqual("", (self.workspace / "production/token-usage.jsonl").read_text(encoding="utf-8"))

    def test_migrate_v2_creates_backup_and_preserves_content(self) -> None:
        self.workspace.mkdir()
        prose = self.workspace / "novel-brief.md"
        prose.write_text("# 原简报\n", encoding="utf-8")
        state = {
            "schema_version": 2,
            "workspace": {"persistence_mode": "workspace"},
            "novel": {"title": "旧小说", "current_stage": "chapter_planning"},
            "artifacts": {
                "novel_brief": {
                    "path": "novel-brief.md",
                    "status": "ready",
                    "source": "user_edited",
                    "protected": True,
                }
            },
            "continuity": {"last_committed_chapter": None},
            "next_action": {"type": "plan_chapter", "target": "chapter_001"},
        }
        self.write_state(state)
        self.run_cli("migrate", str(self.workspace))
        migrated = self.read_state()
        self.assertEqual(3, migrated["schema_version"])
        self.assertEqual("legacy_migrated", migrated["opening_choices"]["status"])
        self.assertEqual(self.digest(prose), migrated["artifacts"]["novel_brief"]["sha256"])
        self.assertEqual("approved", migrated["artifacts"]["novel_brief"]["approval"])
        self.assertEqual("# 原简报\n", prose.read_text(encoding="utf-8"))
        self.assertEqual(1, len(list(self.workspace.glob("novel-state.yaml.bak.*"))))

    def test_validate_rejects_persisted_next_action_drift(self) -> None:
        state = self.init_workspace()
        state["next_action"] = {"type": "wrong", "target": "wrong", "reason": "wrong", "requires_approval": False}
        self.write_state(state)
        result = self.run_cli("validate", str(self.workspace), check=False)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("next_action drifted", result.stdout)

    def test_confirmed_opening_choices_cannot_have_empty_values(self) -> None:
        state = self.init_workspace()
        state["opening_choices"]["channel"] = ""
        state["next_action"] = {
            "type": "collect_opening_choices",
            "target": "opening_choices",
            "reason": "开书前需确认频道、发布形态和主要阅读回报",
            "requires_approval": True,
        }
        self.write_state(state)
        result = self.run_cli("validate", str(self.workspace), check=False)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("three non-empty values", result.stdout)

    def test_reconcile_protects_edit_and_stales_downstream(self) -> None:
        state = self.init_workspace(mode="auto")
        brief = self.workspace / "novel-brief.md"
        bible = self.workspace / "story-bible.md"
        brief.write_text("brief v1", encoding="utf-8")
        bible.write_text("bible v1", encoding="utf-8")
        state["artifacts"]["novel_brief"].update(
            {"status": "ready", "sha256": self.digest(brief), "approval": "delegated"}
        )
        state["artifacts"]["story_bible"].update(
            {"status": "ready", "sha256": self.digest(bible), "approval": "delegated"}
        )
        self.write_state(state)
        brief.write_text("brief user edit", encoding="utf-8")

        result = json.loads(self.run_cli("reconcile", str(self.workspace)).stdout)
        state = self.read_state()
        self.assertIn("novel_brief", result["changed"])
        self.assertTrue(state["artifacts"]["novel_brief"]["protected"])
        self.assertEqual("user_edited", state["artifacts"]["novel_brief"]["source"])
        self.assertEqual("stale", state["artifacts"]["story_bible"]["status"])
        self.assertEqual("brief user edit", brief.read_text(encoding="utf-8"))

    def test_protected_artifact_requires_explicit_overwrite_approval(self) -> None:
        state = self.init_workspace()
        brief = self.workspace / "novel-brief.md"
        brief.write_text("user brief", encoding="utf-8")
        state["artifacts"]["novel_brief"].update(
            {"status": "ready", "protected": True, "source": "user_edited", "sha256": self.digest(brief)}
        )
        self.write_state(state)
        failed = self.run_cli(
            "start-step",
            str(self.workspace),
            "--step",
            "novel_brief",
            "--target",
            "novel_brief",
            "--artifact",
            "novel-brief.md",
            check=False,
        )
        self.assertEqual(2, failed.returncode)
        self.run_cli("approve", str(self.workspace), "--target", "novel_brief", "--overwrite")
        self.run_cli(
            "start-step",
            str(self.workspace),
            "--step",
            "novel_brief",
            "--target",
            "novel_brief",
            "--artifact",
            "novel-brief.md",
        )
        self.assertEqual("in_progress", self.read_state()["artifacts"]["novel_brief"]["status"])

    def test_chapter_range_stops_after_continuity_commit(self) -> None:
        state = self.init_workspace(mode="auto")
        for key, artifact in state["artifacts"].items():
            path = self.workspace / artifact["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# {key}\n", encoding="utf-8")
            artifact.update(
                {
                    "status": "ready",
                    "approval": "delegated" if key in {"novel_brief", "story_bible", "volume_strategy"} else "not_required",
                    "sha256": self.digest(path),
                }
            )
        self.write_state(state)
        relative = "continuity/chapter-deltas/chapter-001.md"
        review_path = self.workspace / "chapters/chapter-001/review.md"
        review_path.parent.mkdir(parents=True, exist_ok=True)
        review_path.write_text("# 审校\n已验收。\n", encoding="utf-8")
        state["artifacts"]["chapter_001_review"] = {
            "path": "chapters/chapter-001/review.md", "status": "ready", "review_decision": "accepted",
            "sha256": self.digest(review_path), "approval": "not_required", "depends_on": [],
        }
        self.attach_review_inputs(state)
        self.write_state(state)
        self.run_cli(
            "start-step",
            str(self.workspace),
            "--step",
            "continuity_update",
            "--target",
            "chapter_001",
            "--artifact",
            relative,
            "--range-start",
            "1",
            "--range-end",
            "1",
        )
        path = self.workspace / relative
        path.write_text("# 第一章差分\n", encoding="utf-8")
        self.run_cli(
            "finish-step",
            str(self.workspace),
            "--step",
            "continuity_update",
            "--target",
            "chapter_001",
            "--artifact",
            relative,
            "--measurement",
            "unavailable",
            "--reason",
            "runtime_usage_not_exposed",
        )
        state = self.read_state()
        self.assertEqual("chapter_001", state["continuity"]["last_committed_chapter"])
        self.assertEqual("waiting_approval", state["director"]["status"])
        self.assertEqual("chapter_range", state["director"]["current_target"])
        self.assertEqual("request_chapter_range", state["next_action"]["type"])

        self.run_cli(
            "approve",
            str(self.workspace),
            "--target",
            "chapter_range",
            "--range-start",
            "2",
            "--range-end",
            "5",
        )
        state = self.read_state()
        self.assertEqual({"start": 2, "end": 5}, state["director"]["requested_range"])
        self.assertEqual("idle", state["director"]["status"])
        self.assertEqual("produce_artifact", state["next_action"]["type"])
        self.assertEqual("chapter_002_plan", state["next_action"]["target"])

    def test_next_walks_the_complete_chapter_chain_and_honors_review_decision(self) -> None:
        state = self.init_workspace(mode="auto")
        for key, artifact in state["artifacts"].items():
            path = self.workspace / artifact["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# {key}\n", encoding="utf-8")
            artifact.update({"status": "ready", "approval": "delegated", "sha256": self.digest(path)})
        self.write_state(state)

        steps = (
            ("chapter_plan", "chapters/chapter-001/plan.md", "chapter_001_plan"),
            ("context_package", "context-packages/chapter-001.md", "chapter_001_context"),
            ("chapter_draft", "chapters/chapter-001/draft.md", "chapter_001_draft"),
            ("humanization_revision", "chapters/chapter-001/humanized.md", "chapter_001_humanized"),
            ("chapter_review", "chapters/chapter-001/review.md", "chapter_001_review"),
        )
        for step, relative, expected_key in steps:
            next_result = self.run_cli("next", str(self.workspace))
            self.assertEqual(expected_key, json.loads(next_result.stdout)["target"])
            self.run_cli(
                "start-step",
                str(self.workspace),
                "--step",
                step,
                "--target",
                "chapter_001",
                "--artifact",
                relative,
            )
            path = self.workspace / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# {step}\n", encoding="utf-8")
            finish = [
                "finish-step",
                str(self.workspace),
                "--step",
                step,
                "--target",
                "chapter_001",
                "--artifact",
                relative,
                "--measurement",
                "unavailable",
                "--reason",
                "runtime_usage_not_exposed",
            ]
            if step == "chapter_review":
                finish.extend(["--review-decision", "accepted"])
            self.run_cli(*finish)

        state = self.read_state()
        self.assertEqual("chapter_001_delta", state["next_action"]["target"])

    def test_review_can_route_to_repair_or_global_replan(self) -> None:
        state = self.init_workspace(mode="auto")
        for suffix in ("plan", "context", "draft", "humanized"):
            state["artifacts"][f"chapter_001_{suffix}"] = {
                "path": f"chapters/chapter-001/{suffix}.md",
                "status": "ready",
                "source": "ai_generated",
                "protected": False,
                "depends_on": [],
                "sha256": "unused",
                "approval": "not_required",
                "updated_at": None,
            }
        state["artifacts"]["chapter_001_review"] = {
            "path": "chapters/chapter-001/review.md",
            "status": "ready",
            "source": "ai_generated",
            "protected": False,
            "depends_on": [],
            "sha256": "unused",
            "approval": "not_required",
            "review_decision": "repair_required",
            "updated_at": None,
        }
        for artifact in state["artifacts"].values():
            if artifact["status"] == "missing":
                artifact["status"] = "ready"
                artifact["approval"] = "delegated"
        self.write_state(state)
        result = self.run_cli("next", str(self.workspace))
        self.assertIn("chapter_001_repair", result.stdout)

    def test_quality_debt_does_not_stop_the_global_chain(self) -> None:
        state = self.init_workspace(mode="auto")
        state["continuity"]["quality_debt_open_count"] = 3
        self.write_state(state)
        result = self.run_cli("next", str(self.workspace))
        action = json.loads(result.stdout)
        self.assertEqual("produce_artifact", action["type"])
        self.assertEqual("novel_brief", action["target"])

    def test_block_step_becomes_the_unique_recovery_action(self) -> None:
        self.init_workspace()
        self.run_cli(
            "start-step",
            str(self.workspace),
            "--step",
            "novel_brief",
            "--target",
            "novel_brief",
            "--artifact",
            "novel-brief.md",
        )
        self.run_cli(
            "block-step",
            str(self.workspace),
            "--step",
            "novel_brief",
            "--target",
            "novel_brief",
            "--reason",
            "missing_hard_constraint",
        )
        state = self.read_state()
        self.assertEqual("blocked", state["director"]["status"])
        self.assertEqual("resolve_blocker", state["next_action"]["type"])
        self.assertEqual("novel_brief", state["next_action"]["target"])

    def test_replan_blocks_next_start_and_finish_until_review_accepts(self) -> None:
        state = self.init_workspace(mode="auto")
        path = self.workspace / "chapters/chapter-001/review.md"
        path.parent.mkdir(parents=True)
        path.write_text("# 审校\n结构性冲突。", encoding="utf-8")
        state["artifacts"]["chapter_001_review"] = {
            "path": "chapters/chapter-001/review.md", "status": "in_progress",
            "approval": "not_required", "depends_on": [],
        }
        self.attach_review_inputs(state)
        self.write_state(state)
        self.run_cli("finish-step", str(self.workspace), "--step", "chapter_review", "--target", "chapter_001",
                     "--artifact", "chapters/chapter-001/review.md", "--review-decision", "stop_for_replan",
                     "--measurement", "unavailable", "--reason", "runtime_usage_not_exposed")
        action = json.loads(self.run_cli("next", str(self.workspace)).stdout)
        self.assertEqual("resolve_blocker", action["type"])
        self.assertTrue(action["requires_approval"])
        before = (self.workspace / "novel-state.yaml").read_bytes()
        for command in ("start-step", "finish-step"):
            extra = ["--measurement", "unavailable", "--reason", "runtime_usage_not_exposed"] if command == "finish-step" else []
            result = self.run_cli(command, str(self.workspace), "--step", "continuity_update", "--target", "chapter_001",
                                  "--artifact", "continuity/chapter-deltas/chapter-001.md", *extra, check=False)
            self.assertIn("stop_for_replan", result.stderr)
        wrong = self.run_cli("approve", str(self.workspace), "--target", "novel_brief", check=False)
        self.assertNotEqual(0, wrong.returncode)
        self.assertEqual(before, (self.workspace / "novel-state.yaml").read_bytes())
        self.run_cli("approve", str(self.workspace), "--target", "chapter_001_review")
        still_blocked = self.run_cli("start-step", str(self.workspace), "--step", "continuity_update", "--target", "chapter_001",
                                    "--artifact", "continuity/chapter-deltas/chapter-001.md", check=False)
        self.assertIn("accepted chapter review", still_blocked.stderr)

    def test_style_edit_invalidates_future_context_and_review_preserving_accepted_prose(self) -> None:
        state = self.init_workspace(mode="auto")
        style = self.workspace / "writing-style.md"
        style.write_text("STYLE-01：对白保留分歧。", encoding="utf-8")
        self.run_cli("reconcile", str(self.workspace))
        state = self.read_state()
        self.assertIn("writing_style", state["artifacts"])
        state["continuity"]["last_committed_chapter"] = "chapter_001"
        for chapter in (1, 2):
            for kind in ("context", "draft", "review"):
                key = f"chapter_{chapter:03d}_{kind}"
                relative = f"chapters/chapter-{chapter:03d}/{kind}.md"
                path = self.workspace / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"稳定内容 {key}", encoding="utf-8")
                state["artifacts"][key] = {"path": relative, "status": "ready", "protected": chapter == 1,
                                          "approval": "not_required", "sha256": self.digest(path),
                                          "depends_on": [f"chapter_{chapter:03d}_context"] if kind == "draft" else []}
        self.write_state(state)
        stable = self.workspace / "chapters/chapter-001/draft.md"
        before = stable.read_bytes()
        style.write_text("STYLE-01：对白保留分歧。STYLE-02：取消旁白说教。", encoding="utf-8")
        result = self.run_cli("context", str(self.workspace), "--chapter", "2", check=False)
        self.assertIn("reconcile", result.stderr)
        self.run_cli("reconcile", str(self.workspace))
        after = self.read_state()
        self.assertEqual(before, stable.read_bytes())
        for kind in ("context", "draft", "review"):
            self.assertEqual("ready", after["artifacts"][f"chapter_001_{kind}"]["status"])
            self.assertEqual("stale", after["artifacts"][f"chapter_002_{kind}"]["status"])
        self.assertNotEqual("blocked", after["director"]["status"])

    def test_source_changes_block_fanfic_context_and_production(self) -> None:
        self.prepare_fanfic_handoff()
        source_path = self.root / "analysis/analysis-state.yaml"
        for source in ({"fingerprint": "sha256:NEW"}, {"fingerprint": "sha256:TEST", "scope": "第1-4章"}):
            source_path.write_text(yaml.safe_dump({"source": source}, allow_unicode=True), encoding="utf-8")
            for command in (("context", "--chapter", "1"), ("validate",),
                            ("start-step", "--step", "novel_brief", "--target", "novel_brief", "--artifact", "novel-brief.md")):
                result = self.run_cli(command[0], str(self.workspace), *command[1:], check=False)
                self.assertNotEqual(0, result.returncode)
                self.assertIn("analysis source changed", result.stdout + result.stderr)

    def test_recovery_refresh_preserves_notes_and_flags_confirmation_conflicts(self) -> None:
        state = self.init_workspace()
        recovery = self.workspace / "production/recovery.md"
        recovery.write_text(recovery.read_text(encoding="utf-8") + "\n作者备注：保留此前线索。\n", encoding="utf-8")
        brief = self.workspace / "novel-brief.md"
        brief.write_text("# 简报\n## 故事发动机（AI 推荐待确认）\n", encoding="utf-8")
        state["artifacts"]["novel_brief"].update({"status": "ready", "approval": "approved", "sha256": self.digest(brief)})
        self.write_state(state)
        result = self.run_cli("validate", str(self.workspace), check=False)
        self.assertIn("confirmation conflict", result.stdout)
        rejected = self.run_cli("approve", str(self.workspace), "--target", "novel_brief", check=False)
        self.assertIn("confirmation conflict", rejected.stderr)
        state["artifacts"]["story_bible"]["status"] = "in_progress"
        (self.workspace / "story-bible.md").write_text("# 故事圣经\n已生成候选。", encoding="utf-8")
        self.write_state(state)
        before = (self.workspace / "novel-state.yaml").read_bytes()
        finish = self.run_cli("finish-step", str(self.workspace), "--step", "story_bible", "--target", "story_bible",
                              "--artifact", "story-bible.md", "--measurement", "unavailable",
                              "--reason", "runtime_usage_not_exposed", check=False)
        self.assertIn("confirmation conflict", finish.stderr)
        self.assertEqual(before, (self.workspace / "novel-state.yaml").read_bytes())
        self.run_cli("reconcile", str(self.workspace))
        self.assertIn("作者备注：保留此前线索。", recovery.read_text(encoding="utf-8"))
        report = json.loads(self.run_cli("validate", str(self.workspace), check=False).stdout)
        self.assertFalse(any("recovery" in item for item in report["warnings"]))
        self.assertIn("待确认", brief.read_text(encoding="utf-8"))

    def test_incomplete_v3_can_be_repaired_with_backup_and_readonly_dry_run(self) -> None:
        self.init_workspace()
        state = self.read_state()
        state["director"] = {"mode": "auto"}
        state.pop("opening_choices")
        state.pop("next_action")
        for artifact in state["artifacts"].values():
            artifact.pop("approval")
        self.write_state(state)
        before = (self.workspace / "novel-state.yaml").read_bytes()
        self.run_cli("migrate", str(self.workspace), "--dry-run")
        self.assertEqual(before, (self.workspace / "novel-state.yaml").read_bytes())
        self.assertEqual([], list(self.workspace.glob("novel-state.yaml.bak.*")))
        self.run_cli("migrate", str(self.workspace))
        self.assertEqual("auto", self.read_state()["director"]["mode"])
        backups = list(self.workspace.glob("novel-state.yaml.bak.*"))
        self.assertEqual(before, backups[0].read_bytes())
        self.assertTrue(json.loads(self.run_cli("validate", str(self.workspace)).stdout)["valid"])

    def test_legacy_context_falls_back_to_selected_markdown(self) -> None:
        state = self.init_workspace(mode="auto")
        brief = self.workspace / "novel-brief.md"
        plan = self.workspace / "chapters/chapter-001/plan.md"
        style = self.workspace / "writing-style.md"
        brief.write_text("# 简报\n阅读承诺。\n", encoding="utf-8")
        plan.parent.mkdir(parents=True, exist_ok=True)
        plan.write_text("# 第一章计划\n必须发生。\n", encoding="utf-8")
        style.write_text("# 本书写法\nSTYLE-01：对白体现人物风险偏好。\n", encoding="utf-8")
        state["artifacts"]["novel_brief"].update(
            {"status": "ready", "approval": "delegated", "sha256": self.digest(brief)}
        )
        self.write_state(state)
        result = self.run_cli("context", str(self.workspace), "--chapter", "1")
        self.assertIn("第一章计划", result.stdout)
        self.assertIn("阅读承诺", result.stdout)
        self.assertIn("STYLE-01：对白体现人物风险偏好", result.stdout)

        too_long = "风" * 2201
        style.write_text(too_long, encoding="utf-8")
        rejected = self.run_cli("context", str(self.workspace), "--chapter", "1", check=False)
        self.assertNotEqual(0, rejected.returncode)
        self.assertIn("writing-style.md", rejected.stderr)


if __name__ == "__main__":
    unittest.main()
