#!/usr/bin/env python3
"""Manage Codex-native private cross-book assets and their derived graphs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

import yaml

import continuity_store


SCHEMA_VERSION = 1
NAMESPACES = {"reusable", "universe"}
GOVERNANCE = {"author_approval", "codex_delegated"}
LINK_MODES = {"fork", "sync"}
LINK_STATUSES = {"active", "update_available", "conflict", "retired"}
LIBRARY_MANIFEST = "library.yaml"
ASSET_DIR = Path("assets")
GRAPH_DIR = Path("graph")
GRAPH_INDEX = GRAPH_DIR / "asset-graph-index.sqlite3"
WORKSPACE_ASSETS = Path("cross-book-assets")
WORKSPACE_GRAPH = Path("continuity/graph")
WORKSPACE_INDEX = WORKSPACE_GRAPH / "asset-graph-index.sqlite3"
SELECTION_SCHEMA_VERSION = 1
SELECTION_NAME = re.compile(r"^chapter-(\d{3,})\.assets\.yaml$")
CHAPTER_NAME = re.compile(r"^chapter[-_](\d+)$")
EVENT_KIND = "event"
CANON_RELATIONS = {"precedes", "follows"}


def configure_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    os.close(descriptor)
    temporary = Path(name)
    try:
        temporary.write_text(text, encoding="utf-8", newline="\n")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_yaml(path: Path, value: Any) -> None:
    atomic_text(path, yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=1000))


def read_yaml(path: Path) -> Any:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ValueError(f"invalid YAML in {path}: {error}") from error
    return {} if value is None else value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def asset_hash(asset: dict[str, Any]) -> str:
    stable = {key: value for key, value in asset.items() if key not in {"content_sha256", "updated_at"}}
    encoded = yaml.safe_dump(stable, allow_unicode=True, sort_keys=True, width=1000).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def library_paths(library: Path) -> dict[str, Path]:
    return {
        "manifest": library / LIBRARY_MANIFEST,
        "assets": library / ASSET_DIR,
        "nodes": library / GRAPH_DIR / "nodes.jsonl",
        "edges": library / GRAPH_DIR / "edges.jsonl",
        "index": library / GRAPH_INDEX,
    }


def init_library(library: Path) -> dict[str, Any]:
    paths = library_paths(library)
    if paths["manifest"].exists():
        raise ValueError("library already initialized")
    if library.exists() and any(library.iterdir()):
        raise ValueError("library directory is not empty")
    paths["assets"].mkdir(parents=True, exist_ok=True)
    (library / GRAPH_DIR).mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "library_id": library.name,
        "visibility": "private",
        "creative_engine": "codex",
        "universe_id": library.name,
        "universe_governance": "author_approval",
        "revision": 1,
        "created_at": utc_now(),
    }
    write_yaml(paths["manifest"], manifest)
    return {"initialized": str(library), "manifest": manifest}


def load_manifest(library: Path) -> dict[str, Any]:
    path = library_paths(library)["manifest"]
    if not path.is_file():
        raise ValueError("library is not initialized; run init first")
    manifest = read_yaml(path)
    if not isinstance(manifest, dict) or manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("library.yaml has unsupported schema_version")
    if not isinstance(manifest.get("revision"), int) or manifest["revision"] < 1:
        raise ValueError("library.yaml revision must be a positive integer")
    universe_id = manifest.setdefault("universe_id", manifest.get("library_id"))
    if not isinstance(universe_id, str) or not universe_id.strip() or any(token in universe_id for token in ("/", "\\", "..")):
        raise ValueError("library.yaml universe_id must be a stable id")
    universe_governance = manifest.setdefault("universe_governance", "author_approval")
    if universe_governance not in GOVERNANCE:
        raise ValueError("library.yaml universe_governance is invalid")
    return manifest


def asset_path(library: Path, asset_id: str) -> Path:
    if not asset_id or any(token in asset_id for token in ("/", "\\", "..")):
        raise ValueError("asset id must be a stable filename-safe id")
    return library_paths(library)["assets"] / f"{asset_id}.yaml"


def validate_asset(asset: Any, *, existing_ids: set[str] | None = None, published: bool = False) -> list[str]:
    if not isinstance(asset, dict):
        return ["asset must be a YAML mapping"]
    errors: list[str] = []
    for key in ("id", "namespace", "kind", "title", "summary", "version", "status", "governance", "visibility", "source", "content"):
        if key not in asset:
            errors.append(f"asset missing {key}")
    asset_id = asset.get("id")
    if not isinstance(asset_id, str) or not asset_id.strip() or any(token in asset_id for token in ("/", "\\", "..")):
        errors.append("asset id must be a stable filename-safe id")
    if asset.get("namespace") not in NAMESPACES:
        errors.append("asset namespace must be reusable or universe")
    if asset.get("governance") not in GOVERNANCE:
        errors.append("asset governance must be author_approval or codex_delegated")
    if asset.get("visibility") != "private":
        errors.append("asset visibility must be private in the local library")
    valid_statuses = {"active", "retired"} if published else {"active"}
    if asset.get("status") not in valid_statuses:
        errors.append("only active assets may be published" if not published else "published asset status must be active or retired")
    if not isinstance(asset.get("version"), int) or asset.get("version", 0) < 1:
        errors.append("asset version must be a positive integer")
    if not isinstance(asset.get("content"), dict):
        errors.append("asset content must be a mapping")
    if published:
        if not isinstance(asset.get("content_sha256"), str) or asset.get("content_sha256") != asset_hash(asset):
            errors.append("published asset content_sha256 does not match its content")
        if not str(asset.get("updated_at", "")).strip():
            errors.append("published asset missing updated_at")
    source = asset.get("source")
    if not isinstance(source, dict):
        errors.append("asset source must be a mapping")
    else:
        for key in ("workspace", "artifact", "chapter", "artifact_sha256", "evidence"):
            if not str(source.get(key, "")).strip():
                errors.append(f"asset source missing {key}")
        if not isinstance(source.get("artifact_sha256"), str) or not re.fullmatch(r"[0-9a-fA-F]{64}", source["artifact_sha256"]):
            errors.append("asset source artifact_sha256 must be a SHA-256 fingerprint")
        if source.get("accepted") is not True:
            errors.append("asset source must be accepted")
    relationships = asset.get("relationships", [])
    if not isinstance(relationships, list):
        errors.append("asset relationships must be a list")
    else:
        for position, relation in enumerate(relationships, 1):
            if not isinstance(relation, dict):
                errors.append(f"relationship[{position}] must be a mapping")
                continue
            for key in ("target", "relation", "evidence", "confidence"):
                if not str(relation.get(key, "")).strip():
                    errors.append(f"relationship[{position}] missing {key}")
            if not isinstance(relation.get("confidence"), (int, float)) or not 0 <= relation["confidence"] <= 1:
                errors.append(f"relationship[{position}] confidence must be between 0 and 1")
            target = relation.get("target")
            if existing_ids is not None and target not in existing_ids | {asset_id}:
                errors.append(f"relationship[{position}] references missing asset {target}")
    return errors


def canon_event_errors(asset: dict[str, Any], assets: dict[str, dict[str, Any]], *, candidate: bool = False) -> list[str]:
    if asset.get("namespace") != "universe" or asset.get("kind") != EVENT_KIND:
        return []
    canon = asset.get("content", {}).get("canon") if isinstance(asset.get("content"), dict) else None
    if not isinstance(canon, dict):
        return ["universe event content must include canon mapping"]
    errors: list[str] = []
    source = asset.get("source")
    if not isinstance(source, dict) or source.get("continuity_committed") is not True:
        errors.append("universe event source must declare continuity_committed: true")
    if not isinstance(canon.get("sequence"), int):
        errors.append("universe event canon.sequence must be an integer")
    participants = canon.get("participants")
    if not isinstance(participants, list) or not participants or not all(isinstance(item, str) and item.strip() for item in participants):
        errors.append("universe event canon.participants must be a non-empty list of asset ids")
    if not isinstance(canon.get("effects"), str) or not canon["effects"].strip():
        errors.append("universe event canon.effects must be a non-empty string")
    for key in CANON_RELATIONS:
        values = canon.get(key, [])
        if not isinstance(values, list) or not all(isinstance(item, str) and item.strip() for item in values):
            errors.append(f"universe event canon.{key} must be a list of event ids")
    targets = list(participants or []) + list(canon.get("precedes", []) or []) + list(canon.get("follows", []) or [])
    for target in targets:
        referenced = assets.get(target)
        if referenced is None or (candidate and target == asset.get("id")):
            errors.append(f"universe event references unpublished asset {target}")
            continue
        if referenced.get("namespace") != "universe" or referenced.get("status") != "active":
            errors.append(f"universe event references non-active universe asset {target}")
            continue
        if target in canon.get("precedes", []) or target in canon.get("follows", []):
            if referenced.get("kind") != EVENT_KIND:
                errors.append(f"universe event canon relation target is not an event: {target}")
    return errors


def load_assets(library: Path) -> dict[str, dict[str, Any]]:
    load_manifest(library)
    assets: dict[str, dict[str, Any]] = {}
    for path in sorted(library_paths(library)["assets"].glob("*.yaml")):
        asset = read_yaml(path)
        if not isinstance(asset, dict):
            raise ValueError(f"{path.name} must be a mapping")
        asset_id = asset.get("id")
        if not isinstance(asset_id, str) or not asset_id:
            raise ValueError(f"{path.name} missing asset id")
        if asset_id in assets:
            raise ValueError(f"duplicate asset id {asset_id}")
        assets[asset_id] = asset
    errors = [error for asset in assets.values() for error in validate_asset(asset, existing_ids=set(assets), published=True)]
    errors.extend(error for asset in assets.values() for error in canon_event_errors(asset, assets))
    if errors:
        raise ValueError("invalid library assets: " + "; ".join(errors))
    return assets


def save_manifest(library: Path, manifest: dict[str, Any]) -> None:
    manifest["updated_at"] = utc_now()
    write_yaml(library_paths(library)["manifest"], manifest)


def publish_asset(library: Path, candidate: Path, author_approved: bool, source_workspace: Path | None = None) -> dict[str, Any]:
    if source_workspace is not None:
        verify_candidate_source(source_workspace, candidate)
    manifest = load_manifest(library)
    assets = load_assets(library)
    asset = read_yaml(candidate)
    if not isinstance(asset, dict):
        raise ValueError("candidate asset must be a mapping")
    errors = validate_asset(asset, existing_ids=set(assets) | {str(asset.get("id", ""))})
    if isinstance(asset, dict):
        errors.extend(canon_event_errors(asset, assets, candidate=True))
        proposed = dict(assets)
        proposed[str(asset.get("id", ""))] = asset
        errors.extend(canon_topology_errors(proposed))
    if errors:
        raise ValueError("invalid candidate: " + "; ".join(errors))
    delegated = asset["governance"] == "codex_delegated" or (
        asset["namespace"] == "universe" and manifest["universe_governance"] == "codex_delegated"
    )
    if not author_approved and not delegated:
        raise ValueError("author-approved assets require --author-approved")
    current = assets.get(asset["id"])
    asset["version"] = (current.get("version", 0) if current else 0) + 1
    asset["content_sha256"] = asset_hash(asset)
    asset["updated_at"] = utc_now()
    write_yaml(asset_path(library, asset["id"]), asset)
    manifest["revision"] += 1
    save_manifest(library, manifest)
    return {"published": asset["id"], "version": asset["version"], "hash": asset["content_sha256"]}


def set_delegation(library: Path, asset_id: str, enabled: bool) -> dict[str, Any]:
    manifest = load_manifest(library)
    asset = load_assets(library).get(asset_id)
    if asset is None:
        raise ValueError(f"asset not found: {asset_id}")
    asset["governance"] = "codex_delegated" if enabled else "author_approval"
    asset["version"] += 1
    asset["content_sha256"] = asset_hash(asset)
    asset["updated_at"] = utc_now()
    write_yaml(asset_path(library, asset_id), asset)
    manifest["revision"] += 1
    save_manifest(library, manifest)
    return {"asset": asset_id, "governance": asset["governance"], "version": asset["version"]}


def set_universe_delegation(library: Path, enabled: bool) -> dict[str, Any]:
    manifest = load_manifest(library)
    manifest["universe_governance"] = "codex_delegated" if enabled else "author_approval"
    manifest["revision"] += 1
    save_manifest(library, manifest)
    return {"universe_id": manifest["universe_id"], "governance": manifest["universe_governance"], "revision": manifest["revision"]}


def require_v3_workspace(workspace: Path) -> dict[str, Any]:
    state_path = workspace / "novel-state.yaml"
    if not state_path.is_file():
        raise ValueError("workspace is missing novel-state.yaml")
    state = read_yaml(state_path)
    if not isinstance(state, dict) or state.get("schema_version") != 3:
        raise ValueError("cross-book assets require schema v3; run novelctl.py migrate first")
    if not (workspace / continuity_store.STORE_RELATIVE).is_dir():
        raise ValueError("cross-book assets require continuity/data; migrate structured continuity first")
    return state


def asset_links_path(workspace: Path) -> Path:
    return workspace / continuity_store.STORE_RELATIVE / "asset-links.yaml"


def ensure_asset_links(workspace: Path) -> None:
    path = asset_links_path(workspace)
    if path.is_file():
        return
    write_yaml(path, [])


def read_links(workspace: Path, *, create: bool = True) -> list[dict[str, Any]]:
    path = asset_links_path(workspace)
    if not path.is_file():
        if not create:
            return []
        ensure_asset_links(workspace)
    links = read_yaml(path)
    if not isinstance(links, list) or not all(isinstance(item, dict) for item in links):
        raise ValueError("asset-links.yaml must be a YAML list")
    return links


def refresh_continuity_index(workspace: Path) -> None:
    store = continuity_store.load_store(workspace)
    errors = continuity_store.validate_store(workspace, store)
    if errors:
        raise ValueError("invalid continuity store: " + "; ".join(errors))
    continuity_store.build_index(workspace, store)
    continuity_store.update_state_for_store(workspace, store, "current")


def write_links(workspace: Path, links: list[dict[str, Any]]) -> None:
    require_v3_workspace(workspace)
    write_yaml(asset_links_path(workspace), links)
    manifest_path = workspace / continuity_store.STORE_RELATIVE / "manifest.yaml"
    manifest = read_yaml(manifest_path)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("revision"), int):
        raise ValueError("continuity manifest is invalid")
    manifest["revision"] += 1
    manifest["updated_at"] = utc_now()
    write_yaml(manifest_path, manifest)
    refresh_continuity_index(workspace)


def local_asset_path(workspace: Path, asset_id: str) -> Path:
    return workspace / WORKSPACE_ASSETS / f"{asset_id}.yaml"


def workspace_relative(workspace: Path, value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("workspace path must be relative and cannot contain '..'")
    resolved = (workspace / candidate).resolve()
    try:
        resolved.relative_to(workspace.resolve())
    except ValueError as error:
        raise ValueError("workspace path escapes the novel workspace") from error
    return resolved


def default_selection_path(workspace: Path, chapter: int) -> Path:
    if chapter < 1:
        raise ValueError("chapter must be positive")
    return workspace / "context-packages" / f"chapter-{chapter:03d}.assets.yaml"


def selection_chapter(selection_path: Path) -> int:
    matched = SELECTION_NAME.fullmatch(selection_path.name)
    if not matched:
        raise ValueError("asset selection must be named context-packages/chapter-XXX.assets.yaml")
    return int(matched.group(1))


def chapter_number(value: Any) -> int | None:
    matched = CHAPTER_NAME.fullmatch(str(value or ""))
    return int(matched.group(1)) if matched else None


def read_selection(workspace: Path, selection_path: Path) -> dict[str, Any]:
    resolved = selection_path.resolve()
    try:
        relative = resolved.relative_to(workspace.resolve())
    except ValueError as error:
        raise ValueError("asset selection must be inside the novel workspace") from error
    if relative.parent.as_posix() != "context-packages":
        raise ValueError("asset selection must be stored under context-packages/")
    selection_chapter(resolved)
    if not resolved.is_file():
        raise ValueError(f"asset selection is missing: {relative.as_posix()}")
    selection = read_yaml(resolved)
    if not isinstance(selection, dict):
        raise ValueError("asset selection must be a YAML mapping")
    return selection


def validate_asset_selection(workspace: Path, selection_path: Path) -> dict[str, Any]:
    require_v3_workspace(workspace)
    selection = read_selection(workspace, selection_path)
    if selection.get("schema_version") != SELECTION_SCHEMA_VERSION:
        raise ValueError("asset selection has unsupported schema_version")
    chapter = selection_chapter(selection_path)
    declared_chapter = chapter_number(selection.get("chapter"))
    if declared_chapter != chapter:
        raise ValueError("asset selection chapter does not match its filename")
    selected = selection.get("assets")
    if not isinstance(selected, list):
        raise ValueError("asset selection assets must be a YAML list")
    links = {str(link.get("asset_id")): link for link in read_links(workspace)}
    seen: set[str] = set()
    for position, item in enumerate(selected, 1):
        label = f"asset selection assets[{position}]"
        if not isinstance(item, dict):
            raise ValueError(f"{label} must be a mapping")
        for key in ("asset_id", "purpose", "constraints", "mode", "library_version", "library_hash", "local_path", "local_hash"):
            if item.get(key) in (None, "", []):
                raise ValueError(f"{label} missing {key}")
        if not isinstance(item["purpose"], str) or not item["purpose"].strip():
            raise ValueError(f"{label} purpose must be a non-empty string")
        if not isinstance(item["constraints"], list) or not all(isinstance(value, str) and value.strip() for value in item["constraints"]):
            raise ValueError(f"{label} constraints must be a non-empty list of strings")
        asset_id = str(item["asset_id"])
        if asset_id in seen:
            raise ValueError(f"asset selection repeats asset id: {asset_id}")
        seen.add(asset_id)
        link = links.get(asset_id)
        if link is None:
            raise ValueError(f"asset selection references an unimported asset: {asset_id}")
        if link.get("status") == "conflict":
            raise ValueError(f"asset selection is blocked by sync conflict: {asset_id}")
        if link.get("status") not in {"active", "update_available"}:
            raise ValueError(f"asset selection references a non-active asset: {asset_id}")
        for key in ("mode", "library_version", "library_hash", "local_path", "local_hash"):
            if item.get(key) != link.get(key):
                raise ValueError(f"asset selection {asset_id} has stale {key}")
        local = workspace_relative(workspace, str(link["local_path"]))
        if not local.is_file() or sha256(local) != link["local_hash"]:
            raise ValueError(f"asset selection local snapshot changed or is missing: {asset_id}")
        snapshot = read_yaml(local)
        if not isinstance(snapshot, dict) or snapshot.get("id") != asset_id:
            raise ValueError(f"asset selection local snapshot is invalid: {asset_id}")
        if snapshot.get("content_sha256") != link["library_hash"]:
            raise ValueError(f"asset selection local snapshot hash is invalid: {asset_id}")
    return selection


def validate_selection_with_library(library: Path, workspace: Path, selection_path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    selection = validate_asset_selection(workspace, selection_path)
    assets = load_assets(library)
    for item in selection["assets"]:
        asset_id = str(item["asset_id"])
        if asset_id not in assets:
            raise ValueError(f"asset selection library asset is missing: {asset_id}")
    return selection, assets


def render_selection_context(library: Path, workspace: Path, selection_path: Path, max_chars: int) -> str:
    if max_chars < 1:
        raise ValueError("asset context budget must be positive")
    selection, assets = validate_selection_with_library(library, workspace, selection_path)
    links = {str(link["asset_id"]): link for link in read_links(workspace)}
    selected_ids = {str(item["asset_id"]) for item in selection["assets"]}
    lines = ["## 跨书资产：已锁定快照", "", "仅列出候选与权威回读路径；不得将图谱摘要直接当作事实。"]
    for item in selection["assets"]:
        asset_id = str(item["asset_id"])
        link = links[asset_id]
        update = "；共享库有新版本，本章仍固定使用本书快照" if link["status"] == "update_available" else ""
        item_lines = [
            f"- `{asset_id}`｜{item['purpose']}",
            f"  - 约束：{'; '.join(str(value) for value in item['constraints'])}",
            f"  - 固定版本：v{item['library_version']} / {item['mode']} / {item['library_hash']}",
            f"  - 必须回读：`{item['local_path']}`{update}",
        ]
        if len("\n".join(lines + item_lines)) > max_chars:
            break
        lines.extend(item_lines)
    neighbor_lines: list[str] = []
    for asset_id in sorted(selected_ids):
        for relation in assets[asset_id].get("relationships", []):
            target = str(relation["target"])
            if target in selected_ids or target not in assets:
                continue
            neighbor_lines.append(f"- 图谱候选 `{target}`：{relation['relation']}；仅可建议导入，未选中不得作为本章事实。")
    if neighbor_lines and len("\n".join(lines + ["", "### 图谱邻域候选"] + neighbor_lines)) <= max_chars:
        lines.extend(["", "### 图谱邻域候选", *neighbor_lines])
    return ("\n".join(lines) + "\n")[:max_chars]


def verify_candidate_source(workspace: Path, candidate_path: Path) -> dict[str, Any]:
    require_v3_workspace(workspace)
    resolved = candidate_path.resolve()
    staging_root = (workspace / "production" / "asset-candidates").resolve()
    try:
        resolved.relative_to(staging_root)
    except ValueError as error:
        raise ValueError("asset candidate must be stored under production/asset-candidates/") from error
    asset = read_yaml(resolved)
    if not isinstance(asset, dict):
        raise ValueError("asset candidate must be a YAML mapping")
    errors = validate_asset(asset)
    if errors:
        raise ValueError("invalid candidate: " + "; ".join(errors))
    source = asset["source"]
    if source.get("continuity_committed") is not True:
        raise ValueError("asset candidate source must declare continuity_committed: true")
    source_chapter = chapter_number(source.get("chapter"))
    store = continuity_store.load_store(workspace)
    committed_chapter = chapter_number(store["manifest"].get("last_committed_chapter"))
    if source_chapter is None or committed_chapter is None or source_chapter > committed_chapter:
        raise ValueError("asset candidate source chapter is not committed")
    expected_stage = f"chapter-{source_chapter:03d}"
    if resolved.parent.name != expected_stage:
        raise ValueError("asset candidate staging directory must match its source chapter")
    artifact = workspace_relative(workspace, str(source["artifact"]))
    expected_chapter_dir = Path("chapters") / expected_stage
    try:
        artifact.relative_to(workspace / expected_chapter_dir)
    except ValueError as error:
        raise ValueError("asset candidate source artifact must belong to its source chapter") from error
    if not artifact.is_file() or sha256(artifact) != source["artifact_sha256"]:
        raise ValueError("asset candidate source artifact changed or is missing")
    return {"valid": True, "asset_id": asset["id"], "source_chapter": source["chapter"], "source_artifact": source["artifact"]}


def make_link(asset: dict[str, Any], mode: str, local: Path, workspace: Path) -> dict[str, Any]:
    return {
        "id": f"LINK-{asset['id']}",
        "asset_id": asset["id"],
        "namespace": asset["namespace"],
        "mode": mode,
        "library_version": asset["version"],
        "library_hash": asset["content_sha256"],
        "local_path": local.relative_to(workspace).as_posix(),
        "local_hash": sha256(local),
        "status": "active",
        "updated_at": utc_now(),
    }


def import_asset(library: Path, workspace: Path, asset_id: str, mode: str) -> dict[str, Any]:
    if mode not in LINK_MODES:
        raise ValueError("mode must be fork or sync")
    require_v3_workspace(workspace)
    asset = load_assets(library).get(asset_id)
    if asset is None:
        raise ValueError(f"asset not found: {asset_id}")
    if asset.get("status") != "active":
        raise ValueError(f"only active assets may be imported: {asset_id}")
    links = read_links(workspace)
    if any(link.get("asset_id") == asset_id and link.get("status") != "retired" for link in links):
        raise ValueError(f"asset already imported: {asset_id}")
    local = local_asset_path(workspace, asset_id)
    local.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(asset_path(library, asset_id), local)
    links.append(make_link(asset, mode, local, workspace))
    write_links(workspace, links)
    return {"imported": asset_id, "mode": mode, "local_path": str(local)}


def find_link(links: list[dict[str, Any]], asset_id: str) -> dict[str, Any]:
    for link in links:
        if link.get("asset_id") == asset_id:
            return link
    raise ValueError(f"asset link not found: {asset_id}")


def reconcile(library: Path, workspace: Path) -> dict[str, Any]:
    require_v3_workspace(workspace)
    assets = load_assets(library)
    links = read_links(workspace)
    changed = False
    report: list[dict[str, Any]] = []
    for link in links:
        if link.get("mode") != "sync" or link.get("status") == "retired":
            continue
        local = workspace / str(link.get("local_path", ""))
        asset = assets.get(str(link.get("asset_id", "")))
        previous = link.get("status")
        if asset is None or not local.is_file() or sha256(local) != link.get("local_hash"):
            link["status"] = "conflict"
        elif asset.get("content_sha256") != link.get("library_hash"):
            link["status"] = "update_available"
        else:
            link["status"] = "active"
        if link["status"] != previous:
            link["updated_at"] = utc_now()
            changed = True
        report.append({"asset_id": link.get("asset_id"), "status": link["status"]})
    if changed:
        write_links(workspace, links)
    return {"links": report, "changed": changed}


def resolve(library: Path, workspace: Path, asset_id: str, action: str, author_approved: bool) -> dict[str, Any]:
    require_v3_workspace(workspace)
    assets = load_assets(library)
    links = read_links(workspace)
    link = find_link(links, asset_id)
    local = workspace / str(link["local_path"])
    if not local.is_file():
        raise ValueError("local imported asset is missing")
    current_local_hash = sha256(local)
    asset = assets.get(asset_id)
    if action == "keep-local":
        link.update({"mode": "fork", "local_hash": current_local_hash, "status": "active", "updated_at": utc_now()})
    elif action == "adopt-shared":
        if asset is None:
            raise ValueError("shared asset is missing")
        if current_local_hash != link.get("local_hash"):
            raise ValueError("local asset changed; keep-local or publish-local explicitly")
        shutil.copy2(asset_path(library, asset_id), local)
        link.update({"mode": "sync", "library_version": asset["version"], "library_hash": asset["content_sha256"], "local_hash": sha256(local), "status": "active", "updated_at": utc_now()})
    elif action == "publish-local":
        candidate = read_yaml(local)
        if not isinstance(candidate, dict):
            raise ValueError("local imported asset must be a mapping")
        if asset is not None and asset.get("governance") == "author_approval" and not author_approved:
            raise ValueError("publishing to shared canon requires --author-approved or a Codex delegation")
        result = publish_asset(library, local, author_approved=author_approved or bool(asset and asset.get("governance") == "codex_delegated"))
        published = load_assets(library)[asset_id]
        shutil.copy2(asset_path(library, asset_id), local)
        link.update({"mode": "sync", "library_version": published["version"], "library_hash": published["content_sha256"], "local_hash": sha256(local), "status": "active", "updated_at": utc_now()})
        write_links(workspace, links)
        return {"resolved": asset_id, "action": action, **result}
    else:
        raise ValueError("action must be keep-local, adopt-shared, or publish-local")
    write_links(workspace, links)
    return {"resolved": asset_id, "action": action, "status": link["status"]}


def universe_events(assets: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        asset_id: asset
        for asset_id, asset in assets.items()
        if asset.get("namespace") == "universe" and asset.get("kind") == EVENT_KIND and asset.get("status") == "active"
    }


def canon_precedence(events: dict[str, dict[str, Any]]) -> list[tuple[str, str]]:
    edges: list[tuple[str, str]] = []
    for event_id, event in events.items():
        canon = event["content"]["canon"]
        edges.extend((event_id, target) for target in canon.get("precedes", []))
        edges.extend((target, event_id) for target in canon.get("follows", []))
    return edges


def canon_topology_errors(assets: dict[str, dict[str, Any]]) -> list[str]:
    events = universe_events(assets)
    errors: list[str] = []
    edges = canon_precedence(events)
    for source, target in edges:
        if source not in events or target not in events:
            errors.append(f"canon event relation has missing endpoint: {source} -> {target}")
            continue
        source_sequence = events[source]["content"]["canon"]["sequence"]
        target_sequence = events[target]["content"]["canon"]["sequence"]
        if source_sequence >= target_sequence:
            errors.append(f"canon sequence contradicts precedence: {source} -> {target}")
    adjacency: dict[str, list[str]] = {event_id: [] for event_id in events}
    for source, target in edges:
        if source in adjacency and target in adjacency:
            adjacency[source].append(target)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(event_id: str) -> None:
        if event_id in visiting:
            errors.append(f"canon event precedence cycle includes {event_id}")
            return
        if event_id in visited:
            return
        visiting.add(event_id)
        for target in adjacency[event_id]:
            visit(target)
        visiting.remove(event_id)
        visited.add(event_id)

    for event_id in sorted(events):
        visit(event_id)
    return sorted(set(errors))


def canon_check(library: Path) -> dict[str, Any]:
    manifest = load_manifest(library)
    assets = load_assets(library)
    errors = canon_topology_errors(assets)
    return {"valid": not errors, "universe_id": manifest["universe_id"], "events": len(universe_events(assets)), "errors": errors}


def timeline(library: Path) -> dict[str, Any]:
    checked = canon_check(library)
    if not checked["valid"]:
        raise ValueError("invalid canon: " + "; ".join(checked["errors"]))
    assets = load_assets(library)
    records: list[dict[str, Any]] = []
    for event_id, event in universe_events(assets).items():
        canon = event["content"]["canon"]
        records.append({
            "event_id": event_id,
            "sequence": canon["sequence"],
            "title": event["title"],
            "participants": canon["participants"],
            "effects": canon["effects"],
            "precedes": canon.get("precedes", []),
            "follows": canon.get("follows", []),
            "version": event["version"],
            "source": event["source"],
        })
    return {"universe_id": checked["universe_id"], "events": sorted(records, key=lambda item: (item["sequence"], item["event_id"]))}


def candidate_for_review(library: Path, candidate_path: Path, source_workspace: Path | None = None) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    if source_workspace is not None:
        verify_candidate_source(source_workspace, candidate_path)
    assets = load_assets(library)
    candidate = read_yaml(candidate_path)
    if not isinstance(candidate, dict):
        raise ValueError("candidate asset must be a mapping")
    errors = validate_asset(candidate, existing_ids=set(assets) | {str(candidate.get("id", ""))})
    errors.extend(canon_event_errors(candidate, assets, candidate=True))
    proposed = dict(assets)
    proposed[str(candidate.get("id", ""))] = candidate
    errors.extend(canon_topology_errors(proposed))
    if errors:
        raise ValueError("invalid candidate: " + "; ".join(errors))
    return candidate, assets


def candidate_impact(library: Path, candidate_path: Path, workspaces: list[Path], source_workspace: Path | None = None) -> dict[str, Any]:
    candidate, assets = candidate_for_review(library, candidate_path, source_workspace)
    changed_ids = {str(candidate["id"])}
    current = assets.get(str(candidate["id"]))
    event_references: set[str] = set()
    for event in (candidate, current):
        if isinstance(event, dict) and event.get("namespace") == "universe" and event.get("kind") == EVENT_KIND:
            canon = event.get("content", {}).get("canon", {})
            if isinstance(canon, dict):
                event_references.update(str(item) for item in canon.get("participants", []))
                event_references.update(str(item) for item in canon.get("precedes", []))
                event_references.update(str(item) for item in canon.get("follows", []))
    affected_ids = changed_ids | event_references
    impacted_events: list[dict[str, Any]] = []
    for event_id, event in universe_events(assets).items():
        canon = event["content"]["canon"]
        references = {event_id, *canon.get("participants", []), *canon.get("precedes", []), *canon.get("follows", [])}
        if changed_ids & references or event_references & {event_id}:
            impacted_events.append({"event_id": event_id, "sequence": canon["sequence"], "reason": "direct canonical reference"})
    worktree_reports: list[dict[str, Any]] = []
    for workspace in workspaces:
        resolved = workspace.resolve()
        require_v3_workspace(resolved)
        links = read_links(resolved, create=False)
        impacted_links = [
            {"asset_id": link.get("asset_id"), "mode": link.get("mode"), "status": link.get("status")}
            for link in links if link.get("asset_id") in affected_ids
        ]
        selections: list[dict[str, Any]] = []
        selection_root = resolved / "context-packages"
        selection_paths = sorted(selection_root.glob("chapter-*.assets.yaml")) if selection_root.is_dir() else []
        for path in selection_paths:
            value = read_yaml(path)
            chosen = value.get("assets", []) if isinstance(value, dict) else []
            selected_ids = [item.get("asset_id") for item in chosen if isinstance(item, dict)]
            matching = sorted(str(item) for item in selected_ids if item in affected_ids)
            if matching:
                selections.append({"path": path.relative_to(resolved).as_posix(), "assets": matching, "risk": "requires_canon_review"})
        if impacted_links or selections:
            worktree_reports.append({"workspace": str(resolved), "links": impacted_links, "chapter_selections": selections})
    return {
        "candidate": candidate["id"],
        "review_required": bool(worktree_reports or impacted_events or event_references),
        "timeline_events": sorted(impacted_events, key=lambda item: (item["sequence"], item["event_id"])),
        "workspaces": worktree_reports,
        "writes": False,
    }


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    atomic_text(path, "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSONL at {path}:{number}: {error.msg}") from error
        if not isinstance(value, dict):
            raise ValueError(f"JSONL record at {path}:{number} must be an object")
        records.append(value)
    return records


def build_sqlite(nodes: list[dict[str, Any]], edges: list[dict[str, Any]], index: Path) -> dict[str, Any]:
    ids = {node.get("id") for node in nodes}
    if len(ids) != len(nodes) or not all(isinstance(item, str) and item for item in ids):
        raise ValueError("graph nodes need unique stable ids")
    for node in nodes:
        for key in ("id", "type", "label", "version", "status", "source_refs"):
            if node.get(key) in (None, "", []):
                raise ValueError(f"graph node missing {key}")
    for edge in edges:
        for key in ("id", "source", "target", "relation", "evidence", "version", "confidence", "status", "source_refs"):
            if not str(edge.get(key, "")).strip():
                raise ValueError(f"graph edge missing {key}")
        if not isinstance(edge["confidence"], (int, float)) or not 0 <= edge["confidence"] <= 1:
            raise ValueError("graph edge confidence must be between 0 and 1")
        if edge["source"] not in ids or edge["target"] not in ids:
            raise ValueError("graph edge references a missing endpoint")
    index.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".asset-graph-", suffix=".sqlite3", dir=index.parent)
    os.close(descriptor)
    temporary = Path(name)
    try:
        connection = sqlite3.connect(temporary)
        try:
            connection.executescript("""
                CREATE TABLE nodes (node_id TEXT PRIMARY KEY, type TEXT NOT NULL, label TEXT NOT NULL, payload_json TEXT NOT NULL);
                CREATE TABLE edges (edge_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, target_id TEXT NOT NULL, relation TEXT NOT NULL, status TEXT NOT NULL, payload_json TEXT NOT NULL);
                CREATE INDEX edges_source ON edges(source_id);
                CREATE INDEX edges_target ON edges(target_id);
            """)
            connection.executemany("INSERT INTO nodes VALUES (?, ?, ?, ?)", [(node["id"], str(node.get("type", "asset")), str(node.get("label", node["id"])), json.dumps(node, ensure_ascii=False)) for node in nodes])
            connection.executemany("INSERT INTO edges VALUES (?, ?, ?, ?, ?, ?)", [(edge["id"], edge["source"], edge["target"], edge["relation"], edge["status"], json.dumps(edge, ensure_ascii=False)) for edge in edges])
            connection.commit()
        finally:
            connection.close()
        os.replace(temporary, index)
    finally:
        if temporary.exists():
            temporary.unlink()
    return {"nodes": len(nodes), "edges": len(edges), "index": str(index)}


def build_library_graph(library: Path) -> dict[str, Any]:
    assets = load_assets(library)
    paths = library_paths(library)
    nodes = [{"id": asset["id"], "type": asset["kind"], "label": asset["title"], "namespace": asset["namespace"], "version": asset["version"], "status": asset["status"], "source_refs": [asset["source"]]} for asset in assets.values()]
    edges: list[dict[str, Any]] = []
    for asset in assets.values():
        for position, relation in enumerate(asset.get("relationships", []), 1):
            edges.append({"id": f"EDGE-{asset['id']}-{position}", "source": asset["id"], "target": relation["target"], "relation": relation["relation"], "evidence": relation["evidence"], "source_refs": [asset["source"]], "confidence": relation["confidence"], "status": "active", "version": asset["version"]})
        if asset.get("namespace") == "universe" and asset.get("kind") == EVENT_KIND and asset.get("status") == "active":
            canon = asset["content"]["canon"]
            evidence = str(asset["source"].get("evidence", ""))
            for position, target in enumerate(canon["participants"], 1):
                edges.append({"id": f"EDGE-CANON-{asset['id']}-PARTICIPANT-{position}", "source": asset["id"], "target": target, "relation": "involves", "evidence": evidence, "source_refs": [asset["source"]], "confidence": 1.0, "status": "active", "version": asset["version"]})
            for position, target in enumerate(canon.get("precedes", []), 1):
                edges.append({"id": f"EDGE-CANON-{asset['id']}-PRECEDES-{position}", "source": asset["id"], "target": target, "relation": "precedes", "evidence": evidence, "source_refs": [asset["source"]], "confidence": 1.0, "status": "active", "version": asset["version"]})
            for position, target in enumerate(canon.get("follows", []), 1):
                edges.append({"id": f"EDGE-CANON-{asset['id']}-FOLLOWS-{position}", "source": target, "target": asset["id"], "relation": "precedes", "evidence": evidence, "source_refs": [asset["source"]], "confidence": 1.0, "status": "active", "version": asset["version"]})
    write_jsonl(paths["nodes"], nodes)
    write_jsonl(paths["edges"], edges)
    return build_sqlite(nodes, edges, paths["index"])


def build_workspace_graph(library: Path, workspace: Path) -> dict[str, Any]:
    require_v3_workspace(workspace)
    assets = load_assets(library)
    store = continuity_store.load_store(workspace)
    errors = continuity_store.validate_store(workspace, store)
    if errors:
        raise ValueError("invalid continuity store: " + "; ".join(errors))
    revision = store["manifest"]["revision"]
    nodes: list[dict[str, Any]] = []
    for domain in ("facts", "payoffs", "resources", "characters", "relationships"):
        for entry in store[domain]:
            nodes.append({"id": f"BOOK:{entry['id']}", "type": domain, "label": entry.get("summary") or entry.get("name") or entry["id"], "version": revision, "status": entry.get("status", "active"), "source_refs": [entry.get("evidence", {})]})
    edges: list[dict[str, Any]] = []
    for link in store["asset_links"]:
        asset = assets.get(link.get("asset_id"))
        if asset is None:
            continue
        node_id = f"LIB:{asset['id']}"
        nodes.append({"id": node_id, "type": asset["kind"], "label": asset["title"], "namespace": asset["namespace"], "version": asset["version"], "status": link["status"], "source_refs": [asset["source"]]})
        edges.append({"id": f"EDGE-{link['id']}", "source": f"BOOK:{link['id']}", "target": node_id, "relation": "imports", "evidence": link["local_path"], "source_refs": [asset["source"]], "version": link["library_version"], "confidence": 1.0, "status": link["status"]})
        nodes.append({"id": f"BOOK:{link['id']}", "type": "asset_link", "label": link["asset_id"], "version": revision, "status": link["status"], "source_refs": [link["local_path"]]})
    for relation in store["relationships"]:
        edges.append({"id": f"EDGE-{relation['id']}", "source": f"BOOK:{relation['character_a']}", "target": f"BOOK:{relation['character_b']}", "relation": "related_to", "evidence": str(relation.get("constraints", relation["id"])), "source_refs": [relation.get("evidence", {})], "version": revision, "confidence": 1.0, "status": "active"})
    node_ids = {node["id"] for node in nodes}
    edges = [edge for edge in edges if edge["source"] in node_ids and edge["target"] in node_ids]
    nodes_path = workspace / WORKSPACE_GRAPH / "nodes.jsonl"
    edges_path = workspace / WORKSPACE_GRAPH / "edges.jsonl"
    write_jsonl(nodes_path, nodes)
    write_jsonl(edges_path, edges)
    return build_sqlite(nodes, edges, workspace / WORKSPACE_INDEX)


def graph_neighbors(graph_root: Path, node: str, depth: int) -> dict[str, Any]:
    nodes = read_jsonl(graph_root / "nodes.jsonl")
    edges = read_jsonl(graph_root / "edges.jsonl")
    by_id = {record.get("id"): record for record in nodes}
    if node not in by_id:
        raise ValueError(f"graph node not found: {node}")
    visited = {node}
    pending = deque([(node, 0)])
    selected: list[dict[str, Any]] = []
    while pending:
        current, distance = pending.popleft()
        if distance >= depth:
            continue
        for edge in edges:
            if edge.get("source") == current:
                selected.append(edge)
                target = edge.get("target")
            elif edge.get("target") == current:
                selected.append(edge)
                target = edge.get("source")
            else:
                continue
            if isinstance(target, str) and target not in visited:
                visited.add(target)
                pending.append((target, distance + 1))
    return {"nodes": [by_id[item] for item in sorted(visited)], "edges": selected}


def context_candidates(library: Path, workspace: Path, asset_ids: list[str], depth: int, max_chars: int) -> str:
    require_v3_workspace(workspace)
    assets = load_assets(library)
    links = {link.get("asset_id"): link for link in read_links(workspace) if link.get("status") == "active"}
    selected: set[str] = set()
    for asset_id in asset_ids:
        if asset_id not in links:
            raise ValueError(f"active asset link not found: {asset_id}")
        selected.add(asset_id)
    if not selected:
        return "# 跨书资产候选\n\n- 当前章节未选择跨书资产。\n"
    adjacency: dict[str, set[str]] = {}
    for asset in assets.values():
        for relation in asset.get("relationships", []):
            adjacency.setdefault(asset["id"], set()).add(relation["target"])
    queue = deque((asset_id, 0) for asset_id in selected)
    while queue:
        current, distance = queue.popleft()
        if distance >= depth:
            continue
        for target in adjacency.get(current, set()):
            if target in assets and target not in selected:
                selected.add(target)
                queue.append((target, distance + 1))
    lines = ["# 跨书资产候选", "", "图谱只提供候选；使用前必须回读本书本地副本和资产库权威 YAML。", ""]
    for asset_id in sorted(selected):
        asset = assets[asset_id]
        line = f"- `{asset_id}`｜{asset['namespace']} / {asset['kind']}｜{asset['title']}：{asset['summary']}"
        if len("\n".join(lines + [line])) > max_chars:
            break
        lines.append(line)
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage private Codex-native cross-book assets and derived graphs.")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="initialize a private asset library")
    init.add_argument("library", type=Path)
    validate = commands.add_parser("validate", help="validate assets and library metadata")
    validate.add_argument("library", type=Path)
    publish = commands.add_parser("publish", help="publish one accepted asset candidate")
    publish.add_argument("library", type=Path)
    publish.add_argument("candidate", type=Path)
    publish.add_argument("--author-approved", action="store_true")
    publish.add_argument("--source-workspace", type=Path, help="verify a staged post-commit candidate against this workspace")
    delegate = commands.add_parser("delegate", help="delegate or revoke Codex publication for one asset")
    delegate.add_argument("library", type=Path)
    delegate.add_argument("asset_id")
    delegate.add_argument("--enabled", action="store_true")
    universe_delegate = commands.add_parser("delegate-universe", help="delegate or revoke Codex canon publication for this universe")
    universe_delegate.add_argument("library", type=Path)
    universe_delegate.add_argument("--enabled", action="store_true")
    timeline_command = commands.add_parser("timeline", help="show the validated shared-universe canon timeline")
    timeline_command.add_argument("library", type=Path)
    canon_check_command = commands.add_parser("canon-check", help="validate shared-universe canon event ordering and endpoints")
    canon_check_command.add_argument("library", type=Path)
    impact_command = commands.add_parser("impact", help="report the explicit workspaces affected by a candidate without writing")
    impact_command.add_argument("library", type=Path)
    impact_command.add_argument("candidate", type=Path)
    impact_command.add_argument("--workspace", type=Path, action="append", required=True, help="schema-v3 workspace to inspect; repeat for each workspace")
    impact_command.add_argument("--source-workspace", type=Path, help="verify a staged post-commit candidate against this workspace")
    imported = commands.add_parser("import", help="import one asset into a schema-v3 novel workspace")
    imported.add_argument("library", type=Path)
    imported.add_argument("workspace", type=Path)
    imported.add_argument("asset_id")
    imported.add_argument("--mode", choices=sorted(LINK_MODES), required=True)
    reconcile_command = commands.add_parser("reconcile", help="detect non-destructive sync conflicts")
    reconcile_command.add_argument("library", type=Path)
    reconcile_command.add_argument("workspace", type=Path)
    resolve_command = commands.add_parser("resolve", help="resolve one sync conflict explicitly")
    resolve_command.add_argument("library", type=Path)
    resolve_command.add_argument("workspace", type=Path)
    resolve_command.add_argument("asset_id")
    resolve_command.add_argument("--action", choices=("keep-local", "adopt-shared", "publish-local"), required=True)
    resolve_command.add_argument("--author-approved", action="store_true")
    build = commands.add_parser("build", help="build the library derived graph")
    build.add_argument("library", type=Path)
    workspace_build = commands.add_parser("build-workspace", help="build one workspace derived graph")
    workspace_build.add_argument("library", type=Path)
    workspace_build.add_argument("workspace", type=Path)
    neighbors = commands.add_parser("neighbors", help="show a bounded graph neighborhood")
    neighbors.add_argument("graph_root", type=Path)
    neighbors.add_argument("node")
    neighbors.add_argument("--depth", type=int, default=1)
    context = commands.add_parser("context", help="assemble bounded cross-book asset candidates")
    context.add_argument("library", type=Path)
    context.add_argument("workspace", type=Path)
    context.add_argument("--assets", required=True, help="comma-separated active asset ids")
    context.add_argument("--max-depth", type=int, default=1)
    context.add_argument("--max-chars", type=int, default=4000)
    selection = commands.add_parser("validate-selection", help="validate a chapter asset selection without writing")
    selection.add_argument("library", type=Path)
    selection.add_argument("workspace", type=Path)
    selection.add_argument("selection", type=Path)
    selection_context = commands.add_parser("selection-context", help="render bounded context for one validated selection")
    selection_context.add_argument("library", type=Path)
    selection_context.add_argument("workspace", type=Path)
    selection_context.add_argument("selection", type=Path)
    selection_context.add_argument("--max-chars", type=int, default=2500)
    verify_candidate = commands.add_parser("verify-candidate", help="verify a staged post-commit asset candidate")
    verify_candidate.add_argument("workspace", type=Path)
    verify_candidate.add_argument("candidate", type=Path)
    return parser


def main() -> None:
    configure_utf8_output()
    args = build_parser().parse_args()
    try:
        if args.command == "init":
            result = init_library(args.library.resolve())
        elif args.command == "validate":
            assets = load_assets(args.library.resolve())
            result = {"valid": True, "assets": len(assets)}
        elif args.command == "publish":
            result = publish_asset(args.library.resolve(), args.candidate.resolve(), args.author_approved, args.source_workspace.resolve() if args.source_workspace else None)
        elif args.command == "delegate":
            result = set_delegation(args.library.resolve(), args.asset_id, args.enabled)
        elif args.command == "delegate-universe":
            result = set_universe_delegation(args.library.resolve(), args.enabled)
        elif args.command == "timeline":
            result = timeline(args.library.resolve())
        elif args.command == "canon-check":
            result = canon_check(args.library.resolve())
        elif args.command == "impact":
            result = candidate_impact(args.library.resolve(), args.candidate.resolve(), [workspace.resolve() for workspace in args.workspace], args.source_workspace.resolve() if args.source_workspace else None)
        elif args.command == "import":
            result = import_asset(args.library.resolve(), args.workspace.resolve(), args.asset_id, args.mode)
        elif args.command == "reconcile":
            result = reconcile(args.library.resolve(), args.workspace.resolve())
        elif args.command == "resolve":
            result = resolve(args.library.resolve(), args.workspace.resolve(), args.asset_id, args.action, args.author_approved)
        elif args.command == "build":
            result = build_library_graph(args.library.resolve())
        elif args.command == "build-workspace":
            result = build_workspace_graph(args.library.resolve(), args.workspace.resolve())
        elif args.command == "neighbors":
            if args.depth < 1:
                raise ValueError("graph depth must be at least 1")
            result = graph_neighbors(args.graph_root.resolve(), args.node, args.depth)
        elif args.command == "validate-selection":
            selection, _ = validate_selection_with_library(args.library.resolve(), args.workspace.resolve(), args.selection.resolve())
            result = {"valid": True, "chapter": selection["chapter"], "assets": len(selection["assets"])}
        elif args.command == "selection-context":
            if args.max_chars < 1:
                raise ValueError("asset context max chars must be positive")
            print(render_selection_context(args.library.resolve(), args.workspace.resolve(), args.selection.resolve(), args.max_chars), end="")
            return
        elif args.command == "verify-candidate":
            result = verify_candidate_source(args.workspace.resolve(), args.candidate.resolve())
        else:
            if args.max_depth < 1 or args.max_chars < 500:
                raise ValueError("context depth must be at least 1 and max chars at least 500")
            assets = [item.strip() for item in args.assets.split(",") if item.strip()]
            print(context_candidates(args.library.resolve(), args.workspace.resolve(), assets, args.max_depth, args.max_chars), end="")
            return
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, sqlite3.Error, ValueError, yaml.YAMLError) as error:
        print(f"asset graph failed: {error}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
