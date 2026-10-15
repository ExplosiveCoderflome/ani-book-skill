#!/usr/bin/env python3
"""Validate and plan explicit GitHub sources for writing-related Skills.

Network installation is intentionally delegated to the preinstalled
skill-installer Skill. This script validates local configuration and candidate
content, and renders a deterministic plan without network access.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

import yaml


CONFIG_RELATIVE = Path("production/skill-sources.yaml")
SCHEMA_VERSION = 1
PURPOSES = {"anti-ai", "writing-style"}
UPDATE_POLICIES = {"manual", "notify"}
STATUSES = {"candidate", "enabled", "disabled", "update_available"}
APPROVALS = {"pending", "confirmed", "rejected"}
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
REPO_PART_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
SHA40_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")
SHA64_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


def configure_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


def read_yaml(path: Path) -> Any:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ValueError(f"invalid YAML in {path}: {error}") from error
    return {} if value is None else value


def config_path(workspace: Path) -> Path:
    return workspace / CONFIG_RELATIVE


def _is_safe_repo(value: Any) -> bool:
    if not isinstance(value, str) or value.count("/") != 1:
        return False
    owner, repo = value.split("/")
    return bool(owner and repo and REPO_PART_PATTERN.fullmatch(owner) and REPO_PART_PATTERN.fullmatch(repo))


def _is_safe_repo_path(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and all(part not in {"", ".", ".."} for part in path.parts)


def _is_safe_skill_name(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and "/" not in value and "\\" not in value and value not in {".", ".."}


def _optional_sha(value: Any, pattern: re.Pattern[str], label: str, errors: list[str]) -> None:
    if value in (None, ""):
        return
    if not isinstance(value, str) or not pattern.fullmatch(value):
        errors.append(f"{label} must be a hexadecimal digest of the expected length")


def validate_config(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["skill-sources.yaml must be a YAML mapping"]
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    policy = data.get("policy", {})
    if not isinstance(policy, dict):
        errors.append("policy must be a mapping")
        policy = {}
    if not isinstance(policy.get("enabled", False), bool):
        errors.append("policy.enabled must be a boolean")
    if policy.get("update_policy", "manual") not in UPDATE_POLICIES:
        errors.append("policy.update_policy must be manual or notify")
    if policy.get("require_confirmation", True) is not True:
        errors.append("policy.require_confirmation must remain true")
    sources = data.get("sources", [])
    if not isinstance(sources, list):
        return errors + ["sources must be a list"]
    seen: set[str] = set()
    for position, source in enumerate(sources, 1):
        label = f"sources[{position}]"
        if not isinstance(source, dict):
            errors.append(f"{label} must be a mapping")
            continue
        source_id = source.get("id")
        if not isinstance(source_id, str) or not ID_PATTERN.fullmatch(source_id):
            errors.append(f"{label}.id must be a lowercase identifier")
        elif source_id in seen:
            errors.append(f"duplicate source id {source_id}")
        else:
            seen.add(source_id)
        if source.get("purpose") not in PURPOSES:
            errors.append(f"{label}.purpose must be anti-ai or writing-style")
        if not _is_safe_repo(source.get("repo")):
            errors.append(f"{label}.repo must be owner/repository")
        if not _is_safe_repo_path(source.get("path")):
            errors.append(f"{label}.path must be a relative path inside the repository")
        requested_ref = source.get("requested_ref", "main")
        if not isinstance(requested_ref, str) or not requested_ref.strip() or any(char.isspace() for char in requested_ref):
            errors.append(f"{label}.requested_ref must be a non-empty ref without whitespace")
        resolved_commit = source.get("resolved_commit", "")
        if resolved_commit not in (None, "") and (not isinstance(resolved_commit, str) or not SHA40_PATTERN.fullmatch(resolved_commit)):
            errors.append(f"{label}.resolved_commit must be a full 40-character commit SHA")
        _optional_sha(source.get("content_sha256"), SHA64_PATTERN, f"{label}.content_sha256", errors)
        if source.get("installed_skill") not in (None, "") and not _is_safe_skill_name(source.get("installed_skill")):
            errors.append(f"{label}.installed_skill must be a single directory name")
        status = source.get("status", "candidate")
        if status not in STATUSES:
            errors.append(f"{label}.status is unsupported")
        approval = source.get("approval", "pending")
        if approval not in APPROVALS:
            errors.append(f"{label}.approval is unsupported")
        content_sha = source.get("content_sha256", "")
        if status == "enabled" and (
            approval != "confirmed"
            or not SHA40_PATTERN.fullmatch(str(resolved_commit))
            or not SHA64_PATTERN.fullmatch(str(content_sha))
        ):
            errors.append(f"{label} enabled sources require approval=confirmed, pinned resolved_commit, and content_sha256")
        if status == "update_available" and not SHA40_PATTERN.fullmatch(str(resolved_commit)):
            errors.append(f"{label} update_available sources require the currently enabled commit")
        max_bytes = source.get("max_bytes", 262144)
        if not isinstance(max_bytes, int) or not 1 <= max_bytes <= 1048576:
            errors.append(f"{label}.max_bytes must be an integer from 1 to 1048576")
    if policy.get("enabled") is not True:
        for source in sources:
            if isinstance(source, dict) and source.get("status", "candidate") == "enabled":
                errors.append("policy.enabled must be true when a source is enabled")
    return errors


def load_config(workspace: Path) -> tuple[Path, dict[str, Any] | None]:
    path = config_path(workspace)
    if not path.is_file():
        return path, None
    data = read_yaml(path)
    errors = validate_config(data)
    if errors:
        raise ValueError("; ".join(errors))
    return path, data


def source_plan(source: dict[str, Any], workspace: Path) -> dict[str, Any]:
    resolved = source.get("resolved_commit") or ""
    status = source.get("status", "candidate")
    pinned = bool(SHA40_PATTERN.fullmatch(str(resolved)))
    install_ref = resolved if pinned and status != "update_available" else source.get("requested_ref", "main")
    phase = "enable" if status == "enabled" and pinned else "candidate"
    return {
        "id": source["id"],
        "purpose": source["purpose"],
        "repo": source["repo"],
        "path": source["path"],
        "requested_ref": source.get("requested_ref", "main"),
        "current_commit": resolved or None,
        "install_ref": install_ref,
        "phase": phase,
        "approval": source.get("approval", "pending"),
        "candidate_directory": str((workspace / "production/remote-skill-candidates").resolve()),
        "github_tree_url": f"https://github.com/{source['repo']}/tree/{install_ref}/{source['path']}",
        "max_bytes": source.get("max_bytes", 262144),
        "requires_user_confirmation": True,
    }


def candidate_snapshot(workspace: Path, source: dict[str, Any]) -> dict[str, Any]:
    base = workspace / "production/remote-skill-candidates"
    name = source.get("installed_skill") or PurePosixPath(source["path"]).name
    if not _is_safe_skill_name(name):
        raise ValueError("candidate directory must be a single name")
    root = base / name
    if root.is_symlink() or not root.is_dir() or not root.resolve().is_relative_to(base.resolve()):
        raise ValueError(f"candidate directory missing or outside candidate area: {name}")
    if not (root / "SKILL.md").is_file():
        raise ValueError("candidate SKILL.md is missing")
    manifest = []
    total = 0
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("candidate contains a symlink or escaped path")
        if not path.is_file():
            continue
        size = path.stat().st_size
        total += size
        if total > source.get("max_bytes", 262144):
            raise ValueError("candidate exceeds max_bytes")
        manifest.append([path.relative_to(root).as_posix(), size, hashlib.sha256(path.read_bytes()).hexdigest()])
    payload = json.dumps(manifest, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return {"content_sha256": hashlib.sha256(payload).hexdigest(), "total_bytes": total,
            "file_count": len(manifest), "candidate_path": str(root)}


def command_candidate(args: argparse.Namespace) -> int:
    workspace = args.workspace.resolve()
    _, data = load_config(workspace)
    sources = [item for item in (data or {}).get("sources", []) if item["id"] == args.source_id]
    if not sources:
        raise ValueError(f"unknown source id: {args.source_id}")
    report = candidate_snapshot(workspace, sources[0])
    expected = sources[0].get("content_sha256")
    if expected and expected != report["content_sha256"]:
        raise ValueError("candidate content_sha256 does not match the reviewed snapshot")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def command_validate(args: argparse.Namespace) -> int:
    path, data = load_config(args.workspace.resolve())
    if data is None:
        print(json.dumps({"configured": False, "path": str(path), "valid": True}, ensure_ascii=False, indent=2))
        return 0
    for source in data.get("sources", []):
        if source.get("status") == "enabled":
            actual = candidate_snapshot(args.workspace.resolve(), source)
            if actual["content_sha256"] != source["content_sha256"]:
                raise ValueError("candidate content_sha256 does not match the reviewed snapshot")
    print(json.dumps({"configured": True, "path": str(path), "valid": True, "source_count": len(data.get("sources", []))}, ensure_ascii=False, indent=2))
    return 0


def command_plan(args: argparse.Namespace) -> int:
    workspace = args.workspace.resolve()
    path, data = load_config(workspace)
    if data is None:
        print(json.dumps({"configured": False, "path": str(path), "plans": []}, ensure_ascii=False, indent=2))
        return 0
    sources = data.get("sources", [])
    if args.source_id:
        sources = [source for source in sources if source.get("id") == args.source_id]
        if not sources:
            raise ValueError(f"unknown source id: {args.source_id}")
    print(json.dumps({"configured": True, "path": str(path), "plans": [source_plan(source, workspace) for source in sources]}, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate explicit GitHub writing-skill sources without network access.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, handler in (("validate", command_validate), ("plan", command_plan), ("candidate-report", command_candidate)):
        command = commands.add_parser(name)
        command.add_argument("workspace", type=Path)
        if name in {"plan", "candidate-report"}:
            command.add_argument("--source-id", required=name == "candidate-report")
        command.set_defaults(handler=handler)
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_utf8_output()
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except (OSError, ValueError, yaml.YAMLError) as error:
        print(f"skill source check failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
