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
    elif re.match(r"^volume_\d+_skeleton$", key):
        direct = ["volume_strategy"]
    elif re.match(r"^volume_\d+_beat_sheet$", key):
        volume = key.split("_beat_sheet")[0]
        direct = [f"{volume}_skeleton"]
    else:
        match = re.match(r"^chapter_(\d+)_(plan|context|context_package|draft|humanized|humanized_draft|review|repair|delta)$", key)
        if match:
            number = int(match.group(1))
            kind = match.group(2)
            prefix = f"chapter_{number:03d}"
            if kind == "plan":
                direct = ["volume_01_beat_sheet"]
                previous = f"chapter_{number - 1:03d}_delta"
                if number > 1 and previous in artifacts:
                    direct.append(previous)
            elif kind in {"context", "context_package"}:
                direct = [f"{prefix}_plan"]
            elif kind == "draft":
                direct = [f"{prefix}_plan"]
                context_key = f"{prefix}_context"
                if context_key in artifacts:
                    direct.append(context_key)
            elif kind in {"humanized", "humanized_draft"}:
                direct = [f"{prefix}_draft"]
            elif kind == "review":
                humanized = f"{prefix}_humanized"
                direct = [humanized if humanized in artifacts else f"{prefix}_draft"]
            elif kind == "repair":
                direct = [f"{prefix}_review"]
            else:
                repair = f"{prefix}_repair"
                direct = [repair if repair in artifacts else f"{prefix}_review"]
    return [item for item in direct if item in artifacts]


def approval_for(step: str, mode: str, existing_ready: bool = False) -> str:
    if existing_ready:
        return "approved"
    if mode == "auto" and step in MILESTONE_STEPS:
        return "delegated"
    if step in MILESTONE_STEPS:
        return "required"
    return "not_required"


def initial_artifacts(mode: str) -> dict[str, Any]:
    definitions = [
        ("novel_brief", "novel-brief.md", []),
        ("story_bible", "story-bible.md", ["novel_brief"]),
        ("world_bible", "world-bible.md", ["novel_brief", "story_bible"]),
        ("character_roster", "characters/character-roster.md", ["novel_brief", "story_bible"]),
        ("volume_strategy", "volumes/volume-strategy.md", ["novel_brief", "story_bible", "world_bible", "character_roster"]),
        ("volume_01_skeleton", "volumes/volume-01.md", ["volume_strategy"]),
        ("volume_01_beat_sheet", "volumes/volume-01-beat-sheet.md", ["volume_01_skeleton"]),
    ]
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


