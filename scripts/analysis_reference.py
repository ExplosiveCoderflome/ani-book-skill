#!/usr/bin/env python3
"""Validate explicit analysis mechanisms and render bounded craft context. No writes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError("reference path must be a workspace-relative path")
    value = Path(relative)
    if value.is_absolute() or ".." in value.parts:
        raise ValueError("reference path escapes workspace")
    resolved = (root / value).resolve(strict=True)
    if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
        raise ValueError("reference file escapes workspace or is missing")
    return resolved


def mapping(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML: {path.name}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"expected YAML mapping: {path.name}")
    return value


def text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing non-empty {label}")
    return value.strip()


def strings(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a non-empty list")
    return [text(item, label) for item in value]


def registry(root: Path) -> tuple[dict[str, Any], dict[str, Any], str]:
    state = mapping(local_file(root, "analysis-state.yaml"))
    source = state.get("source")
    if not isinstance(source, dict):
        raise ValueError("analysis source metadata is missing")
    lens = state.get("analysis_lens")
    if isinstance(lens, dict) and lens.get("status") != "ready":
        raise ValueError("analysis lens is not ready; confirm the core promise first")
    artifacts = state.get("artifacts", {})
    if not isinstance(artifacts, dict):
        raise ValueError("analysis artifacts must be a mapping")
    for artifact in artifacts.values():
        if isinstance(artifact, dict) and artifact.get("path") == "pattern-cards.yaml":
            if artifact.get("status") != "ready":
                raise ValueError("mechanism registry is not ready")
    path = local_file(root, "pattern-cards.yaml")
    data = mapping(path)
    for artifact in artifacts.values():
        if isinstance(artifact, dict) and artifact.get("path") == "pattern-cards.yaml":
            if artifact.get("sha256") and artifact["sha256"] != digest(path):
                raise ValueError("mechanism registry state fingerprint changed")
    if data.get("schema_version") != 1 or not isinstance(data.get("cards"), list):
        raise ValueError("unsupported mechanism registry")
    if not isinstance(data.get("source"), dict):
        raise ValueError("mechanism source metadata is missing")
    for key in ("fingerprint", "scope", "coverage"):
        if text(source.get(key), f"source.{key}") != data["source"].get(key):
            raise ValueError(f"analysis source {key} changed; review mechanisms first")
    if source["coverage"] not in {"sampled", "full"}:
        raise ValueError("analysis coverage must be sampled or full")
    ids = [card.get("id") if isinstance(card, dict) else None for card in data["cards"]]
    if any(not isinstance(value, str) or not re.fullmatch(r"PATTERN-\d{3,}", value) for value in ids) or len(set(ids)) != len(ids):
        raise ValueError("mechanism IDs must be unique PATTERN-XXX identifiers")
    return data, state, digest(path)


def validate_card(root: Path, card: dict[str, Any], state: dict[str, Any]) -> None:
    if card.get("status") != "ready":
        raise ValueError(f"mechanism is not ready: {card['id']}")
    for key in ("title", "scope", "core_promise", "problem", "mechanism", "payoff"):
        text(card.get(key), key)
    for key in ("stimulus_object", "viewing_position", "psychological_progression", "return_attachment"):
        if key in card:
            text(card[key], key)
    for key in ("prerequisites", "failure_modes", "forbidden_elements"):
        strings(card.get(key), key)
    evidence = card.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("mechanism requires evidence")
    artifacts = state.get("artifacts", {})
    if not isinstance(artifacts, dict):
        raise ValueError("analysis artifacts must be a mapping")
    for item in evidence:
        if not isinstance(item, dict):
            raise ValueError("invalid mechanism evidence")
        relative = text(item.get("path"), "evidence.path")
        if Path(relative).suffix.lower() != ".md" or relative.split("/")[0] in {"source", "retrieval"}:
            raise ValueError("evidence must reference analysis Markdown, not raw source or caches")
        path = local_file(root, relative)
        actual = digest(path)
        if actual != item.get("sha256"):
            raise ValueError(f"evidence changed: {relative}")
        for artifact in artifacts.values():
            if isinstance(artifact, dict) and artifact.get("path") == relative:
                if artifact.get("status") in {"stale", "blocked", "missing", "in_progress"}:
                    raise ValueError(f"evidence is not ready: {relative}")
                if artifact.get("sha256") and artifact["sha256"] != actual:
                    raise ValueError(f"evidence state fingerprint changed: {relative}")


def inspect(root: Path) -> dict[str, Any]:
    root = root.resolve()
    data, state, fingerprint = registry(root)
    results = []
    for card in data["cards"]:
        try:
            validate_card(root, card, state)
            error = None
        except (ValueError, OSError) as exc:
            error = str(exc)
        results.append({"id": card["id"], "title": card.get("title"), "usable": error is None, "error": error})
    return {"registry_sha256": fingerprint, "source": data["source"], "cards": results}


def selection_path(workspace: Path, chapter: int) -> Path:
    if type(chapter) is not int or chapter < 1:
        raise ValueError("chapter must be a positive integer")
    return workspace / "context-packages" / f"chapter-{chapter:03d}.references.yaml"


def validate_selection(workspace: Path, chapter: int) -> list[dict[str, Any]]:
    path = selection_path(workspace, chapter)
    selection = mapping(local_file(workspace, path.relative_to(workspace).as_posix()))
    if selection.get("schema_version") != 1 or type(selection.get("chapter")) is not int or selection["chapter"] != chapter:
        raise ValueError("reference selection schema or chapter mismatch")
    items = selection.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("reference selection items must be a non-empty list; remove the file to opt out")
    selected = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("invalid reference selection item")
        root = Path(text(item.get("analysis_workspace"), "analysis_workspace"))
        if not root.is_absolute():
            raise ValueError("analysis_workspace must be an explicit absolute path")
        root = root.resolve(strict=True)
        data, state, fingerprint = registry(root)
        if fingerprint != item.get("registry_sha256"):
            raise ValueError("mechanism registry changed; review and repin the selection")
        card = next((card for card in data["cards"] if card["id"] == item.get("pattern_id")), None)
        if card is None:
            raise ValueError("selected mechanism does not exist")
        identity = (root, card["id"])
        if identity in seen:
            raise ValueError("duplicate selected mechanism")
        seen.add(identity)
        validate_card(root, card, state)
        for key in ("use_for", "adaptation", "success_check"):
            text(item.get(key), key)
        strings(item.get("avoid"), "avoid")
        selected.append({"root": str(root), "source": data["source"], "card": card, "application": item})
    return selected


def render_context(workspace: Path, chapter: int, max_chars: int | None = None) -> str:
    if max_chars is None:
        selection = mapping(local_file(workspace, selection_path(workspace, chapter).relative_to(workspace).as_posix()))
        max_chars = selection.get("max_chars", 2200)
    if type(max_chars) is not int or max_chars < 1:
        raise ValueError("reference budget must be positive")
    lines = ["## 拆书机制参考（创作方法，不是本书事实）", "", "本书计划、角色和连续性约束优先。仅采用下列已明确改造的机制；审校时核对实际效果。", ""]
    for entry in validate_selection(workspace, chapter):
        card, source, application = entry["card"], entry["source"], entry["application"]
        lines += [f"### {card['id']} · {card['title']}", f"- 来源：{entry['root']}；来源范围：{source['scope']}（{source['coverage']}）；机制依据范围：{card['scope']}",
                  f"- 来源指纹：{source['fingerprint']}", f"- 解决问题：{card['problem']}", f"- 运作机制：{card['mechanism']}",
                  f"- 前提：{'；'.join(card['prerequisites'])}", f"- 核心阅读承诺：{card['core_promise']}",
                  *[f"- {label}：{card[key]}" for key, label in (("stimulus_object", "刺激对象"), ("viewing_position", "观看位置"),
                     ("psychological_progression", "心理推进"), ("return_attachment", "回归/依恋")) if key in card],
                  f"- 读者回报：{card['payoff']}",
                  f"- 失败方式：{'；'.join(card['failure_modes'])}", f"- 本章用途：{application['use_for']}",
                  f"- 原创改造：{application['adaptation']}", f"- 不可照搬：{'；'.join(card['forbidden_elements'] + application['avoid'])}",
                  f"- 审校检查：{application['success_check']}",
                  "- 证据：" + "；".join(f"{item['path']}#{item.get('anchor', '')} [sha256:{item['sha256']}]" for item in card["evidence"]), ""]
    rendered = "\n".join(lines).rstrip() + "\n"
    if len(rendered) > max_chars:
        raise ValueError(f"reference context needs {len(rendered)} characters, exceeds {max_chars}; select fewer mechanisms or explicitly increase reference budget")
    return rendered


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    scan = commands.add_parser("inspect", help="list mechanism readiness without writing")
    scan.add_argument("workspace", type=Path)
    for command in ("validate", "context"):
        sub = commands.add_parser(command)
        sub.add_argument("workspace", type=Path)
        sub.add_argument("--chapter", type=int, required=True)
        sub.add_argument("--max-chars", type=int)
    args = parser.parse_args()
    try:
        if args.command == "inspect":
            result = inspect(args.workspace)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            rendered = render_context(args.workspace.resolve(), args.chapter, args.max_chars)
            print(rendered if args.command == "context" else json.dumps({"valid": True, "characters": len(rendered)}, ensure_ascii=False), end="\n")
        return 0
    except (ValueError, OSError, yaml.YAMLError) as exc:
        print(f"analysis reference error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
