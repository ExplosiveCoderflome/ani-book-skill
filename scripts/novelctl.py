#!/usr/bin/env python3
"""Deterministic controller for Codex-native novel workspaces."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml

import asset_graph
import analysis_reference
import continuity_store
import token_usage


SCHEMA_VERSION = 3
SUPPORTED_READ_VERSIONS = {1, 2, 3}
ARTIFACT_STATUSES = {"missing", "in_progress", "ready", "stale", "blocked"}
DIRECTOR_MODES = {"milestone_approval", "auto"}
DIRECTOR_STATUSES = {"idle", "running", "waiting_approval", "blocked", "completed"}
APPROVALS = {"required", "approved", "delegated", "not_required"}
MILESTONE_STEPS = {"novel_brief", "story_bible", "volume_strategy"}
CHAPTER_STEPS = {
    "chapter_plan",
    "context_package",
    "chapter_draft",
    "humanization_revision",
    "chapter_review",
    "chapter_repair",
    "continuity_update",
}
STEP_ORDER = {
    "fanfic_handoff": 5,
    "novel_brief": 10,
    "story_bible": 20,
    "world_bible": 30,
    "character_roster": 31,
    "volume_strategy": 40,
    "volume_skeleton": 50,
    "beat_sheet": 60,
    "chapter_plan": 70,
    "context_package": 80,
    "chapter_draft": 90,
    "humanization_revision": 100,
    "chapter_review": 110,
    "chapter_repair": 120,
    "continuity_update": 130,
}
CHAPTER_TARGET = re.compile(r"^chapter[_-](\d+)$")
SAFE_NAME = re.compile(r"^[a-z][a-z0-9_.-]{1,63}$")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def configure_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def safe_relative_path(value: str) -> str:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("artifact path must be workspace-relative and cannot contain '..'")
    normalized = path.as_posix().strip("/")
    if not normalized:
        raise ValueError("artifact path cannot be empty")
    return normalized


def state_path(workspace: Path) -> Path:
    return workspace / "novel-state.yaml"


def read_state(workspace: Path) -> dict[str, Any]:
    path = state_path(workspace)
    if not path.is_file():
        raise ValueError(f"missing state file: {path}")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("novel-state.yaml must contain a mapping")
    version = loaded.get("schema_version")
    if version not in SUPPORTED_READ_VERSIONS:
        raise ValueError(f"unsupported schema_version: {version}")
    return loaded


def require_v3(state: dict[str, Any]) -> None:
    if state.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("write operations require schema v3; run novelctl.py migrate first")


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def atomic_write_state(workspace: Path, state: dict[str, Any]) -> None:
    rendered = yaml.safe_dump(state, allow_unicode=True, sort_keys=False, width=120)
    atomic_write_text(state_path(workspace), rendered)
    refresh_recovery(workspace, state)


def recovery_snapshot(state: dict[str, Any]) -> str:
    artifacts = state.get("artifacts", {})
    director = state.get("director", {})
    action = decide_next(state)
    protected = [key for key, item in artifacts.items() if isinstance(item, dict) and item.get("protected")]
    stale = [key for key, item in artifacts.items() if isinstance(item, dict) and item.get("status") == "stale"]
    return "\n".join([
        "<!-- novelctl:recovery:start -->", "## 当前状态（由 novel-state.yaml 生成）", "",
        f"- 连续性已提交至：{state.get('continuity', {}).get('last_committed_chapter') or '无'}",
        f"- 当前步骤：{director.get('current_step') or '无'}",
        f"- 当前阻断：{director.get('stop_reason') or '无'}",
        f"- 受保护资产：{', '.join(protected) or '无'}",
        f"- stale 资产：{', '.join(stale) or '无'}",
        f"- 下一步：{action['type']} / {action['target']}；{action['reason']}",
        "<!-- novelctl:recovery:end -->",
    ])


def refresh_recovery(workspace: Path, state: dict[str, Any]) -> None:
    path = workspace / "production/recovery.md"
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    snapshot = recovery_snapshot(state)
    pattern = r"<!-- novelctl:recovery:start -->.*?<!-- novelctl:recovery:end -->"
    if re.search(pattern, existing, re.S):
        rendered = re.sub(pattern, lambda _: snapshot, existing, count=1, flags=re.S)
    else:
        template = Path(__file__).resolve().parents[1] / "assets/workspace-template/production/recovery.md"
        notes = "" if existing.strip() == template.read_text(encoding="utf-8").strip() else existing.strip()
        rendered = "# 生产恢复记录\n\n" + snapshot + "\n"
        if notes:
            rendered += "\n## 保留的人工记录（历史信息，以当前状态为准）\n\n" + notes + "\n"
    atomic_write_text(path, rendered)


def pending_confirmation(path: Path) -> bool:
    if not path.is_file():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if "待确认" in line and (line.startswith("#") or line.startswith("> 状态") or
                                  (line.startswith("|") and "待确认" in line.rstrip("|").split("|")[-1])):
            return True
    return False


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_location(workspace: Path, artifact: dict[str, Any]) -> Path:
    relative = safe_relative_path(str(artifact.get("path", "")))
    return workspace / relative


def chapter_number(value: str | None) -> int | None:
    if not value:
        return None
    match = CHAPTER_TARGET.fullmatch(value)
    return int(match.group(1)) if match else None


def chapter_target(number: int) -> str:
    return f"chapter_{number:03d}"


def artifact_key(step: str, target: str) -> str:
    if step in CHAPTER_STEPS:
        number = chapter_number(target)
        if number is None:
            raise ValueError(f"{step} requires target chapter_NNN")
        suffix = {
            "chapter_plan": "plan",
            "context_package": "context",
            "chapter_draft": "draft",
            "humanization_revision": "humanized",
            "chapter_review": "review",
            "chapter_repair": "repair",
            "continuity_update": "delta",
        }[step]
        return f"chapter_{number:03d}_{suffix}"
    return target if target else step


def step_from_key(key: str) -> str:
    if re.match(r"^chapter_\d+_plan$", key):
        return "chapter_plan"
    if re.match(r"^chapter_\d+_(context|context_package)$", key):
        return "context_package"
    if re.match(r"^chapter_\d+_draft$", key):
        return "chapter_draft"
    if re.match(r"^chapter_\d+_(humanized|humanized_draft)$", key):
        return "humanization_revision"
    if re.match(r"^chapter_\d+_review$", key):
        return "chapter_review"
    if re.match(r"^chapter_\d+_repair$", key):
        return "chapter_repair"
    if re.match(r"^chapter_\d+_delta$", key):
        return "continuity_update"
    if key.startswith("volume_") and key.endswith("_skeleton"):
        return "volume_skeleton"
    if key.startswith("volume_") and key.endswith("_beat_sheet"):
        return "beat_sheet"
    return key


def infer_dependencies(key: str, artifacts: dict[str, Any]) -> list[str]:
    direct: list[str] = []
    if key == "story_bible":
        direct = ["novel_brief"]
    elif key in {"world_bible", "character_roster", "character_profiles"}:
        direct = ["novel_brief", "story_bible"]
    elif key == "volume_strategy":
        direct = ["novel_brief", "story_bible", "world_bible", "character_roster"]
    elif re.fullmatch(r"volume_\d+_skeleton", key):
        direct = ["volume_strategy"]
    elif re.fullmatch(r"volume_\d+_beat_sheet", key):
        direct = [key.replace("_beat_sheet", "_skeleton")]
    else:
        match = re.fullmatch(r"chapter_(\d+)_(plan|context|context_package|draft|humanized|humanized_draft|review|repair|delta)", key)
        if match:
            number, kind = int(match[1]), match[2]
            prefix = f"chapter_{number:03d}"
            if kind == "plan":
                existing = artifacts.get(key, {})
                volume = existing.get("volume")
                windows = [item for item in existing.get("depends_on", []) if re.fullmatch(r"volume_\d+_beat_sheet", item)]
                if volume is not None:
                    direct = [f"volume_{int(volume):02d}_beat_sheet"]
                elif len(windows) == 1:
                    direct = windows
                else:
                    available = [item for item in artifacts if re.fullmatch(r"volume_\d+_beat_sheet", item)]
                    if len(available) > 1:
                        raise ValueError("chapter volume is ambiguous; supply --volume or an explicit beat-sheet dependency")
                    direct = available or ["volume_01_beat_sheet"]
            elif kind in {"context", "context_package"}:
                direct = [f"{prefix}_plan"]
            elif kind == "draft":
                direct = [f"{prefix}_plan", f"{prefix}_context"]
            elif kind in {"humanized", "humanized_draft"}:
                direct = [f"{prefix}_draft"]
            elif kind == "review":
                humanized = f"{prefix}_humanized"
                direct = [f"{prefix}_plan", f"{prefix}_context", humanized if humanized in artifacts else f"{prefix}_draft"]
            elif kind == "repair":
                direct = [f"{prefix}_review"]
            else:
                direct = [f"{prefix}_review"]
            if kind in {"context", "context_package", "review"} and "writing_style" in artifacts:
                direct.append("writing_style")
    return direct


def approval_for(step: str, mode: str, existing_ready: bool = False) -> str:
    if existing_ready:
        return "approved"
    if mode == "auto" and step in MILESTONE_STEPS:
        return "delegated"
    if step in MILESTONE_STEPS:
        return "required"
    return "not_required"


def initial_artifacts(mode: str, novel_mode: str = "original") -> dict[str, Any]:
    definitions = [
        ("novel_brief", "novel-brief.md", ["fanfic_handoff"] if novel_mode == "fanfic" else []),
        ("story_bible", "story-bible.md", ["novel_brief"]),
        ("world_bible", "world-bible.md", ["novel_brief", "story_bible"]),
        ("character_roster", "characters/character-roster.md", ["novel_brief", "story_bible"]),
        ("volume_strategy", "volumes/volume-strategy.md", ["novel_brief", "story_bible", "world_bible", "character_roster"]),
        ("volume_01_skeleton", "volumes/volume-01.md", ["volume_strategy"]),
        ("volume_01_beat_sheet", "volumes/volume-01-beat-sheet.md", ["volume_01_skeleton"]),
    ]
    if novel_mode == "fanfic":
        definitions.insert(0, ("fanfic_handoff", "fanfic-handoff.md", []))
    result: dict[str, Any] = {}
    for key, path, dependencies in definitions:
        step = step_from_key(key)
        result[key] = {
            "path": path,
            "status": "missing",
            "source": "ai_generated",
            "protected": False,
            "depends_on": dependencies,
            "sha256": None,
            "approval": approval_for(step, mode),
            "updated_at": None,
        }
    return result


def make_next(action_type: str, target: str, reason: str, requires_approval: bool = False) -> dict[str, Any]:
    return {
        "type": action_type,
        "target": target,
        "reason": reason,
        "requires_approval": requires_approval,
    }


def opening_choices_ready(state: dict[str, Any]) -> bool:
    choices = state.get("opening_choices")
    if not isinstance(choices, dict):
        return False
    if choices.get("status") == "legacy_migrated":
        return True
    return choices.get("status") in {"confirmed", "delegated"} and all(
        isinstance(choices.get(field), str) and choices[field].strip()
        for field in ("channel", "publication_format", "primary_reader_reward")
    )


def initial_state(title: str, mode: str, novel_mode: str = "original", source_analysis: dict[str, str] | None = None, fanfic_mode: str | None = None) -> dict[str, Any]:
    state = {
        "schema_version": SCHEMA_VERSION,
        "workspace": {"persistence_mode": "workspace", "promoted_from_preview": False},
        "novel": {"title": title, "mode": novel_mode, "current_stage": "fanfic_handoff" if novel_mode == "fanfic" else "novel_brief"},
        "opening_choices": {
            "status": "pending",
            "channel": None,
            "publication_format": None,
            "primary_reader_reward": None,
        },
        "director": {
            "mode": mode,
            "status": "idle",
            "run_id": None,
            "current_step": None,
            "current_target": None,
            "requested_range": None,
            "stop_reason": None,
        },
        "artifacts": initial_artifacts(mode, novel_mode),
        "continuity": {
            "baseline_chapter": None,
            "last_committed_chapter": None,
            "recovery_path": "production/recovery.md",
            "quality_debt_open_count": 0,
        },
        "usage": {
            "ledger_path": "production/token-usage.jsonl",
            "summary_path": "production/token-summary.json",
            "exact_tokens": 0,
            "estimated_tokens": 0,
            "unavailable_events": 0,
        },
        "next_action": make_next("collect_opening_choices", "opening_choices", "开书前需确认频道、发布形态和主要阅读回报", True),
    }
    if novel_mode == "fanfic":
        state["novel"]["fanfic_mode"] = fanfic_mode
        state["source_analysis"] = source_analysis
        state.pop("opening_choices")
        state["next_action"] = decide_next(state)
    return state


def ordered_artifacts(state: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    artifacts = state.get("artifacts", {})
    if not isinstance(artifacts, dict):
        return []
    return sorted(
        ((key, value) for key, value in artifacts.items() if isinstance(value, dict)),
        key=lambda item: (STEP_ORDER.get(step_from_key(item[0]), 999), item[0]),
    )


def next_chapter_action(state: dict[str, Any]) -> dict[str, Any]:
    artifacts = state.get("artifacts", {})
    last = state.get("continuity", {}).get("last_committed_chapter") if isinstance(state.get("continuity"), dict) else None
    number = (chapter_number(last) or 0) + 1
    requested = state.get("director", {}).get("requested_range") if isinstance(state.get("director"), dict) else None
    if isinstance(requested, dict):
        number = max(number, int(requested.get("start", number)))
    prefix = f"chapter_{number:03d}"
    chain = (
        (f"{prefix}_plan", "chapter_plan"),
        (f"{prefix}_context", "context_package"),
        (f"{prefix}_draft", "chapter_draft"),
        (f"{prefix}_humanized", "humanization_revision"),
        (f"{prefix}_review", "chapter_review"),
    )
    for key, step in chain:
        if key not in artifacts:
            return make_next("produce_artifact", key, f"第 {number} 章下一生产步骤：{step}")
    review = artifacts[f"{prefix}_review"]
    decision = review.get("review_decision")
    if decision == "repair_required" and f"{prefix}_repair" not in artifacts:
        return make_next("produce_artifact", f"{prefix}_repair", f"第 {number} 章审校要求修复")
    if decision == "repair_required":
        return make_next("review_repaired_chapter", f"{prefix}_review", f"第 {number} 章修复后需重新验收")
    if decision == "stop_for_replan":
        return make_next("resolve_blocker", f"{prefix}_review", f"第 {number} 章需要批准重规划并重新审校", True)
    if decision not in {"accepted", "repair_required"}:
        return make_next("record_review_decision", f"{prefix}_review", f"第 {number} 章审校尚未给出验收结论")
    if f"{prefix}_delta" not in artifacts:
        return make_next("produce_artifact", f"{prefix}_delta", f"第 {number} 章可提交连续性差分")
    return make_next("resume_step", f"{prefix}_delta", f"第 {number} 章连续性尚未完成提交")


def decide_next(state: dict[str, Any]) -> dict[str, Any]:
    director = state.get("director", {}) if isinstance(state.get("director"), dict) else {}
    if director.get("status") == "blocked":
        return make_next("resolve_blocker", str(director.get("current_target") or "director"),
                         str(director.get("stop_reason") or "流程阻断尚未解除"), True)
    if director.get("status") == "waiting_approval":
        current = str(director.get("current_target") or "milestone")
        if current == "chapter_range" and director.get("stop_reason") == "requested_range_completed":
            return make_next("request_chapter_range", current, "已完成授权章节范围，需要用户指定下一范围", True)
        return make_next("approve_milestone", current, "当前里程碑需要用户批准", True)
    if state.get("novel", {}).get("mode") != "fanfic" and not opening_choices_ready(state):
        return make_next("collect_opening_choices", "opening_choices", "开书前需确认频道、发布形态和主要阅读回报", True)
    for desired, action in (("in_progress", "resume_step"), ("blocked", "resolve_blocker"), ("stale", "refresh_artifact"), ("missing", "produce_artifact")):
        for key, artifact in ordered_artifacts(state):
            if artifact.get("status") == desired:
                return make_next(action, key, f"首个 {desired} 产物：{key}", desired == "blocked")
    return next_chapter_action(state)


def ensure_workspace_directories(workspace: Path) -> None:
    for relative in (
        "characters/profiles",
        "volumes",
        "chapters",
        "context-packages",
        "continuity/chapter-deltas",
        "production",
        "exports",
    ):
        (workspace / relative).mkdir(parents=True, exist_ok=True)


def command_init(args: argparse.Namespace) -> int:
    workspace = args.workspace.resolve()
    source_analysis = None
    if args.novel_mode == "fanfic":
        if not all((args.source_analysis, args.fanfic_mode, args.read_scope, args.branch_chapter)):
            raise ValueError("fanfic init requires --source-analysis, --fanfic-mode, --read-scope, and --branch-chapter")
        source_path = Path(args.source_analysis).resolve()
        source_state_path = source_path / "analysis-state.yaml"
        if not source_state_path.is_file():
            raise ValueError(f"missing analysis state: {source_state_path}")
        source_state = yaml.safe_load(source_state_path.read_text(encoding="utf-8"))
        source = source_state.get("source", {}) if isinstance(source_state, dict) else {}
        fingerprint = source.get("fingerprint") if isinstance(source, dict) else None
        if not isinstance(fingerprint, str) or not fingerprint.strip():
            raise ValueError("analysis source fingerprint is missing")
        source_analysis = {"path": str(source_path), "fingerprint": fingerprint, "read_scope": args.read_scope, "branch_chapter": args.branch_chapter,
                           "source_snapshot": analysis_snapshot(source_path, source_state)}
    if workspace.exists() and any(workspace.iterdir()):
        raise ValueError(f"workspace is not empty: {workspace}")
    workspace.mkdir(parents=True, exist_ok=True)
    ensure_workspace_directories(workspace)
    template = Path(__file__).resolve().parents[1] / "assets" / "workspace-template" / "production"
    for name in ("recovery.md", "quality-debt.md"):
        shutil.copy2(template / name, workspace / "production" / name)
    (workspace / "production" / "token-usage.jsonl").touch(exist_ok=True)
    atomic_write_state(workspace, initial_state(args.title, args.mode, args.novel_mode, source_analysis, args.fanfic_mode))
    print(json.dumps({"created": str(workspace), "schema_version": SCHEMA_VERSION, "mode": args.mode}, ensure_ascii=False, indent=2))
    return 0


def migrate_artifacts(workspace: Path, state: dict[str, Any], mode: str) -> dict[str, Any]:
    artifacts = state.setdefault("artifacts", {})
    if not isinstance(artifacts, dict):
        raise ValueError("artifacts must be a mapping")
    for key, value in list(artifacts.items()):
        if not isinstance(value, dict):
            raise ValueError(f"artifact {key} must be a mapping")
        step = step_from_key(key)
        path = artifact_location(workspace, value)
        ready = value.get("status") == "ready"
        value.setdefault("depends_on", infer_dependencies(key, artifacts))
        value.setdefault("sha256", file_sha256(path) if path.is_file() else None)
        value.setdefault("approval", approval_for(step, mode, existing_ready=ready))
        value.setdefault("updated_at", None)
    return state


def command_migrate(args: argparse.Namespace) -> int:
    workspace = args.workspace.resolve()
    state = read_state(workspace)
    director_defaults = {"mode": args.mode, "status": "idle", "run_id": None, "current_step": None,
                         "current_target": None, "requested_range": None, "stop_reason": None}
    complete_v3 = (isinstance(state.get("director"), dict) and director_defaults.keys() <= state["director"].keys()
                   and isinstance(state.get("next_action"), dict)
                   and (state.get("novel", {}).get("mode") == "fanfic" or isinstance(state.get("opening_choices"), dict))
                   and all(isinstance(item, dict) and "approval" in item for item in state.get("artifacts", {}).values()))
    if state.get("schema_version") == SCHEMA_VERSION and complete_v3:
        print(json.dumps({"migrated": False, "reason": "already_v3"}, ensure_ascii=False, indent=2))
        return 0
    original = state_path(workspace)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = original.with_name(f"novel-state.yaml.bak.{stamp}")
    if not args.dry_run:
        shutil.copy2(original, backup)
    mode = state.get("director", {}).get("mode", args.mode)
    state["schema_version"] = SCHEMA_VERSION
    state.setdefault("workspace", {"persistence_mode": "workspace", "promoted_from_preview": True})
    state.setdefault("novel", {"title": workspace.name, "mode": "original", "current_stage": "recovery"})
    director = state.setdefault("director", {})
    for key, value in director_defaults.items():
        director.setdefault(key, value)
    migrate_artifacts(workspace, state, mode)
    brief = state.get("artifacts", {}).get("novel_brief", {})
    state.setdefault(
        "opening_choices",
        {
            "status": "legacy_migrated" if isinstance(brief, dict) and brief.get("status") == "ready" else "pending",
            "channel": None,
            "publication_format": None,
            "primary_reader_reward": None,
        },
    )
    state.setdefault("continuity", {"baseline_chapter": None, "last_committed_chapter": None, "recovery_path": "production/recovery.md", "quality_debt_open_count": 0})
    state.setdefault("usage", {"ledger_path": "production/token-usage.jsonl", "summary_path": "production/token-summary.json", "exact_tokens": 0, "estimated_tokens": 0, "unavailable_events": 0})
    state["next_action"] = decide_next(state)
    if args.dry_run:
        print(yaml.safe_dump(state, allow_unicode=True, sort_keys=False, width=120), end="")
        return 0
    atomic_write_state(workspace, state)
    print(json.dumps({"migrated": True, "backup": str(backup), "schema_version": SCHEMA_VERSION}, ensure_ascii=False, indent=2))
    return 0


def validation_report(workspace: Path, state: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        validate_fanfic_source(state)
    except (ValueError, OSError, yaml.YAMLError) as exc:
        errors.append(str(exc))
    if state.get("schema_version") not in SUPPORTED_READ_VERSIONS:
        errors.append("unsupported schema_version")
    if state.get("schema_version") == SCHEMA_VERSION:
        if state.get("novel", {}).get("mode") == "fanfic":
            source = state.get("source_analysis")
            if state.get("novel", {}).get("fanfic_mode") not in {"continue_from_breakpoint", "new_story_with_canon"}:
                errors.append("fanfic_mode is invalid")
            if not isinstance(source, dict) or not all(isinstance(source.get(key), str) and source[key].strip() for key in ("path", "fingerprint", "read_scope", "branch_chapter")):
                errors.append("source_analysis requires path, fingerprint, read_scope, and branch_chapter")
            if not isinstance(state.get("artifacts"), dict) or "fanfic_handoff" not in state["artifacts"]:
                errors.append("fanfic_handoff artifact is missing")
        else:
            choices = state.get("opening_choices")
            if not isinstance(choices, dict) or choices.get("status") not in {"pending", "confirmed", "delegated", "legacy_migrated"}:
                errors.append("opening_choices has invalid or missing status")
            elif choices.get("status") in {"confirmed", "delegated"} and not opening_choices_ready(state):
                errors.append("confirmed opening_choices requires three non-empty values")
    artifacts = state.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append("artifacts must be a mapping")
        return errors, warnings
    for key, artifact in artifacts.items():
        if not isinstance(artifact, dict):
            errors.append(f"artifact {key} must be a mapping")
            continue
        status = artifact.get("status")
        if status not in ARTIFACT_STATUSES:
            errors.append(f"artifact {key} has invalid status: {status}")
        try:
            path = artifact_location(workspace, artifact)
        except ValueError as exc:
            errors.append(f"artifact {key}: {exc}")
            continue
        if status == "ready" and not path.exists():
            errors.append(f"ready artifact is missing: {key} -> {path}")
        recorded = artifact.get("sha256")
        if recorded and path.is_file() and file_sha256(path) != recorded:
            errors.append(f"artifact content changed; run reconcile: {key}")
        for dependency in artifact.get("depends_on", []) or []:
            if dependency not in artifacts:
                errors.append(f"artifact {key} has unknown dependency: {dependency}")
            elif status == "ready" and artifacts[dependency].get("status") != "ready":
                warnings.append(f"ready artifact {key} depends on non-ready {dependency}")
        approval = artifact.get("approval")
        if step_from_key(key) == "chapter_review" and status == "ready" and artifact.get("review_decision") == "accepted":
            try:
                target = chapter_target(int(re.fullmatch(r"chapter_(\d+)_review", key)[1]))
                if artifact.get("review_inputs") != review_snapshot(workspace, state, target):
                    errors.append(f"accepted review version is missing or outdated: {key}; review again")
            except (ValueError, OSError) as exc:
                errors.append(f"accepted review input invalid: {key}: {exc}")
        if status == "ready" and approval in {"approved", "delegated"} and step_from_key(key) in MILESTONE_STEPS and pending_confirmation(path):
            errors.append(f"confirmation conflict: {key} is approved but its document still has pending choices")
        if state.get("schema_version") == 3 and approval not in APPROVALS:
            errors.append(f"artifact {key} has invalid approval: {approval}")
    if state.get("schema_version") == SCHEMA_VERSION and state.get("next_action") != decide_next(state):
        errors.append("persisted next_action drifted from deterministic next action")
    if state.get("schema_version") == 3:
        director = state.get("director")
        if not isinstance(director, dict):
            errors.append("director must be a mapping")
        else:
            if director.get("mode") not in DIRECTOR_MODES:
                errors.append("director.mode is invalid")
            if director.get("status") not in DIRECTOR_STATUSES:
                errors.append("director.status is invalid")
        action = state.get("next_action")
        if not isinstance(action, dict) or not all(field in action for field in ("type", "target", "reason", "requires_approval")):
            errors.append("next_action must contain type, target, reason, and requires_approval")
    recovery = workspace / "production/recovery.md"
    if not recovery.is_file() or recovery_snapshot(state) not in recovery.read_text(encoding="utf-8"):
        warnings.append("recovery snapshot is missing or outdated; run reconcile")
    style = workspace / "writing-style.md"
    if style.is_file() and "writing_style" not in artifacts:
        warnings.append("writing-style.md is not tracked; run reconcile before chapter production")
    return errors, warnings


def command_validate(args: argparse.Namespace) -> int:
    workspace = args.workspace.resolve()
    state = read_state(workspace)
    errors, warnings = validation_report(workspace, state)
    result = {"valid": not errors, "schema_version": state.get("schema_version"), "errors": errors, "warnings": warnings}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


def command_status(args: argparse.Namespace) -> int:
    workspace = args.workspace.resolve()
    state = read_state(workspace)
    artifacts = state.get("artifacts", {})
    counts = {status: 0 for status in ARTIFACT_STATUSES}
    protected: list[str] = []
    for key, artifact in artifacts.items():
        if isinstance(artifact, dict):
            counts[artifact.get("status")] = counts.get(artifact.get("status"), 0) + 1
            if artifact.get("protected"):
                protected.append(key)
    cross_book_assets: dict[str, int] = {}
    if (workspace / "continuity" / "data").is_dir():
        try:
            links = continuity_store.load_store(workspace).get("asset_links", [])
            for link in links:
                if isinstance(link, dict):
                    status = str(link.get("status", "unknown"))
                    cross_book_assets[status] = cross_book_assets.get(status, 0) + 1
        except ValueError:
            cross_book_assets["invalid"] = 1
    result = {
        "title": state.get("novel", {}).get("title"),
        "schema_version": state.get("schema_version"),
        "director": state.get("director"),
        "artifact_counts": counts,
        "protected_artifacts": sorted(protected),
        "continuity": state.get("continuity"),
        "cross_book_assets": cross_book_assets,
        "usage": state.get("usage"),
        "next_action": decide_next(state),
    }
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"# {result['title']}\n")
        print(f"- Schema：{result['schema_version']}")
        print(f"- 导演状态：{(result['director'] or {}).get('status', 'legacy')}")
        print(f"- 最后连续性章节：{(result['continuity'] or {}).get('last_committed_chapter') or '无'}")
        print(f"- 跨书资产：{result['cross_book_assets'] or '无'}")
        print(f"- 受保护产物：{len(protected)}")
        print(f"- 下一步：{result['next_action']['type']} / {result['next_action']['target']}")
        print(f"- 原因：{result['next_action']['reason']}")
    return 0


def command_next(args: argparse.Namespace) -> int:
    state = read_state(args.workspace.resolve())
    action = decide_next(state)
    print(json.dumps(action, ensure_ascii=False, indent=2))
    return 0


def reverse_dependencies(artifacts: dict[str, Any]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {key: set() for key in artifacts}
    for key, artifact in artifacts.items():
        if isinstance(artifact, dict):
            for dependency in artifact.get("depends_on", []) or []:
                result.setdefault(dependency, set()).add(key)
    return result


def descendants(start: str, graph: dict[str, set[str]]) -> set[str]:
    seen: set[str] = set()
    pending = list(graph.get(start, set()))
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        pending.extend(graph.get(current, set()))
    return seen


def command_reconcile(args: argparse.Namespace) -> int:
    workspace = args.workspace.resolve()
    state = read_state(workspace)
    require_v3(state)
    artifacts = state["artifacts"]
    changed: list[str] = []
    stale: list[str] = []
    protected_conflicts: list[str] = []
    style = workspace / "writing-style.md"
    if style.is_symlink():
        raise ValueError("writing-style.md must be a local book snapshot")
    if style.is_file() and "writing_style" not in artifacts:
        artifacts["writing_style"] = {"path": "writing-style.md", "status": "ready", "source": "user_edited",
                                      "protected": True, "depends_on": [], "sha256": None,
                                      "approval": "not_required", "updated_at": now_utc()}
    last = chapter_number(state.get("continuity", {}).get("last_committed_chapter")) or 0
    accepted = {int(match[1]) for key, item in artifacts.items()
                if (match := re.match(r"^chapter_(\d+)_review$", key))
                and item.get("status") == "ready" and item.get("review_decision") == "accepted"}
    if "writing_style" in artifacts:
        for key, artifact in artifacts.items():
            match = re.match(r"^chapter_(\d+)_(context|context_package|review)$", key)
            if match and int(match[1]) > last and int(match[1]) not in accepted:
                artifact["depends_on"] = list(dict.fromkeys([*(artifact.get("depends_on") or []), "writing_style"]))
    graph = reverse_dependencies(artifacts)
    for key, artifact in artifacts.items():
        path = artifact_location(workspace, artifact)
        recorded = artifact.get("sha256")
        if (recorded or key == "writing_style"):
            current = file_sha256(path) if path.is_file() else None
            if current != recorded:
                artifact.update({"sha256": current, "source": "user_edited", "protected": True, "updated_at": now_utc()})
                if current is None:
                    artifact["status"] = "missing"
                elif key == "writing_style":
                    artifact["status"] = "ready"
                changed.append(key)
                for dependent in descendants(key, graph):
                    candidate = artifacts[dependent]
                    match = re.match(r"^chapter_(\d+)_", dependent)
                    if key == "writing_style" and match and (int(match[1]) <= last or int(match[1]) in accepted):
                        continue
                    if candidate.get("protected"):
                        protected_conflicts.append(dependent)
                    elif candidate.get("status") in {"ready", "in_progress"}:
                        candidate["status"] = "stale"
                        stale.append(dependent)
    if protected_conflicts:
        state["director"].update({"status": "blocked", "stop_reason": "protected_dependency_conflict"})
    state["next_action"] = decide_next(state)
    atomic_write_state(workspace, state)
    print(json.dumps({"changed": changed, "stale": sorted(set(stale)), "protected_conflicts": sorted(set(protected_conflicts)), "next_action": state["next_action"]}, ensure_ascii=False, indent=2))
    return 0


def dependency_list(args: argparse.Namespace, key: str, artifacts: dict[str, Any]) -> list[str]:
    supplied = list(dict.fromkeys(args.depends_on or []))
    if args.step == "chapter_plan":
        volume = getattr(args, "volume", None)
        windows = [item for item in supplied if re.fullmatch(r"volume_\d+_beat_sheet", item)]
        if volume is not None:
            if volume < 1:
                raise ValueError("--volume must be positive")
            window = f"volume_{volume:02d}_beat_sheet"
            if windows and windows != [window]:
                raise ValueError("--volume conflicts with explicit beat-sheet dependency")
            return list(dict.fromkeys([window, *supplied]))
        if len(windows) == 1:
            return supplied
        if len(windows) > 1:
            raise ValueError("a chapter plan must select one volume beat sheet")
    return list(dict.fromkeys([*infer_dependencies(key, artifacts), *supplied]))


def ensure_dependencies_ready(artifacts: dict[str, Any], dependencies: Iterable[str], workspace: Path | None = None) -> None:
    for dependency in dependencies:
        artifact = artifacts.get(dependency)
        if not isinstance(artifact, dict) or artifact.get("status") != "ready":
            raise ValueError(f"dependency is not ready: {dependency}")
        if artifact.get("approval") == "required":
            raise ValueError(f"dependency awaits milestone approval: {dependency}")
        if workspace is not None:
            path = artifact_location(workspace, artifact)
            if not path.is_file() or not artifact.get("sha256") or file_sha256(path) != artifact["sha256"]:
                raise ValueError(f"dependency file missing or changed; reconcile first: {dependency}")


def validate_chapter_progress(state: dict[str, Any], target: str, step: str) -> None:
    number = chapter_number(target)
    if number is None:
        return
    last = chapter_number(state.get("continuity", {}).get("last_committed_chapter")) or 0
    if number > last + 1 or (step == "continuity_update" and number != last + 1):
        raise ValueError(f"chapter sequence requires chapter_{last + 1:03d}; previous continuity is not committed")


def review_snapshot(workspace: Path, state: dict[str, Any], target: str) -> dict[str, dict[str, str]]:
    number = chapter_number(target)
    prefix = f"chapter_{number:03d}"
    artifacts = state["artifacts"]
    prose = next((f"{prefix}_{kind}" for kind in ("repair", "humanized", "draft")
                  if artifacts.get(f"{prefix}_{kind}", {}).get("status") == "ready"), None)
    if prose is None:
        raise ValueError("review requires ready prose")
    keys = [f"{prefix}_plan", f"{prefix}_context", prose]
    if "writing_style" in artifacts:
        keys.append("writing_style")
    ensure_dependencies_ready(artifacts, keys)
    snapshot = {}
    for key in keys:
        item = artifacts[key]
        path = artifact_location(workspace, item)
        if not path.is_file() or not item.get("sha256") or file_sha256(path) != item["sha256"]:
            raise ValueError(f"review input changed or fingerprint missing; reconcile first: {key}")
        snapshot[key] = {"path": item["path"], "sha256": item["sha256"]}
    return snapshot


def invalidate_dependents(state: dict[str, Any], key: str, keep: Iterable[str] = ()) -> list[str]:
    artifacts = state["artifacts"]
    stale = []
    for dependent in descendants(key, reverse_dependencies(artifacts)):
        if dependent in keep:
            continue
        item = artifacts[dependent]
        if item.get("status") in {"ready", "in_progress"} and not item.get("protected"):
            item["status"] = "stale"
            item.pop("review_decision", None)
            stale.append(dependent)
    # Review can consume a repaired candidate without a cyclic dependency edge.
    match = re.fullmatch(r"chapter_(\d+)_repair", key)
    if match:
        review = artifacts.get(f"chapter_{int(match[1]):03d}_review")
        if review:
            review["status"] = "stale"
            review.pop("review_decision", None)
    return stale


def validate_confirmation_labels(workspace: Path, artifacts: dict[str, Any], keys: Iterable[str]) -> None:
    pending = list(keys)
    visited: set[str] = set()
    while pending:
        key = pending.pop()
        if key in visited:
            continue
        visited.add(key)
        artifact = artifacts.get(key, {})
        if step_from_key(key) in MILESTONE_STEPS and artifact.get("approval") in {"approved", "delegated"}:
            if pending_confirmation(artifact_location(workspace, artifact)):
                raise ValueError(f"confirmation conflict: dependency {key} still has pending choices")
        pending.extend(artifact.get("depends_on") or [])


def analysis_snapshot(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    source = state.get("source", {})
    snapshot = {key: source.get(key) for key in ("fingerprint", "scope", "coverage")}
    paths = {name for name in ("analysis-lens.md", "overview.md", "coverage-map.md") if (root / name).is_file()}
    paths.update(path.relative_to(root).as_posix() for path in (root / "notes").glob("*.md"))
    artifacts = state.get("artifacts", {})
    if not isinstance(artifacts, dict):
        raise ValueError("analysis artifacts must be a mapping")
    registered = {}
    for item in artifacts.values():
        if isinstance(item, dict) and isinstance(item.get("path"), str):
            relative = item["path"]
            if Path(relative).suffix == ".md" and relative.split("/")[0] not in {"source", "retrieval"}:
                paths.add(relative)
                registered[relative] = item.get("status")
    snapshot["analysis_inputs"] = {}
    for relative in sorted(paths):
        path = root / safe_relative_path(relative)
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("analysis input escapes workspace")
        if registered.get(relative) == "ready" and not path.is_file():
            raise ValueError(f"ready analysis input is missing: {relative}")
        snapshot["analysis_inputs"][relative] = {"sha256": file_sha256(analysis_reference.local_file(root, relative)) if path.is_file() else None,
                                                  "status": registered.get(relative, "unregistered")}
    return snapshot


def validate_fanfic_source(state: dict[str, Any], refresh: bool = False) -> None:
    if state.get("novel", {}).get("mode") != "fanfic":
        return
    binding = state.get("source_analysis")
    if not isinstance(binding, dict) or not binding.get("path"):
        raise ValueError("source_analysis path is missing")
    source_state = yaml.safe_load((Path(binding["path"]) / "analysis-state.yaml").read_text(encoding="utf-8"))
    source = source_state.get("source", {}) if isinstance(source_state, dict) else {}
    if not isinstance(source, dict) or not source.get("fingerprint"):
        raise ValueError("analysis source fingerprint is missing")
    snapshot = analysis_snapshot(Path(binding["path"]), source_state)
    if refresh:
        binding.update({"fingerprint": source["fingerprint"], "source_snapshot": snapshot})
    elif binding.get("source_snapshot") != snapshot:
        raise ValueError("analysis source changed or snapshot missing; rebuild fanfic_handoff and confirm its scope")
    lens = source_state.get("analysis_lens")
    if isinstance(lens, dict) and lens.get("status") != "ready":
        raise ValueError("analysis lens is not ready; confirm before fanfic production")


def validate_continuity_preflight(workspace: Path, state: dict[str, Any], target: str) -> None:
    review_key = artifact_key("chapter_review", target)
    review = state.get("artifacts", {}).get(review_key, {})
    if review.get("status") != "ready" or review.get("review_decision") != "accepted":
        raise ValueError("continuity_update requires an accepted chapter review, including after repair or replan")
    if review.get("review_inputs") != review_snapshot(workspace, state, target):
        raise ValueError("accepted review does not match current prose or contract; review again")
    if state.get("director", {}).get("status") == "blocked":
        raise ValueError("resolve the director blocker before continuity_update")


def validate_style_preflight(workspace: Path, state: dict[str, Any], require_registered: bool = False) -> None:
    style = state.get("artifacts", {}).get("writing_style")
    if require_registered and not style and (workspace / "writing-style.md").exists():
        raise ValueError("writing-style.md is not tracked; run reconcile before production")
    if style:
        path = workspace / "writing-style.md"
        if not path.is_file() or style.get("status") != "ready" or file_sha256(path) != style.get("sha256"):
            raise ValueError("writing-style.md changed or is missing; run reconcile before production")


def validate_chapter_asset_preflight(workspace: Path, target: str) -> None:
    number = chapter_number(target)
    if number is None:
        return
    selection = asset_graph.default_selection_path(workspace, number)
    if selection.is_file():
        asset_graph.validate_asset_selection(workspace, selection)


def validate_chapter_reference_preflight(workspace: Path, target: str) -> None:
    number = chapter_number(target)
    if number is not None:
        selection = analysis_reference.selection_path(workspace, number)
        if selection.exists() or selection.is_symlink():
            analysis_reference.render_context(workspace, number)


def command_start_step(args: argparse.Namespace) -> int:
    workspace = args.workspace.resolve()
    state = read_state(workspace)
    require_v3(state)
    if state.get("director", {}).get("stop_reason") == "stop_for_replan":
        raise ValueError("stop_for_replan requires approval of the blocked review before restarting")
    if args.step in CHAPTER_STEPS:
        validate_style_preflight(workspace, state, require_registered=True)
    if args.step == "continuity_update":
        validate_continuity_preflight(workspace, state, args.target)
    if args.step != "fanfic_handoff":
        validate_fanfic_source(state)
    if not SAFE_NAME.fullmatch(args.step):
        raise ValueError("step has invalid format")
    if args.step in {"context_package", "chapter_draft", "chapter_review"}:
        validate_chapter_asset_preflight(workspace, args.target)
    if args.step in CHAPTER_STEPS - {"continuity_update"}:
        validate_chapter_reference_preflight(workspace, args.target)
    if args.step == "novel_brief" and state.get("novel", {}).get("mode") != "fanfic" and not opening_choices_ready(state):
        raise ValueError("confirm channel, publication format, and primary reader reward before novel_brief")
    if state.get("novel", {}).get("mode") == "fanfic" and (args.step == "novel_brief" or args.step in CHAPTER_STEPS):
        if state.get("artifacts", {}).get("fanfic_handoff", {}).get("status") != "ready":
            raise ValueError("fanfic_handoff must be ready before novel brief or chapter production")
    key = artifact_key(args.step, args.target)
    if args.step in CHAPTER_STEPS:
        validate_chapter_progress(state, args.target, args.step)
    artifacts = state["artifacts"]
    existing = artifacts.get(key)
    accepted_source = False
    if args.step in {"chapter_draft", "humanization_revision", "chapter_repair"}:
        prior_review = artifacts.get(artifact_key("chapter_review", args.target), {})
        if prior_review.get("review_decision") == "accepted":
            bound = prior_review.get("review_inputs", {})
            accepted_source = key in bound or not bound
    if isinstance(existing, dict) and (existing.get("protected") or accepted_source) and not existing.get("overwrite_approved"):
        raise ValueError(f"artifact is protected; approve overwrite first: {key}")
    dependencies = dependency_list(args, key, artifacts)
    ensure_dependencies_ready(artifacts, dependencies, workspace)
    validate_confirmation_labels(workspace, artifacts, dependencies)
    relative = safe_relative_path(args.artifact)
    run_id = args.run_id or str(uuid.uuid4())
    entry = existing if isinstance(existing, dict) else {}
    if args.step == "chapter_review":
        entry["review_inputs"] = review_snapshot(workspace, state, args.target)
    if args.step == "chapter_plan":
        window = next(item for item in dependencies if re.fullmatch(r"volume_\d+_beat_sheet", item))
        entry["volume"] = int(window.split("_")[1])
    if existing and (existing.get("protected") or accepted_source) and existing.get("overwrite_approved"):
        old_path = artifact_location(workspace, existing)
        if old_path.is_file():
            backup = workspace / "production/revisions" / key / (file_sha256(old_path) + old_path.suffix)
            backup.parent.mkdir(parents=True, exist_ok=True)
            if not backup.exists():
                shutil.copy2(old_path, backup)
    if args.step == "chapter_repair":
        attempts = int(entry.get("repair_attempts", 0)) + 1
        if attempts > 2:
            raise ValueError("chapter repair limit reached; record quality debt or stop for replan")
        entry["repair_attempts"] = attempts
        entry["repair_scope"] = args.repair_scope or ("local" if attempts == 1 else "chapter")
    entry.update({
        "path": relative,
        "status": "in_progress",
        "source": "ai_generated",
        "protected": False,
        "depends_on": dependencies,
        "sha256": entry.get("sha256"),
        "approval": approval_for(args.step, state["director"]["mode"]),
        "updated_at": now_utc(),
    })
    entry.pop("overwrite_approved", None)
    artifacts[key] = entry
    requested = state["director"].get("requested_range")
    if args.range_start is not None or args.range_end is not None:
        if args.range_start is None or args.range_end is None or args.range_start > args.range_end:
            raise ValueError("chapter range requires valid --range-start and --range-end")
        requested = {"start": args.range_start, "end": args.range_end}
    state["director"].update({"status": "running", "run_id": run_id, "current_step": args.step, "current_target": args.target, "requested_range": requested, "stop_reason": None})
    state["novel"]["current_stage"] = args.step
    state["next_action"] = decide_next(state)
    atomic_write_state(workspace, state)
    print(json.dumps({"started": key, "run_id": run_id, "artifact": relative}, ensure_ascii=False, indent=2))
    return 0


def command_set_opening_choices(args: argparse.Namespace) -> int:
    workspace = args.workspace.resolve()
    state = read_state(workspace)
    require_v3(state)
    state["opening_choices"] = {
        "status": "delegated" if args.delegated else "confirmed",
        "channel": args.channel.strip(),
        "publication_format": args.publication_format.strip(),
        "primary_reader_reward": args.primary_reader_reward.strip(),
    }
    if not all(state["opening_choices"][field] for field in ("channel", "publication_format", "primary_reader_reward")):
        raise ValueError("all three opening choices must be non-empty")
    state["next_action"] = decide_next(state)
    atomic_write_state(workspace, state)
    print(json.dumps({"opening_choices": state["opening_choices"], "next_action": state["next_action"]}, ensure_ascii=False, indent=2))
    return 0


def refresh_usage_projection(workspace: Path, state: dict[str, Any]) -> None:
    records, errors = token_usage.read_records(workspace)
    if errors:
        raise ValueError("token ledger invalid after record: " + "; ".join(errors))
    summary = token_usage.build_summary(records)
    token_usage.atomic_write_json(workspace / "production" / "token-summary.json", summary)
    totals = summary["totals"]
    state["usage"] = {
        "ledger_path": "production/token-usage.jsonl",
        "summary_path": "production/token-summary.json",
        "exact_tokens": totals["exact_tokens"],
        "estimated_tokens": totals["estimated_tokens"],
        "unavailable_events": totals["unavailable_events"],
    }


def record_usage(args: argparse.Namespace, workspace: Path, run_id: str | None) -> None:
    token_args = argparse.Namespace(
        workspace=workspace,
        route="novel",
        step=args.step,
        status="succeeded" if args.status == "ready" else "partial",
        measurement=args.measurement,
        provider=args.provider,
        model=args.model,
        run_id=run_id,
        request_id=args.request_id,
        artifact=args.artifact,
        reason=args.reason,
        input_tokens=args.input_tokens,
        cached_input_tokens=args.cached_input_tokens,
        output_tokens=args.output_tokens,
        reasoning_tokens=args.reasoning_tokens,
        total_tokens=args.total_tokens,
    )
    token_usage.command_record(token_args)


def command_finish_step(args: argparse.Namespace) -> int:
    workspace = args.workspace.resolve()
    state = read_state(workspace)
    require_v3(state)
    if state.get("director", {}).get("stop_reason") == "stop_for_replan":
        raise ValueError("stop_for_replan requires approval before finishing production")
    if args.step in CHAPTER_STEPS:
        validate_style_preflight(workspace, state, require_registered=True)
    if args.step == "continuity_update":
        validate_continuity_preflight(workspace, state, args.target)
    validate_fanfic_source(state, refresh=args.step == "fanfic_handoff")
    if args.status == "ready" and args.step in CHAPTER_STEPS - {"continuity_update"}:
        validate_chapter_reference_preflight(workspace, args.target)
    key = artifact_key(args.step, args.target)
    artifact = state["artifacts"].get(key)
    if not isinstance(artifact, dict) or artifact.get("status") != "in_progress":
        raise ValueError(f"step is not in progress: {key}")
    if args.step in CHAPTER_STEPS:
        validate_chapter_progress(state, args.target, args.step)
    ensure_dependencies_ready(state["artifacts"], artifact.get("depends_on") or [], workspace)
    validate_confirmation_labels(workspace, state["artifacts"], artifact.get("depends_on") or [])
    relative = safe_relative_path(args.artifact)
    if artifact.get("path") != relative:
        raise ValueError("artifact path differs from start-step")
    path = workspace / relative
    if args.status == "ready" and (not path.is_file() or path.stat().st_size == 0):
        raise ValueError(f"usable artifact is missing or empty: {path}")
    if args.step == "chapter_review" and args.status == "ready" and args.review_decision is None:
        raise ValueError("chapter_review requires --review-decision")
    if args.step == "chapter_review" and args.status == "ready" and artifact.get("review_inputs") != review_snapshot(workspace, state, args.target):
        raise ValueError("review inputs changed during review; restart review")
    if args.status == "ready" and args.step in MILESTONE_STEPS and artifact.get("approval") in {"approved", "delegated"} and pending_confirmation(path):
        raise ValueError("confirmation conflict: resolve document pending choices before marking approved work ready")
    run_id = state["director"].get("run_id")
    record_usage(args, workspace, run_id)
    current_sha = file_sha256(path) if path.is_file() else None
    if artifact.get("sha256") != current_sha:
        invalidate_dependents(state, key, artifact.get("review_inputs", {}) if args.step == "chapter_review" else ())
    artifact.update({"status": args.status, "sha256": current_sha, "updated_at": now_utc()})
    if args.step == "chapter_review" and args.review_decision is not None:
        artifact["review_decision"] = args.review_decision
        if args.status == "ready" and args.review_decision == "accepted":
            for input_key in artifact["review_inputs"]:
                if step_from_key(input_key) in {"chapter_draft", "humanization_revision", "chapter_repair"}:
                    state["artifacts"][input_key]["protected"] = True
    if args.status == "ready" and artifact.get("approval") == "required":
        state["director"].update({"status": "waiting_approval", "current_step": args.step, "current_target": key, "stop_reason": None})
    elif args.status == "blocked":
        state["director"].update({"status": "blocked", "stop_reason": args.reason or "step_blocked"})
    elif args.review_decision == "stop_for_replan":
        state["director"].update({"status": "blocked", "current_step": args.step, "current_target": key, "stop_reason": "stop_for_replan"})
    else:
        state["director"].update({"status": "running", "current_step": None, "current_target": None, "stop_reason": None})
    number = chapter_number(args.target)
    if args.step == "continuity_update" and args.status == "ready" and number is not None:
        state["continuity"]["last_committed_chapter"] = chapter_target(number)
        requested = state["director"].get("requested_range")
        if isinstance(requested, dict) and number >= int(requested.get("end", number + 1)):
            state["director"].update({"status": "waiting_approval", "current_step": None, "current_target": "chapter_range", "stop_reason": "requested_range_completed"})
    refresh_usage_projection(workspace, state)
    state["next_action"] = decide_next(state)
    atomic_write_state(workspace, state)
    print(json.dumps({"finished": key, "status": args.status, "approval": artifact.get("approval"), "next_action": state["next_action"]}, ensure_ascii=False, indent=2))
    return 0


def command_block_step(args: argparse.Namespace) -> int:
    workspace = args.workspace.resolve()
    state = read_state(workspace)
    require_v3(state)
    key = artifact_key(args.step, args.target)
    artifact = state["artifacts"].get(key)
    if not isinstance(artifact, dict):
        raise ValueError(f"unknown artifact: {key}")
    artifact.update({"status": "blocked", "block_reason": args.reason, "updated_at": now_utc()})
    state["director"].update({"status": "blocked", "current_step": args.step, "current_target": key, "stop_reason": args.reason})
    state["next_action"] = decide_next(state)
    atomic_write_state(workspace, state)
    print(json.dumps({"blocked": key, "reason": args.reason, "next_action": state["next_action"]}, ensure_ascii=False, indent=2))
    return 0


def command_approve(args: argparse.Namespace) -> int:
    workspace = args.workspace.resolve()
    state = read_state(workspace)
    require_v3(state)
    if state["director"].get("stop_reason") == "stop_for_replan" and args.target != state["director"].get("current_target"):
        raise ValueError("approve the blocked review to authorize replan; other approvals cannot clear it")
    if args.target == "chapter_range":
        if args.range_start is None or args.range_end is None:
            raise ValueError("chapter_range approval requires --range-start and --range-end")
        if args.range_start < 1 or args.range_end < args.range_start:
            raise ValueError("chapter range must satisfy 1 <= start <= end")
        state["director"].update(
            {
                "status": "idle",
                "current_step": None,
                "current_target": None,
                "requested_range": {"start": args.range_start, "end": args.range_end},
                "stop_reason": None,
            }
        )
        state["next_action"] = decide_next(state)
        atomic_write_state(workspace, state)
        print(
            json.dumps(
                {
                    "approved": args.target,
                    "requested_range": state["director"]["requested_range"],
                    "next_action": state["next_action"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    artifact = state["artifacts"].get(args.target)
    if not isinstance(artifact, dict):
        raise ValueError(f"unknown approval target: {args.target}")
    if not args.overwrite and step_from_key(args.target) in MILESTONE_STEPS and pending_confirmation(artifact_location(workspace, artifact)):
        raise ValueError("confirmation conflict: synchronize document choices with the author's decision before approval")
    artifact["approval"] = "delegated" if args.delegate else "approved"
    if args.overwrite:
        artifact["overwrite_approved"] = True
    state["director"].update({"status": "idle", "current_step": None, "current_target": None, "stop_reason": None})
    state["next_action"] = decide_next(state)
    atomic_write_state(workspace, state)
    print(json.dumps({"approved": args.target, "delegated": args.delegate, "overwrite": args.overwrite, "next_action": state["next_action"]}, ensure_ascii=False, indent=2))
    return 0


def run_script(name: str, arguments: list[str]) -> int:
    script = Path(__file__).resolve().with_name(name)
    completed = subprocess.run([sys.executable, str(script), *arguments], check=False)
    return completed.returncode


def command_context(args: argparse.Namespace) -> int:
    workspace = args.workspace.resolve()
    state = read_state(workspace)
    validate_confirmation_labels(workspace, state.get("artifacts", {}), ["novel_brief", "story_bible"])
    validate_fanfic_source(state)
    validate_style_preflight(workspace, state)
    number = args.chapter
    if number < 1 or args.max_chars < 1:
        raise ValueError("chapter and context budget must be positive")
    validate_chapter_progress(state, chapter_target(number), "context_package")
    structured = (workspace / "continuity/data").is_dir()
    sources: list[str] = []
    parts = [f"# 第{number:03d}章上下文包"]

    def append_file(relative: str, tail: bool = False, required: bool = True) -> bool:
        path = workspace / relative
        if not path.is_file():
            return False
        content = path.read_text(encoding="utf-8").strip()
        if tail:
            content = content[-3500:]
        section = f"### `{relative}`\n{content}"
        if len("\n\n".join(parts + [section])) + 1 > args.max_chars:
            if required:
                raise ValueError(f"context budget cannot fit required source {relative}; increase --max-chars")
            return False
        parts.append(section)
        sources.append(relative)
        return True

    # These sources have the same priority with Markdown and structured stores.
    plan = state.get("artifacts", {}).get(f"chapter_{number:03d}_plan", {})
    plan_path = safe_relative_path(plan.get("path", f"chapters/chapter-{number:03d}/plan.md"))
    if not append_file(plan_path):
        raise ValueError("required chapter plan is missing")
    if number > 1:
        previous = f"chapter_{number - 1:03d}"
        candidates = []
        for kind in ("repair", "humanized", "draft"):
            artifact = state.get("artifacts", {}).get(f"{previous}_{kind}", {})
            if artifact.get("status") == "ready" and artifact.get("path"):
                candidates.append(safe_relative_path(artifact["path"]))
        candidates += [f"chapters/chapter-{number - 1:03d}/draft-humanized.md",
                       f"chapters/chapter-{number - 1:03d}/draft.md"]
        found_tail = False
        for relative in dict.fromkeys(candidates):
            if append_file(relative, tail=True):
                found_tail = True
                break
        if not found_tail:
            raise ValueError("required previous chapter prose is missing")
    if not append_file("novel-brief.md"):
        raise ValueError("required novel-brief.md is missing")
    style_path = workspace / "writing-style.md"
    if style_path.is_symlink():
        raise ValueError("writing-style.md must be a local book snapshot")
    if style_path.is_file():
        style = style_path.read_text(encoding="utf-8").strip()
        if not style or len(style) > 2200:
            raise ValueError("writing-style.md must contain a concise, non-empty style contract (up to 2200 characters)")
        append_file("writing-style.md")
    if state.get("novel", {}).get("mode") == "fanfic":
        handoff = state.get("artifacts", {}).get("fanfic_handoff", {})
        if handoff.get("status") != "ready":
            raise ValueError("fanfic_handoff must be ready before chapter context")
        if not append_file(safe_relative_path(handoff["path"])):
            raise ValueError("fanfic_handoff file is missing")
    selection = analysis_reference.selection_path(workspace, number)
    reference_context = ""
    if selection.exists() or selection.is_symlink():
        reference_context = analysis_reference.render_context(workspace, number)
        sources.append(selection.relative_to(workspace).as_posix())
    if bool(args.asset_library) != bool(args.asset_selection):
        raise ValueError("--asset-library and --asset-selection must be used together")
    if args.asset_library:
        if not structured:
            raise ValueError("cross-book context requires a migrated structured continuity store")
        selection = workspace / safe_relative_path(args.asset_selection)
        parts.append(asset_graph.render_selection_context(args.asset_library.resolve(), workspace, selection,
                                                         min(2500, args.max_chars * 35 // 100)).strip())
        sources.append(safe_relative_path(args.asset_selection))
    remaining = args.max_chars - len("\n\n".join(parts)) - 3
    if remaining < 0:
        raise ValueError("context budget is too small for required sources and selected references")
    if structured:
        characters = {item.strip() for item in args.characters.split(",") if item.strip()}
        parts.append(continuity_store.assemble_context(workspace, number, characters, remaining).strip())
        sources.append("continuity/data/*.yaml")
    optional = ["story-bible.md", "world-bible.md", "characters/character-roster.md"]
    artifacts = state.get("artifacts", {})
    plan = artifacts.get(f"chapter_{number:03d}_plan", {})
    windows = [artifacts[key]["path"] for key in plan.get("depends_on", [])
               if key in artifacts and step_from_key(key) == "beat_sheet" and artifacts[key].get("path")]
    optional += windows or ["volumes/volume-01-beat-sheet.md"]
    if not structured:
        optional += ["continuity/fact-ledger.md", "continuity/payoff-ledger.md", "continuity/resource-ledger.md"]
    omitted = []
    for relative in optional:
        if not append_file(relative, required=False):
            omitted.append(relative)
    rendered = "\n\n".join(parts).strip() + "\n"
    if len(rendered) > args.max_chars:
        raise ValueError("context exceeds --max-chars; increase the budget for required sources")
    if reference_context:
        rendered += "\n" + reference_context
    if args.output:
        atomic_write_text(workspace / safe_relative_path(args.output), rendered)
        print(json.dumps({"written": safe_relative_path(args.output), "sources": sources,
                          "omitted_missing_or_over_budget": omitted}, ensure_ascii=False, indent=2))
    else:
        print(rendered, end="")
    return 0


def command_checkpoint(args: argparse.Namespace) -> int:
    return run_script("continuity_store.py", ["checkpoint", str(args.workspace.resolve()), "--chapter", args.chapter, "--reason", args.reason])


def command_usage(args: argparse.Namespace) -> int:
    forwarded = [args.action, str(args.workspace.resolve())]
    if args.action == "summarize" and args.write:
        forwarded.append("--write")
    return run_script("token_usage.py", forwarded)


def command_export(args: argparse.Namespace) -> int:
    forwarded = [str(args.workspace.resolve()), "--source", args.source, "--stable-only"]
    if args.start is not None:
        forwarded += ["--start", str(args.start)]
    if args.end is not None:
        forwarded += ["--end", str(args.end)]
    if args.output:
        forwarded += ["--output", args.output]
    if args.dry_run:
        forwarded.append("--dry-run")
    return run_script("export_novel_txt.py", forwarded)


def add_workspace(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("workspace", type=Path)


def add_step_identity(parser: argparse.ArgumentParser) -> None:
    add_workspace(parser)
    parser.add_argument("--step", required=True)
    parser.add_argument("--target", required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="create a schema-v3 novel workspace")
    add_workspace(init)
    init.add_argument("--title", required=True)
    init.add_argument("--mode", choices=sorted(DIRECTOR_MODES), default="milestone_approval")
    init.add_argument("--novel-mode", choices=("original", "fanfic"), default="original")
    init.add_argument("--source-analysis")
    init.add_argument("--fanfic-mode", choices=("continue_from_breakpoint", "new_story_with_canon"))
    init.add_argument("--read-scope")
    init.add_argument("--branch-chapter")
    init.set_defaults(handler=command_init)

    migrate = commands.add_parser("migrate", help="back up and explicitly migrate a v1/v2 state")
    add_workspace(migrate)
    migrate.add_argument("--mode", choices=sorted(DIRECTOR_MODES), default="milestone_approval")
    migrate.add_argument("--dry-run", action="store_true")
    migrate.set_defaults(handler=command_migrate)

    status = commands.add_parser("status", help="show the recoverable workspace projection")
    add_workspace(status)
    status.add_argument("--format", choices=("json", "markdown"), default="json")
    status.set_defaults(handler=command_status)

    next_command = commands.add_parser("next", help="return the one deterministic next action")
    add_workspace(next_command)
    next_command.set_defaults(handler=command_next)

    validate = commands.add_parser("validate", help="validate state, paths, dependencies, and fingerprints")
    add_workspace(validate)
    validate.set_defaults(handler=command_validate)

    reconcile = commands.add_parser("reconcile", help="protect user edits and stale their downstream artifacts")
    add_workspace(reconcile)
    reconcile.set_defaults(handler=command_reconcile)

    opening = commands.add_parser("set-opening-choices", help="confirm the three required opening choices")
    add_workspace(opening)
    opening.add_argument("--channel", required=True)
    opening.add_argument("--publication-format", required=True)
    opening.add_argument("--primary-reader-reward", required=True)
    opening.add_argument("--delegated", action="store_true")
    opening.set_defaults(handler=command_set_opening_choices)

    start = commands.add_parser("start-step", help="start a generation step after dependency checks")
    add_step_identity(start)
    start.add_argument("--artifact", required=True)
    start.add_argument("--depends-on", action="append", default=[])
    start.add_argument("--volume", type=int, help="volume owning this chapter plan; required when ambiguous")
    start.add_argument("--run-id")
    start.add_argument("--range-start", type=int)
    start.add_argument("--range-end", type=int)
    start.add_argument("--repair-scope", choices=("local", "chapter"))
    start.set_defaults(handler=command_start_step)

    finish = commands.add_parser("finish-step", help="validate artifact, record usage, then atomically finish a step")
    add_step_identity(finish)
    finish.add_argument("--artifact", required=True)
    finish.add_argument("--status", choices=("ready", "stale", "blocked"), default="ready")
    finish.add_argument("--measurement", choices=sorted(token_usage.MEASUREMENTS), required=True)
    finish.add_argument("--provider")
    finish.add_argument("--model")
    finish.add_argument("--request-id")
    finish.add_argument("--reason")
    finish.add_argument("--review-decision", choices=("accepted", "repair_required", "stop_for_replan"))
    token_usage.add_token_arguments(finish)
    finish.set_defaults(handler=command_finish_step)

    block = commands.add_parser("block-step", help="record a blocking condition and recovery target")
    add_step_identity(block)
    block.add_argument("--reason", required=True)
    block.set_defaults(handler=command_block_step)

    approve = commands.add_parser("approve", help="approve a milestone or a protected overwrite")
    add_workspace(approve)
    approve.add_argument("--target", required=True)
    approve.add_argument("--delegate", action="store_true")
    approve.add_argument("--overwrite", action="store_true")
    approve.add_argument("--range-start", type=int)
    approve.add_argument("--range-end", type=int)
    approve.set_defaults(handler=command_approve)

    context = commands.add_parser("context", help="assemble bounded chapter context")
    add_workspace(context)
    context.add_argument("--chapter", type=int, required=True)
    context.add_argument("--characters", default="")
    context.add_argument("--max-chars", type=int, default=9000)
    context.add_argument("--output")
    context.add_argument("--asset-library", type=Path)
    context.add_argument("--asset-selection", help="workspace-relative context-packages/chapter-XXX.assets.yaml")
    context.set_defaults(handler=command_context)

    checkpoint = commands.add_parser("checkpoint", help="create a structured continuity checkpoint")
    add_workspace(checkpoint)
    checkpoint.add_argument("--chapter", required=True)
    checkpoint.add_argument("--reason", default="manual")
    checkpoint.set_defaults(handler=command_checkpoint)

    usage = commands.add_parser("usage", help="validate or summarize token usage")
    add_workspace(usage)
    usage.add_argument("action", choices=("validate", "summarize"))
    usage.add_argument("--write", action="store_true")
    usage.set_defaults(handler=command_usage)

    export = commands.add_parser("export", help="export stable chapter prose")
    add_workspace(export)
    export.add_argument("--start", type=int)
    export.add_argument("--end", type=int)
    export.add_argument("--source", choices=("auto", "humanized", "draft"), default="auto")
    export.add_argument("--output")
    export.add_argument("--dry-run", action="store_true")
    export.set_defaults(handler=command_export)
    return parser


def main() -> int:
    configure_utf8_output()
    parser = build_parser()
    args = parser.parse_args()
    try:
        if hasattr(args, "max_chars") and args.max_chars < 1000:
            raise ValueError("--max-chars must be at least 1000")
        return args.handler(args)
    except (OSError, ValueError, yaml.YAMLError) as error:
        print(f"novelctl failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
