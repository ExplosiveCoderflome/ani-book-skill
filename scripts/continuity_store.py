#!/usr/bin/env python3
"""YAML-authoritative continuity store for long-form novel workspaces.

Markdown ledgers and SQLite are generated views.  This module never reads facts
back from SQLite, so removing the index cannot change a novel's continuity.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml


STORE_RELATIVE = Path("continuity/data")
INDEX_RELATIVE = Path("continuity/index.sqlite3")
STORE_VERSION = 1
CHECKPOINT_INTERVAL = 10
DOMAIN_FILES = {
    "facts": "facts.yaml",
    "payoffs": "payoffs.yaml",
    "resources": "resources.yaml",
    "characters": "character-state.yaml",
    "relationships": "relationships.yaml",
}
TABLE_SEPARATOR = re.compile(r"^\|(?:\s*:?-{3,}:?\s*\|)+\s*$")
CHAPTER_PATTERN = re.compile(r"(?:chapter[-_ ]?|第\s*)(\d+)(?:\s*章)?", re.IGNORECASE)


def configure_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def chapter_number(value: Any) -> int | None:
    match = CHAPTER_PATTERN.search(str(value))
    return int(match.group(1)) if match else None


def chapter_label(number: int) -> str:
    return f"chapter-{number:03d}"


def read_yaml(path: Path) -> Any:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ValueError(f"invalid YAML in {path}: {error}") from error
    return {} if value is None else value


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def write_yaml(path: Path, value: Any) -> None:
    atomic_write_text(path, yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=1000))


def parse_markdown_tables(path: Path) -> list[list[dict[str, str]]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    tables: list[list[dict[str, str]]] = []
    for index in range(len(lines) - 1):
        if not lines[index].lstrip().startswith("|") or not TABLE_SEPARATOR.match(lines[index + 1].strip()):
            continue
        headers = [part.strip() for part in lines[index].strip().strip("|").split("|")]
        rows: list[dict[str, str]] = []
        for line in lines[index + 2 :]:
            if not line.lstrip().startswith("|"):
                break
            cells = [part.strip() for part in line.strip().strip("|").split("|")]
            if len(cells) != len(headers):
                raise ValueError(f"{path}: malformed table row: {line}")
            rows.append(dict(zip(headers, cells)))
        tables.append(rows)
    if not tables:
        raise ValueError(f"{path}: no Markdown table found")
    return tables


def parse_markdown_table(path: Path) -> list[dict[str, str]]:
    tables = parse_markdown_tables(path)
    if tables:
        return tables[0]
    raise ValueError(f"{path}: no Markdown table found")


def split_status(value: str) -> tuple[str, str]:
    head, separator, tail = value.partition("；")
    return head.strip() or "unknown", tail.strip() if separator else ""


def split_list(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[、,，]", value) if item.strip() and item.strip() not in {"无", "-"}]


def entry_base(row: dict[str, str], *, summary: str, chapter: str, evidence: str) -> dict[str, Any]:
    number = chapter_number(chapter)
    return {
        "id": row["ID"].strip(),
        "summary": summary.strip(),
        "introduced_in": chapter_label(number) if number else chapter.strip(),
        "updated_in": chapter_label(number) if number else chapter.strip(),
        "evidence": {"text": evidence.strip()},
        "tags": ["migrated"],
    }


def migrate_facts(path: Path) -> list[dict[str, Any]]:
    rows = parse_markdown_table(path)
    entries: list[dict[str, Any]] = []
    for row in rows:
        status, constraints = split_status(row["状态与后续约束"])
        entry = entry_base(row, summary=row["稳定事实"], chapter=row["发生章节"], evidence=row["证据"])
        entry.update({"characters": split_list(row["涉及角色"]), "status": status, "constraints": constraints})
        entries.append(entry)
    return entries


def migrate_payoffs(path: Path) -> list[dict[str, Any]]:
    rows = parse_markdown_table(path)
    entries: list[dict[str, Any]] = []
    for row in rows:
        entry = entry_base(row, summary=row["承诺/伏笔"], chapter=row["首现"], evidence=row["来源"])
        entry.update({
            "target_window": row["目标窗口"].strip(),
            "status": row["当前状态"].strip(),
            "latest_progress": row["最近推进"].strip(),
            "risks_next_window": row["风险与下次窗口"].strip(),
        })
        entries.append(entry)
    return entries


def migrate_resources(path: Path) -> list[dict[str, Any]]:
    rows = parse_markdown_table(path)
    entries: list[dict[str, Any]] = []
    for row in rows:
        entry = entry_base(row, summary=row["资源"], chapter=row["来源"], evidence=row["来源"])
        entry.update({
            "holder": row["持有人/归属"].strip(),
            "visibility_state": row["可见性与状态"].strip(),
            "usage_constraints": row["使用窗口与禁止误用"].strip(),
            "status": "active",
        })
        entries.append(entry)
    return entries


def migrate_characters(workspace: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    roster = workspace / "characters/character-roster.md"
    if not roster.is_file():
        return [], []
    tables = parse_markdown_tables(roster)
    characters: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []
    for rows in tables:
        for row in rows:
            if "ID" in row:
                characters.append({
                    "id": row["ID"].strip(),
                    "name": row.get("姓名/称呼", "").strip(),
                    "current_state": [],
                    "updated_in": "migration",
                    "tags": ["migrated", "roster-reference"],
                })
            elif "角色 A" in row:
                relationships.append({
                    "id": f"REL-{len(relationships) + 1:03d}",
                    "character_a": row["角色 A"].strip(),
                    "character_b": row["角色 B"].strip(),
                    "public_relation": row["公开关系"].strip(),
                    "hidden_binding": row["隐秘绑定"].strip(),
                    "direction": row["当前方向"].strip(),
                    "constraints": row["不可越过边界"].strip(),
                    "updated_in": "migration",
                    "tags": ["migrated"],
                })
    return characters, relationships


def migrate_baseline(path: Path, last_committed: str) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    source = re.search(r"source-hash:\s*([^|]+?)\s*\|\s*([0-9A-Fa-f]{64})", text)
    chapter = re.search(r"基线章节：`([^`]+)`", text)
    bullets = [line[2:].strip() for line in text.splitlines() if line.startswith("- ")]
    return {
        "schema_version": STORE_VERSION,
        "baseline_chapter": chapter.group(1) if chapter else last_committed,
        "source_path": source.group(1).strip() if source else "",
        "source_hash": source.group(2).upper() if source else "",
        "confirmed_state": bullets,
    }


def store_paths(workspace: Path) -> dict[str, Path]:
    root = workspace / STORE_RELATIVE
    return {"root": root, "manifest": root / "manifest.yaml", "baseline": root / "baseline.yaml", **{key: root / name for key, name in DOMAIN_FILES.items()}}


def make_manifest(last_committed: str) -> dict[str, Any]:
    return {
        "schema_version": STORE_VERSION,
        "revision": 1,
        "last_committed_chapter": last_committed,
        "checkpoint_policy": {"interval_chapters": CHECKPOINT_INTERVAL, "at_volume_end": True},
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }


def load_store(workspace: Path) -> dict[str, Any]:
    paths = store_paths(workspace)
    missing = [str(path.relative_to(workspace)) for key, path in paths.items() if key != "root" and not path.is_file()]
    if missing:
        raise ValueError(f"structured continuity store is incomplete: {', '.join(missing)}")
    result = {key: read_yaml(path) for key, path in paths.items() if key != "root"}
    if not isinstance(result["manifest"], dict):
        raise ValueError("manifest.yaml must be a YAML mapping")
    for key in DOMAIN_FILES:
        if not isinstance(result[key], list):
            raise ValueError(f"{DOMAIN_FILES[key]} must be a YAML list")
    if not isinstance(result["baseline"], dict):
        raise ValueError("baseline.yaml must be a YAML mapping")
    return result


def validate_store(workspace: Path, store: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    try:
        store = store or load_store(workspace)
    except ValueError as error:
        return [str(error)]
    manifest = store["manifest"]
    if manifest.get("schema_version") != STORE_VERSION:
        errors.append("manifest.yaml has unsupported schema_version")
    if not isinstance(manifest.get("revision"), int) or manifest["revision"] < 1:
        errors.append("manifest.yaml revision must be a positive integer")
    last_number = chapter_number(manifest.get("last_committed_chapter"))
    if last_number is None:
        errors.append("manifest.yaml last_committed_chapter is invalid")
        last_number = 0
    character_ids = {item.get("id") for item in store["characters"] if isinstance(item, dict)}
    for domain in ("facts", "payoffs", "resources", "characters", "relationships"):
        seen: set[str] = set()
        for position, entry in enumerate(store[domain], 1):
            label = f"{domain}[{position}]"
            if not isinstance(entry, dict):
                errors.append(f"{label} must be a mapping")
                continue
            entry_id = entry.get("id")
            if not isinstance(entry_id, str) or not entry_id.strip():
                errors.append(f"{label} missing stable id")
            elif entry_id in seen:
                errors.append(f"{domain} has duplicate id {entry_id}")
            else:
                seen.add(entry_id)
            if domain in ("facts", "payoffs", "resources"):
                for key in ("summary", "introduced_in", "updated_in", "evidence", "status", "tags"):
                    if key not in entry:
                        errors.append(f"{label} missing {key}")
                entry_chapter = chapter_number(entry.get("introduced_in"))
                if entry_chapter is not None and entry_chapter > last_number:
                    errors.append(f"{label} is beyond last committed chapter")
                if not isinstance(entry.get("evidence"), dict) or not str(entry["evidence"].get("text", "")).strip():
                    errors.append(f"{label} needs evidence.text")
                if not isinstance(entry.get("tags"), list):
                    errors.append(f"{label} tags must be a list")
            if domain == "relationships":
                for key in ("character_a", "character_b", "updated_in", "constraints"):
                    if not str(entry.get(key, "")).strip():
                        errors.append(f"{label} missing {key}")
                for key in ("character_a", "character_b"):
                    if character_ids and entry.get(key) not in character_ids:
                        errors.append(f"{label} references missing character {entry.get(key)}")
    baseline = store["baseline"]
    if not str(baseline.get("baseline_chapter", "")).strip():
        errors.append("baseline.yaml missing baseline_chapter")
    if not isinstance(baseline.get("confirmed_state"), list):
        errors.append("baseline.yaml confirmed_state must be a list")
    return errors


def markdown_table(headers: list[str], rows: Iterable[list[str]]) -> str:
    output = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    output.extend("| " + " | ".join(cell.replace("\n", " ") for cell in row) + " |" for row in rows)
    return "\n".join(output) + "\n"


def generated_header(manifest: dict[str, Any]) -> str:
    return f"<!-- generated-from: continuity/data revision {manifest['revision']}; do not edit this view directly -->\n\n"


def render_views(workspace: Path, store: dict[str, Any] | None = None) -> list[Path]:
    store = store or load_store(workspace)
    errors = validate_store(workspace, store)
    if errors:
        raise ValueError("cannot render invalid store: " + "; ".join(errors))
    manifest = store["manifest"]
    header = generated_header(manifest)
    baseline = store["baseline"]
    baseline_header = ""
    if baseline.get("source_path") and baseline.get("source_hash"):
        baseline_header = f"<!-- source-hash: {baseline['source_path']} | {baseline['source_hash']} -->\n"
    baseline_text = baseline_header + header + "# 连续性基线｜结构化视图\n\n## 基线来源\n\n"
    baseline_text += f"- 基线章节：`{baseline['baseline_chapter']}`\n"
    baseline_text += f"- 最后稳定章节：`{manifest['last_committed_chapter']}`\n\n## 已确认状态\n\n"
    baseline_text += "\n".join(f"- {item}" for item in baseline.get("confirmed_state", [])) + "\n"
    paths = [workspace / "continuity/baseline.md"]
    atomic_write_text(paths[0], baseline_text)
    fact_rows = [[item["id"], item["summary"], item["introduced_in"], item["evidence"]["text"], "、".join(item.get("characters", [])), "；".join(filter(None, [str(item.get("status", "")), str(item.get("constraints", ""))]))] for item in store["facts"]]
    fact_path = workspace / "continuity/fact-ledger.md"
    atomic_write_text(fact_path, header + "# 事实账本\n\n" + markdown_table(["ID", "稳定事实", "发生章节", "证据", "涉及角色", "状态与后续约束"], fact_rows))
    paths.append(fact_path)
    payoff_rows = [[item["id"], item["summary"], item["evidence"]["text"], item["introduced_in"], item.get("target_window", ""), item.get("status", ""), item.get("latest_progress", ""), item.get("risks_next_window", "")] for item in store["payoffs"]]
    payoff_path = workspace / "continuity/payoff-ledger.md"
    atomic_write_text(payoff_path, header + "# 伏笔与承诺账本\n\n" + markdown_table(["ID", "承诺/伏笔", "来源", "首现", "目标窗口", "当前状态", "最近推进", "风险与下次窗口"], payoff_rows))
    paths.append(payoff_path)
    resource_rows = [[item["id"], item["summary"], item.get("holder", ""), item.get("visibility_state", ""), item["introduced_in"], item.get("usage_constraints", "")] for item in store["resources"]]
    resource_path = workspace / "continuity/resource-ledger.md"
    atomic_write_text(resource_path, header + "# 资源账本\n\n" + markdown_table(["ID", "资源", "持有人/归属", "可见性与状态", "来源", "使用窗口与禁止误用"], resource_rows))
    paths.append(resource_path)
    return paths


def checkpoint_path(workspace: Path, chapter: str) -> Path:
    return workspace / STORE_RELATIVE / "checkpoints" / f"checkpoint-{chapter_number(chapter):03d}.yaml"


def create_checkpoint(workspace: Path, chapter: str, reason: str, store: dict[str, Any] | None = None) -> Path:
    store = store or load_store(workspace)
    number = chapter_number(chapter)
    if number is None:
        raise ValueError("checkpoint chapter must be a chapter label or number")
    manifest = copy.deepcopy(store["manifest"])
    payload = {
        "schema_version": STORE_VERSION,
        "chapter": chapter_label(number),
        "reason": reason,
        "revision": manifest["revision"],
        "created_at": utc_now(),
        "snapshot": {key: copy.deepcopy(store[key]) for key in ("manifest", "baseline", *DOMAIN_FILES)},
    }
    path = checkpoint_path(workspace, chapter_label(number))
    write_yaml(path, payload)
    return path


def text_for_entry(domain: str, entry: dict[str, Any]) -> str:
    values = [domain, str(entry.get("id", "")), str(entry.get("summary", "")), str(entry.get("status", ""))]
    for key in ("constraints", "target_window", "latest_progress", "risks_next_window", "holder", "visibility_state", "usage_constraints", "name", "public_relation", "hidden_binding", "direction"):
        if entry.get(key):
            values.append(str(entry[key]))
    evidence = entry.get("evidence")
    if isinstance(evidence, dict):
        values.append(str(evidence.get("text", "")))
    values.extend(str(item) for item in entry.get("tags", []) if item)
    return "\n".join(values)


def build_index(workspace: Path, store: dict[str, Any] | None = None) -> dict[str, Any]:
    store = store or load_store(workspace)
    errors = validate_store(workspace, store)
    if errors:
        raise ValueError("cannot index invalid store: " + "; ".join(errors))
    index = workspace / INDEX_RELATIVE
    index.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".continuity-index-", suffix=".sqlite3", dir=index.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    entries = [(domain, item) for domain in ("facts", "payoffs", "resources", "characters", "relationships") for item in store[domain]]
    try:
        connection = sqlite3.connect(temporary)
        try:
            connection.executescript("""
                PRAGMA journal_mode = DELETE;
                CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE entries (
                  domain TEXT NOT NULL, entry_id TEXT PRIMARY KEY, introduced_chapter INTEGER,
                  status TEXT NOT NULL, tags_json TEXT NOT NULL, payload_json TEXT NOT NULL, search_text TEXT NOT NULL
                );
                CREATE INDEX entries_chapter ON entries(introduced_chapter);
                CREATE INDEX entries_domain ON entries(domain);
                CREATE VIRTUAL TABLE entries_fts USING fts5(entry_id UNINDEXED, search_text, tokenize='unicode61');
            """)
            manifest = store["manifest"]
            connection.executemany("INSERT INTO meta VALUES (?, ?)", [
                ("schema_version", str(STORE_VERSION)),
                ("revision", str(manifest["revision"])),
                ("last_committed_chapter", str(manifest["last_committed_chapter"])),
                ("built_at", utc_now()),
            ])
            for domain, entry in entries:
                searchable = text_for_entry(domain, entry)
                connection.execute("INSERT INTO entries VALUES (?, ?, ?, ?, ?, ?, ?)", (
                    domain, entry["id"], chapter_number(entry.get("introduced_in")), str(entry.get("status", "active")),
                    json.dumps(entry.get("tags", []), ensure_ascii=False), json.dumps(entry, ensure_ascii=False), searchable,
                ))
                connection.execute("INSERT INTO entries_fts VALUES (?, ?)", (entry["id"], searchable))
            connection.commit()
        finally:
            connection.close()
        for attempt in range(3):
            try:
                os.replace(temporary, index)
                break
            except PermissionError:
                if attempt == 2:
                    raise
                time.sleep(0.05 * (attempt + 1))
        return {"index": str(index), "revision": store["manifest"]["revision"], "entries": len(entries)}
    finally:
        if temporary.exists():
            temporary.unlink()


def index_revision(workspace: Path) -> int | None:
    index = workspace / INDEX_RELATIVE
    if not index.is_file():
        return None
    try:
        connection = sqlite3.connect(index)
        try:
            row = connection.execute("SELECT value FROM meta WHERE key = 'revision'").fetchone()
            return int(row[0]) if row else None
        finally:
            connection.close()
    except (sqlite3.Error, ValueError):
        return None


def update_state_for_store(workspace: Path, store: dict[str, Any], index_status: str) -> None:
    path = workspace / "novel-state.yaml"
    state = read_yaml(path)
    if not isinstance(state, dict):
        raise ValueError("novel-state.yaml must be a mapping")
    current_version = state.get("schema_version", 0)
    state["schema_version"] = max(3, current_version if isinstance(current_version, int) else 0)
    continuity = state.setdefault("continuity", {})
    if not isinstance(continuity, dict):
        raise ValueError("novel-state.yaml continuity must be a mapping")
    continuity["last_committed_chapter"] = store["manifest"]["last_committed_chapter"]
    continuity["structured_store"] = {
        "authority": "yaml",
        "path": STORE_RELATIVE.as_posix(),
        "schema_version": STORE_VERSION,
        "revision": store["manifest"]["revision"],
        "index_path": INDEX_RELATIVE.as_posix(),
        "index_status": index_status,
        "indexed_revision": store["manifest"]["revision"] if index_status == "current" else None,
    }
    write_yaml(path, state)


def backup_legacy_views(workspace: Path) -> list[Path]:
    sources = [workspace / relative for relative in ("continuity/baseline.md", "continuity/fact-ledger.md", "continuity/payoff-ledger.md", "continuity/resource-ledger.md")]
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    destination = workspace / "continuity/legacy-markdown" / stamp
    copied: list[Path] = []
    for source in sources:
        if source.is_file():
            destination.mkdir(parents=True, exist_ok=True)
            target = destination / source.name
            shutil.copy2(source, target)
            copied.append(target)
    return copied


def migrate_workspace(workspace: Path, dry_run: bool = False) -> dict[str, Any]:
    state_path = workspace / "novel-state.yaml"
    if not state_path.is_file():
        raise ValueError("missing novel-state.yaml")
    state = read_yaml(state_path)
    if not isinstance(state, dict) or not isinstance(state.get("continuity"), dict):
        raise ValueError("novel-state.yaml needs a continuity mapping")
    last_committed = str(state["continuity"].get("last_committed_chapter", ""))
    if chapter_number(last_committed) is None:
        raise ValueError("novel-state.yaml continuity.last_committed_chapter is invalid")
    paths = store_paths(workspace)
    if paths["root"].exists():
        raise ValueError("continuity/data already exists; migration refuses to overwrite it")
    required = [workspace / relative for relative in ("continuity/baseline.md", "continuity/fact-ledger.md", "continuity/payoff-ledger.md", "continuity/resource-ledger.md")]
    missing = [str(item.relative_to(workspace)) for item in required if not item.is_file()]
    if missing:
        raise ValueError("migration inputs missing: " + ", ".join(missing))
    characters, relationships = migrate_characters(workspace)
    data = {
        "manifest": make_manifest(last_committed),
        "baseline": migrate_baseline(workspace / "continuity/baseline.md", last_committed),
        "facts": migrate_facts(workspace / "continuity/fact-ledger.md"),
        "payoffs": migrate_payoffs(workspace / "continuity/payoff-ledger.md"),
        "resources": migrate_resources(workspace / "continuity/resource-ledger.md"),
        "characters": characters,
        "relationships": relationships,
    }
    temporary_root = Path(tempfile.mkdtemp(prefix="continuity-store-", dir=workspace / "continuity"))
    try:
        staged_workspace = temporary_root.parent.parent
        staged_data = temporary_root / "data"
        staged_data.mkdir()
        staged_paths = {"root": staged_data, "manifest": staged_data / "manifest.yaml", "baseline": staged_data / "baseline.yaml", **{key: staged_data / name for key, name in DOMAIN_FILES.items()}}
        for key, path in staged_paths.items():
            if key != "root":
                write_yaml(path, data[key])
        # Validate a staging object directly; it uses the same schema rules as a committed store.
        validation_workspace = workspace
        errors = validate_store_from_data(data)
        if errors:
            raise ValueError("migration validation failed: " + "; ".join(errors))
        if dry_run:
            return {"dry_run": True, "last_committed_chapter": last_committed, "facts": len(data["facts"]), "payoffs": len(data["payoffs"]), "resources": len(data["resources"]), "characters": len(characters), "relationships": len(relationships)}
        paths["root"].parent.mkdir(parents=True, exist_ok=True)
        os.replace(staged_data, paths["root"])
        backups = backup_legacy_views(workspace)
        committed_store = load_store(workspace)
        render_views(workspace, committed_store)
        index_result = build_index(workspace, committed_store)
        create_checkpoint(workspace, last_committed, "migration-baseline", committed_store)
        update_state_for_store(workspace, committed_store, "current")
        return {"last_committed_chapter": last_committed, "facts": len(data["facts"]), "payoffs": len(data["payoffs"]), "resources": len(data["resources"]), "characters": len(characters), "relationships": len(relationships), "legacy_backup": [str(path) for path in backups], **index_result}
    finally:
        if temporary_root.exists():
            shutil.rmtree(temporary_root)


def validate_store_from_data(data: dict[str, Any]) -> list[str]:
    # Same checks as validate_store, without requiring a committed directory.
    root = Path(tempfile.mkdtemp(prefix="continuity-validate-"))
    try:
        paths = {"root": root, "manifest": root / "manifest.yaml", "baseline": root / "baseline.yaml", **{key: root / name for key, name in DOMAIN_FILES.items()}}
        for key, path in paths.items():
            if key != "root":
                write_yaml(path, data[key])
        return validate_store(root.parent, {key: data[key] for key in ("manifest", "baseline", *DOMAIN_FILES)})
    finally:
        shutil.rmtree(root)


def index_candidate_ids(workspace: Path, target: int, revision: int) -> set[str] | None:
    if index_revision(workspace) != revision:
        return None
    try:
        connection = sqlite3.connect(workspace / INDEX_RELATIVE)
        try:
            rows = connection.execute("SELECT entry_id FROM entries WHERE introduced_chapter IS NULL OR introduced_chapter <= ?", (target,)).fetchall()
            return {str(row[0]) for row in rows}
        finally:
            connection.close()
    except sqlite3.Error:
        return None


def assemble_context(workspace: Path, target: int, characters: set[str], budget: int) -> str:
    store = load_store(workspace)
    errors = validate_store(workspace, store)
    if errors:
        raise ValueError("cannot assemble invalid store: " + "; ".join(errors))
    selected_ids = index_candidate_ids(workspace, target, store["manifest"]["revision"])
    source = "SQLite candidates + YAML authority" if selected_ids is not None else "YAML direct fallback (SQLite missing or stale)"
    lines = [f"<!-- continuity-context: revision {store['manifest']['revision']}; source: {source} -->", "", f"# 第{target:03d}章连续性上下文", ""]
    def append_section(title: str, entries: Iterable[dict[str, Any]], formatter: Any) -> None:
        nonlocal lines
        material = [entry for entry in entries if selected_ids is None or entry.get("id") in selected_ids]
        if not material:
            return
        lines.extend([f"## {title}", ""])
        for entry in material:
            candidate = f"- `{entry['id']}`：{formatter(entry)}"
            if len("\n".join(lines + [candidate])) > budget:
                return
            lines.append(candidate)
        lines.append("")
    active_facts = [item for item in store["facts"] if (chapter_number(item["introduced_in"]) or 0) <= target]
    if characters:
        active_facts.sort(key=lambda item: (not bool(set(item.get("characters", [])) & characters), item["id"]))
    append_section("稳定事实", active_facts, lambda item: f"{item['summary']}（{item.get('constraints', '')}）")
    append_section("未结伏笔", [item for item in store["payoffs"] if item.get("status") not in {"paid_off", "retired"}], lambda item: f"{item['summary']}；{item.get('risks_next_window', '')}")
    append_section("活跃资源", [item for item in store["resources"] if item.get("status") != "retired"], lambda item: f"{item['summary']}；{item.get('usage_constraints', '')}")
    if characters:
        append_section("角色状态", [item for item in store["characters"] if item.get("id") in characters], lambda item: f"{item.get('name', '')}；{'；'.join(item.get('current_state', [])) or '无新增动态状态'}")
        append_section("关系约束", [item for item in store["relationships"] if {item.get("character_a"), item.get("character_b")} & characters], lambda item: f"{item.get('public_relation', '')}；不得越过：{item.get('constraints', '')}")
    return "\n".join(lines).rstrip() + "\n"


def validate_workspace(workspace: Path) -> tuple[list[str], list[str]]:
    """Return structural errors and stale derived-artifact messages without writing."""
    errors: list[str] = []
    stale: list[str] = []
    state_path = workspace / "novel-state.yaml"
    if not state_path.is_file():
        return ["missing novel-state.yaml"], stale
    state = read_yaml(state_path)
    if not isinstance(state, dict):
        return ["novel-state.yaml must be a mapping"], stale
    if (workspace / STORE_RELATIVE).is_dir():
        store_errors = validate_store(workspace)
        errors.extend(store_errors)
        if not store_errors:
            store = load_store(workspace)
            structured = state.get("continuity", {}).get("structured_store", {}) if isinstance(state.get("continuity"), dict) else {}
            if structured.get("authority") != "yaml":
                errors.append("novel-state.yaml must declare YAML continuity authority")
            if structured.get("revision") != store["manifest"]["revision"]:
                stale.append("novel-state.yaml structured_store revision is stale")
            if index_revision(workspace) != store["manifest"]["revision"]:
                stale.append("continuity/index.sqlite3 is missing or stale; YAML fallback remains available")
        return errors, stale
    # Legacy workspaces remain valid and are checked by check_continuity_workspace.py.
    return errors, stale


def command_migrate(args: argparse.Namespace) -> None:
    print(json.dumps(migrate_workspace(args.workspace.resolve(), args.dry_run), ensure_ascii=False, indent=2))


def command_validate(args: argparse.Namespace) -> int:
    errors, stale = validate_workspace(args.workspace.resolve())
    if errors:
        print("CONTINUITY STORE CHECK FAILED")
        for item in errors:
            print(f"- {item}")
        return 1
    if stale:
        print("CONTINUITY STORE CHECK: STALE")
        for item in stale:
            print(f"- {item}")
        return 2
    print("CONTINUITY STORE CHECK: OK")
    return 0


def command_render(args: argparse.Namespace) -> None:
    paths = render_views(args.workspace.resolve())
    print(json.dumps({"rendered": [str(path) for path in paths]}, ensure_ascii=False, indent=2))


def command_index(args: argparse.Namespace) -> None:
    workspace = args.workspace.resolve()
    store = load_store(workspace)
    result = build_index(workspace, store)
    update_state_for_store(workspace, store, "current")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def command_context(args: argparse.Namespace) -> None:
    chars = set(split_list(args.characters)) if args.characters else set()
    print(assemble_context(args.workspace.resolve(), args.chapter, chars, args.max_chars), end="")


def command_checkpoint(args: argparse.Namespace) -> None:
    path = create_checkpoint(args.workspace.resolve(), args.chapter, args.reason)
    print(json.dumps({"checkpoint": str(path)}, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage YAML-authoritative novel continuity with a rebuildable SQLite index.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    migrate = subparsers.add_parser("migrate", help="Migrate legacy Markdown ledgers into YAML authority")
    migrate.add_argument("workspace", type=Path)
    migrate.add_argument("--dry-run", action="store_true")
    validate = subparsers.add_parser("validate", help="Validate the structured store without writing")
    validate.add_argument("workspace", type=Path)
    render = subparsers.add_parser("render-views", help="Regenerate read-only Markdown ledger views")
    render.add_argument("workspace", type=Path)
    index = subparsers.add_parser("build-index", help="Rebuild the disposable SQLite continuity index")
    index.add_argument("workspace", type=Path)
    context = subparsers.add_parser("assemble-context", help="Assemble bounded context from YAML authority")
    context.add_argument("workspace", type=Path)
    context.add_argument("--chapter", type=int, required=True)
    context.add_argument("--characters", default="")
    context.add_argument("--max-chars", type=int, default=9000)
    checkpoint = subparsers.add_parser("checkpoint", help="Create an auditable YAML checkpoint")
    checkpoint.add_argument("workspace", type=Path)
    checkpoint.add_argument("--chapter", required=True)
    checkpoint.add_argument("--reason", default="manual")
    return parser


def main() -> None:
    configure_utf8_output()
    args = build_parser().parse_args()
    if not args.workspace.is_dir():
        raise SystemExit(f"continuity store failed: workspace not found: {args.workspace}")
    if hasattr(args, "max_chars") and args.max_chars < 1000:
        raise SystemExit("continuity store failed: --max-chars must be at least 1000")
    try:
        if args.command == "migrate":
            command_migrate(args)
        elif args.command == "validate":
            raise SystemExit(command_validate(args))
        elif args.command == "render-views":
            command_render(args)
        elif args.command == "build-index":
            command_index(args)
        elif args.command == "assemble-context":
            command_context(args)
        else:
            command_checkpoint(args)
    except (OSError, sqlite3.Error, ValueError, yaml.YAMLError) as error:
        print(f"continuity store failed: {error}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