def initial_state(title: str, mode: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "workspace": {"persistence_mode": "workspace", "promoted_from_preview": False},
        "novel": {"title": title, "mode": "original", "current_stage": "novel_brief"},
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
        "artifacts": initial_artifacts(mode),
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
    if decision not in {"accepted", "repair_required"}:
        return make_next("record_review_decision", f"{prefix}_review", f"第 {number} 章审校尚未给出验收结论")
    if f"{prefix}_delta" not in artifacts:
        return make_next("produce_artifact", f"{prefix}_delta", f"第 {number} 章可提交连续性差分")
    return make_next("resume_step", f"{prefix}_delta", f"第 {number} 章连续性尚未完成提交")


def decide_next(state: dict[str, Any]) -> dict[str, Any]:
    director = state.get("director", {}) if isinstance(state.get("director"), dict) else {}
    if director.get("status") == "waiting_approval":
        current = str(director.get("current_target") or "milestone")
        if current == "chapter_range" and director.get("stop_reason") == "requested_range_completed":
            return make_next("request_chapter_range", current, "已完成授权章节范围，需要用户指定下一范围", True)
        return make_next("approve_milestone", current, "当前里程碑需要用户批准", True)
    if not opening_choices_ready(state):
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
    if workspace.exists() and any(workspace.iterdir()):
        raise ValueError(f"workspace is not empty: {workspace}")
    workspace.mkdir(parents=True, exist_ok=True)
    ensure_workspace_directories(workspace)
    template = Path(__file__).resolve().parents[1] / "assets" / "workspace-template" / "production"
    for name in ("recovery.md", "quality-debt.md"):
        shutil.copy2(template / name, workspace / "production" / name)
    (workspace / "production" / "token-usage.jsonl").touch(exist_ok=True)
    atomic_write_state(workspace, initial_state(args.title, args.mode))
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
    if state.get("schema_version") == SCHEMA_VERSION:
        print(json.dumps({"migrated": False, "reason": "already_v3"}, ensure_ascii=False, indent=2))
        return 0
    original = state_path(workspace)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = original.with_name(f"novel-state.yaml.bak.{stamp}")
    shutil.copy2(original, backup)
    mode = args.mode
    state["schema_version"] = SCHEMA_VERSION
    state.setdefault("workspace", {"persistence_mode": "workspace", "promoted_from_preview": True})
    state.setdefault("novel", {"title": workspace.name, "mode": "original", "current_stage": "recovery"})
    state["director"] = {
        "mode": mode,
        "status": "idle",
        "run_id": None,
        "current_step": None,
        "current_target": None,
        "requested_range": None,
        "stop_reason": None,
    }
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
        backup.unlink(missing_ok=True)
        print(yaml.safe_dump(state, allow_unicode=True, sort_keys=False, width=120), end="")
        return 0
    atomic_write_state(workspace, state)
    print(json.dumps({"migrated": True, "backup": str(backup), "schema_version": SCHEMA_VERSION}, ensure_ascii=False, indent=2))
    return 0


def validation_report(workspace: Path, state: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if state.get("schema_version") not in SUPPORTED_READ_VERSIONS:
        errors.append("unsupported schema_version")
    if state.get("schema_version") == SCHEMA_VERSION:
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
    result = {
        "title": state.get("novel", {}).get("title"),
        "schema_version": state.get("schema_version"),
        "director": state.get("director"),
        "artifact_counts": counts,
        "protected_artifacts": sorted(protected),
        "continuity": state.get("continuity"),
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
    graph = reverse_dependencies(artifacts)
    changed: list[str] = []
    stale: list[str] = []
    protected_conflicts: list[str] = []
    for key, artifact in artifacts.items():
        path = artifact_location(workspace, artifact)
        recorded = artifact.get("sha256")
        if recorded and path.is_file():
            current = file_sha256(path)
            if current != recorded:
                artifact.update({"sha256": current, "source": "user_edited", "protected": True, "updated_at": now_utc()})
                changed.append(key)
                for dependent in descendants(key, graph):
                    candidate = artifacts[dependent]
                    if candidate.get("protected"):
                        protected_conflicts.append(dependent)
                    elif candidate.get("status") == "ready":
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
    return supplied if supplied else infer_dependencies(key, artifacts)


def ensure_dependencies_ready(artifacts: dict[str, Any], dependencies: Iterable[str]) -> None:
    for dependency in dependencies:
        artifact = artifacts.get(dependency)
        if not isinstance(artifact, dict) or artifact.get("status") != "ready":
            raise ValueError(f"dependency is not ready: {dependency}")
        if artifact.get("approval") == "required":
            raise ValueError(f"dependency awaits milestone approval: {dependency}")


def command_start_step(args: argparse.Namespace) -> int:
    workspace = args.workspace.resolve()
    state = read_state(workspace)
    require_v3(state)
    if not SAFE_NAME.fullmatch(args.step):
        raise ValueError("step has invalid format")
    if args.step == "novel_brief" and not opening_choices_ready(state):
        raise ValueError("confirm channel, publication format, and primary reader reward before novel_brief")
    key = artifact_key(args.step, args.target)
    artifacts = state["artifacts"]
    existing = artifacts.get(key)
    if isinstance(existing, dict) and existing.get("protected") and not existing.get("overwrite_approved"):
        raise ValueError(f"artifact is protected; approve overwrite first: {key}")
    dependencies = dependency_list(args, key, artifacts)
    ensure_dependencies_ready(artifacts, dependencies)
    relative = safe_relative_path(args.artifact)
    run_id = args.run_id or str(uuid.uuid4())
    entry = existing if isinstance(existing, dict) else {}
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
    key = artifact_key(args.step, args.target)
    artifact = state["artifacts"].get(key)
    if not isinstance(artifact, dict) or artifact.get("status") != "in_progress":
        raise ValueError(f"step is not in progress: {key}")
    relative = safe_relative_path(args.artifact)
    if artifact.get("path") != relative:
        raise ValueError("artifact path differs from start-step")
    path = workspace / relative
    if args.status == "ready" and (not path.is_file() or path.stat().st_size == 0):
        raise ValueError(f"usable artifact is missing or empty: {path}")
    if args.step == "chapter_review" and args.status == "ready" and args.review_decision is None:
        raise ValueError("chapter_review requires --review-decision")
    run_id = state["director"].get("run_id")
    record_usage(args, workspace, run_id)
    artifact.update({"status": args.status, "sha256": file_sha256(path) if path.is_file() else None, "updated_at": now_utc()})
    if args.step == "chapter_review" and args.review_decision is not None:
        artifact["review_decision"] = args.review_decision
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
    if (workspace / "continuity" / "data").is_dir():
        forwarded = ["assemble-context", str(workspace), "--chapter", str(args.chapter), "--max-chars", str(args.max_chars)]
        if args.characters:
            forwarded += ["--characters", args.characters]
        return run_script("continuity_store.py", forwarded)
    state = read_state(workspace)
    number = args.chapter
    selected: list[tuple[str, str]] = []
    candidates = [
        f"chapters/chapter-{number:03d}/plan.md",
        "novel-brief.md",
        "story-bible.md",
        "world-bible.md",
        "characters/character-roster.md",
        "volumes/volume-01-beat-sheet.md",
        "continuity/fact-ledger.md",
        "continuity/payoff-ledger.md",
        "continuity/resource-ledger.md",
    ]
    if number > 1:
        candidates.insert(1, f"chapters/chapter-{number - 1:03d}/draft-humanized.md")
        candidates.insert(2, f"chapters/chapter-{number - 1:03d}/draft.md")
    budget = args.max_chars
    for relative in candidates:
        path = workspace / relative
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8").strip()
        if "draft" in path.name and len(content) > 3500:
            content = content[-3500:]
        remaining = budget - sum(len(value) for _, value in selected)
        if remaining <= 0:
            break
        selected.append((relative, content[:remaining]))
    output = [f"# 第{number:03d}章上下文包", "", "## 已选权威来源"]
    for relative, content in selected:
        output += [f"\n### `{relative}`", content]
    output += ["", "## 裁剪说明", f"- 最大字符预算：{args.max_chars}", "- 未列出的文件因无关、重复、缺失或预算限制而省略。"]
    rendered = "\n".join(output).strip() + "\n"
    if args.output:
        relative_output = safe_relative_path(args.output)
        atomic_write_text(workspace / relative_output, rendered)
        print(json.dumps({"written": relative_output, "sources": [item[0] for item in selected]}, ensure_ascii=False, indent=2))
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
