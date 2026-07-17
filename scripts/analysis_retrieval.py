#!/usr/bin/env python3
"""Build and query a lightweight retrieval index for a book-analysis workspace."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sqlite3
import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


META_PATTERN = re.compile(r"<!--\s*retrieval-meta:\s*(\{.*?\})\s*-->", re.DOTALL)
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
CHAPTER_PATTERNS = (
    re.compile(r"chapter[-_ ]?(\d+)", re.IGNORECASE),
    re.compile(r"第\s*(\d+)\s*章"),
)
CHINESE_SEQUENCE = re.compile(r"[\u3400-\u9fff]+")
LATIN_TOKEN = re.compile(r"[A-Za-z0-9_]+")
DEFAULT_INDEX = "retrieval/analysis-index.sqlite3"
DEFAULT_EMBEDDINGS = "retrieval/embeddings.jsonl"


def configure_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    relative_path: str
    source_kind: str
    heading: str
    ordinal: int
    chapter_start: int | None
    chapter_end: int | None
    dimensions: tuple[str, ...]
    characters: tuple[str, ...]
    content_hash: str
    content: str


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def load_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value, list):
        return {"vector": value}
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object or vector array")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {error.msg}") from error
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: expected a JSON object")
        rows.append(value)
    return rows


def normalize_string_list(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))


def extract_metadata(text: str, path: Path) -> dict[str, Any]:
    match = META_PATTERN.search(text)
    if not match:
        return {}
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError as error:
        raise ValueError(f"{path}: invalid retrieval-meta JSON: {error.msg}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{path}: retrieval-meta must be a JSON object")
    return value


def infer_chapter_range(text: str, metadata: dict[str, Any]) -> tuple[int | None, int | None]:
    explicit_start = metadata.get("chapter_start")
    explicit_end = metadata.get("chapter_end")
    if isinstance(explicit_start, int) and explicit_start > 0:
        end = explicit_end if isinstance(explicit_end, int) and explicit_end >= explicit_start else explicit_start
        return explicit_start, end
    found: list[int] = []
    for pattern in CHAPTER_PATTERNS:
        found.extend(int(value) for value in pattern.findall(text))
    return (min(found), max(found)) if found else (None, None)


def source_kind(relative_path: str) -> str:
    normalized = relative_path.replace("\\", "/")
    if normalized.startswith("notes/"):
        return "note"
    if normalized.startswith("sections/"):
        return "section"
    if normalized == "evidence-ledger.md":
        return "evidence"
    if normalized == "pattern-cards.md":
        return "pattern"
    if normalized == "uncertainty-ledger.md":
        return "uncertainty"
    return "manifest"


def split_markdown(text: str, max_chars: int, overlap: int) -> list[tuple[str, str]]:
    headings = list(HEADING_PATTERN.finditer(text))
    sections: list[tuple[str, str]] = []
    if not headings:
        sections.append(("", text.strip()))
    else:
        prefix = text[: headings[0].start()].strip()
        if prefix:
            sections.append(("", prefix))
        for index, match in enumerate(headings):
            end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
            sections.append((match.group(2).strip(), text[match.start() : end].strip()))

    chunks: list[tuple[str, str]] = []
    for heading, section in sections:
        if not section:
            continue
        if len(section) <= max_chars:
            chunks.append((heading, section))
            continue
        start = 0
        while start < len(section):
            end = min(len(section), start + max_chars)
            if end < len(section):
                paragraph_end = section.rfind("\n\n", start + max_chars // 2, end)
                if paragraph_end > start:
                    end = paragraph_end
            part = section[start:end].strip()
            if part:
                chunks.append((heading, part))
            if end >= len(section):
                break
            start = max(start + 1, end - overlap)
    return chunks


def discover_markdown(workspace: Path) -> list[Path]:
    candidates: list[Path] = []
    for directory in (workspace / "notes", workspace / "sections"):
        if directory.is_dir():
            candidates.extend(directory.rglob("*.md"))
    for name in (
        "source-manifest.md",
        "coverage-map.md",
        "evidence-ledger.md",
        "uncertainty-ledger.md",
        "pattern-cards.md",
    ):
        path = workspace / name
        if path.is_file():
            candidates.append(path)
    return sorted(set(path.resolve() for path in candidates))


def build_chunks(workspace: Path, max_chars: int, overlap: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in discover_markdown(workspace):
        text = path.read_text(encoding="utf-8")
        metadata = extract_metadata(text, path)
        indexable_text = META_PATTERN.sub("", text).strip()
        relative = path.relative_to(workspace).as_posix()
        dimensions = normalize_string_list(metadata.get("dimensions"))
        if not dimensions and relative.startswith("sections/"):
            dimensions = (path.stem.replace("-", "_"),)
        characters = normalize_string_list(metadata.get("characters"))
        file_start, file_end = infer_chapter_range(relative + "\n" + indexable_text[:500], metadata)
        for ordinal, (heading, content) in enumerate(split_markdown(indexable_text, max_chars, overlap), 1):
            chapter_start, chapter_end = infer_chapter_range(heading + "\n" + content[:500], metadata)
            chapter_start = chapter_start if chapter_start is not None else file_start
            chapter_end = chapter_end if chapter_end is not None else file_end
            identity = f"{relative}\n{heading}\n{ordinal}"
            chunks.append(Chunk(
                chunk_id=f"CHUNK-{sha256_text(identity)[:20]}",
                relative_path=relative,
                source_kind=source_kind(relative),
                heading=heading,
                ordinal=ordinal,
                chapter_start=chapter_start,
                chapter_end=chapter_end,
                dimensions=dimensions,
                characters=characters,
                content_hash=sha256_text(content),
                content=content,
            ))
    return chunks


def lexical_terms(text: str) -> str:
    terms: list[str] = [token.lower() for token in LATIN_TOKEN.findall(text)]
    for sequence in CHINESE_SEQUENCE.findall(text):
        if len(sequence) <= 2:
            terms.append(sequence)
            continue
        terms.extend(sequence[index : index + 2] for index in range(len(sequence) - 1))
        terms.extend(sequence[index : index + 3] for index in range(len(sequence) - 2))
    return " ".join(dict.fromkeys(terms))


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript("""
        PRAGMA journal_mode = DELETE;
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE chunks (
          chunk_id TEXT PRIMARY KEY,
          relative_path TEXT NOT NULL,
          source_kind TEXT NOT NULL,
          heading TEXT NOT NULL,
          ordinal INTEGER NOT NULL,
          chapter_start INTEGER,
          chapter_end INTEGER,
          dimensions_json TEXT NOT NULL,
          characters_json TEXT NOT NULL,
          content_hash TEXT NOT NULL,
          content TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE chunks_fts USING fts5(
          chunk_id UNINDEXED,
          lexical_text,
          content,
          tokenize='unicode61'
        );
        CREATE TABLE graph_nodes (
          node_id TEXT PRIMARY KEY,
          node_type TEXT NOT NULL,
          label TEXT NOT NULL,
          aliases_json TEXT NOT NULL,
          attributes_json TEXT NOT NULL,
          confidence TEXT NOT NULL,
          source_refs_json TEXT NOT NULL
        );
        CREATE TABLE graph_edges (
          edge_id TEXT PRIMARY KEY,
          source_id TEXT NOT NULL,
          target_id TEXT NOT NULL,
          relation TEXT NOT NULL,
          confidence TEXT NOT NULL,
          evidence_json TEXT NOT NULL,
          attributes_json TEXT NOT NULL,
          FOREIGN KEY(source_id) REFERENCES graph_nodes(node_id),
          FOREIGN KEY(target_id) REFERENCES graph_nodes(node_id)
        );
        CREATE INDEX graph_edges_source ON graph_edges(source_id);
        CREATE INDEX graph_edges_target ON graph_edges(target_id);
    """)


def require_text(row: dict[str, Any], key: str, label: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}: missing non-empty '{key}'")
    return value.strip()


def insert_graph(connection: sqlite3.Connection, workspace: Path) -> tuple[int, int]:
    node_path = workspace / "graph" / "nodes.jsonl"
    edge_path = workspace / "graph" / "edges.jsonl"
    nodes = load_jsonl(node_path)
    node_ids: set[str] = set()
    for index, row in enumerate(nodes, 1):
        label = f"{node_path}:{index}"
        node_id = require_text(row, "id", label)
        node_type = require_text(row, "type", label)
        node_label = require_text(row, "label", label)
        if node_id in node_ids:
            raise ValueError(f"{label}: duplicate node id '{node_id}'")
        node_ids.add(node_id)
        connection.execute(
            "INSERT INTO graph_nodes VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                node_id,
                node_type,
                node_label,
                json.dumps(normalize_string_list(row.get("aliases")), ensure_ascii=False),
                json.dumps(row.get("attributes") if isinstance(row.get("attributes"), dict) else {}, ensure_ascii=False),
                str(row.get("confidence") or "medium"),
                json.dumps(normalize_string_list(row.get("source_refs")), ensure_ascii=False),
            ),
        )

    edges = load_jsonl(edge_path)
    edge_ids: set[str] = set()
    for index, row in enumerate(edges, 1):
        label = f"{edge_path}:{index}"
        edge_id = require_text(row, "id", label)
        source = require_text(row, "source", label)
        target = require_text(row, "target", label)
        relation = require_text(row, "relation", label)
        if edge_id in edge_ids:
            raise ValueError(f"{label}: duplicate edge id '{edge_id}'")
        if source not in node_ids or target not in node_ids:
            raise ValueError(f"{label}: edge endpoints must exist in graph/nodes.jsonl")
        edge_ids.add(edge_id)
        connection.execute(
            "INSERT INTO graph_edges VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                edge_id,
                source,
                target,
                relation,
                str(row.get("confidence") or "medium"),
                json.dumps(normalize_string_list(row.get("evidence")), ensure_ascii=False),
                json.dumps(row.get("attributes") if isinstance(row.get("attributes"), dict) else {}, ensure_ascii=False),
            ),
        )
    return len(nodes), len(edges)


def source_fingerprint(workspace: Path) -> str:
    state_path = workspace / "analysis-state.yaml"
    if not state_path.is_file():
        return ""
    match = re.search(r"^\s*fingerprint:\s*[\"']?(.+?)[\"']?\s*$", state_path.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1).strip() if match else ""


def build_index(workspace: Path, index_path: Path, max_chars: int, overlap: int) -> dict[str, Any]:
    chunks = build_chunks(workspace, max_chars, overlap)
    if not chunks:
        raise ValueError("no analysis Markdown found under notes/, sections/, or the analysis ledgers")
    index_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = index_path.with_suffix(index_path.suffix + ".tmp")
    if temporary.exists():
        temporary.unlink()
    connection = sqlite3.connect(temporary)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        create_schema(connection)
        for chunk in chunks:
            connection.execute(
                "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    chunk.chunk_id,
                    chunk.relative_path,
                    chunk.source_kind,
                    chunk.heading,
                    chunk.ordinal,
                    chunk.chapter_start,
                    chunk.chapter_end,
                    json.dumps(chunk.dimensions, ensure_ascii=False),
                    json.dumps(chunk.characters, ensure_ascii=False),
                    chunk.content_hash,
                    chunk.content,
                ),
            )
            searchable = " ".join((chunk.relative_path, chunk.heading, *chunk.dimensions, *chunk.characters, chunk.content))
            connection.execute(
                "INSERT INTO chunks_fts(chunk_id, lexical_text, content) VALUES (?, ?, ?)",
                (chunk.chunk_id, lexical_terms(searchable), chunk.content),
            )
        node_count, edge_count = insert_graph(connection, workspace)
        metadata = {
            "schema_version": "1",
            "workspace": str(workspace),
            "source_fingerprint": source_fingerprint(workspace),
            "chunk_count": str(len(chunks)),
            "node_count": str(node_count),
            "edge_count": str(edge_count),
        }
        connection.executemany("INSERT INTO meta(key, value) VALUES (?, ?)", metadata.items())
        connection.commit()
    finally:
        connection.close()
    os.replace(temporary, index_path)
    return {"index": str(index_path), "chunks": len(chunks), "nodes": node_count, "edges": edge_count}


def resolve_index(workspace: Path, value: str | None) -> Path:
    return Path(value).expanduser().resolve() if value else (workspace / DEFAULT_INDEX).resolve()


def open_index(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise ValueError(f"index not found: {path}; run the build command first")
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def row_allowed(row: sqlite3.Row, args: argparse.Namespace) -> bool:
    if args.kind and row["source_kind"] != args.kind:
        return False
    dimensions = json.loads(row["dimensions_json"])
    characters = json.loads(row["characters_json"])
    if args.dimension and args.dimension not in dimensions:
        return False
    if args.character and not any(args.character.lower() in value.lower() for value in characters):
        return False
    if args.chapter is not None:
        start, end = row["chapter_start"], row["chapter_end"]
        if start is None or end is None or not start <= args.chapter <= end:
            return False
    return True


def lexical_rank(connection: sqlite3.Connection, query: str, args: argparse.Namespace) -> list[sqlite3.Row]:
    terms = lexical_terms(query).split()
    if not terms:
        return []
    expression = " OR ".join(f'"{term.replace(chr(34), chr(34) * 2)}"' for term in terms)
    rows = connection.execute(
        """
        SELECT c.*, bm25(chunks_fts) AS lexical_score
        FROM chunks_fts JOIN chunks c ON c.chunk_id = chunks_fts.chunk_id
        WHERE chunks_fts MATCH ? ORDER BY lexical_score LIMIT ?
        """,
        (expression, max(args.limit * 20, 100)),
    ).fetchall()
    filtered = [row for row in rows if row_allowed(row, args)]
    if filtered:
        return filtered
    like_rows = connection.execute(
        "SELECT *, 0.0 AS lexical_score FROM chunks WHERE content LIKE ? LIMIT ?",
        (f"%{query}%", max(args.limit * 20, 100)),
    ).fetchall()
    return [row for row in like_rows if row_allowed(row, args)]


def normalize_vector(value: Any, label: str) -> list[float]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label}: vector must be a non-empty array")
    try:
        vector = [float(item) for item in value]
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label}: vector values must be numeric") from error
    if not all(math.isfinite(item) for item in vector):
        raise ValueError(f"{label}: vector contains non-finite values")
    return vector


def cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("query vector and stored embeddings use different dimensions")
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm) if left_norm and right_norm else 0.0


def vector_rank(connection: sqlite3.Connection, embeddings_path: Path, query_path: Path, args: argparse.Namespace) -> list[tuple[sqlite3.Row, float]]:
    query_record = load_json_object(query_path)
    query_vector = normalize_vector(query_record.get("vector"), str(query_path))
    query_model = str(query_record.get("model") or "")
    rows_by_id = {row["chunk_id"]: row for row in connection.execute("SELECT * FROM chunks").fetchall() if row_allowed(row, args)}
    ranked: list[tuple[sqlite3.Row, float]] = []
    for index, record in enumerate(load_jsonl(embeddings_path), 1):
        chunk_id = str(record.get("chunk_id") or "")
        row = rows_by_id.get(chunk_id)
        if row is None:
            continue
        model = str(record.get("model") or "")
        if query_model and model and model != query_model:
            continue
        vector = normalize_vector(record.get("vector"), f"{embeddings_path}:{index}")
        ranked.append((row, cosine(query_vector, vector)))
    return sorted(ranked, key=lambda item: item[1], reverse=True)


def fuse_results(lexical: list[sqlite3.Row], vectors: list[tuple[sqlite3.Row, float]], vector_weight: float) -> list[dict[str, Any]]:
    combined: dict[str, dict[str, Any]] = {}
    for rank, row in enumerate(lexical, 1):
        combined[row["chunk_id"]] = {"row": row, "score": (1 - vector_weight) / (60 + rank), "reason": ["lexical"]}
    for rank, (row, similarity) in enumerate(vectors, 1):
        item = combined.setdefault(row["chunk_id"], {"row": row, "score": 0.0, "reason": []})
        item["score"] += vector_weight / (60 + rank)
        item["reason"].append("vector")
        item["vector_similarity"] = similarity
    return sorted(combined.values(), key=lambda item: item["score"], reverse=True)


def add_neighbors(connection: sqlite3.Connection, results: list[dict[str, Any]], distance: int) -> list[dict[str, Any]]:
    if distance <= 0:
        return results
    seen = {item["row"]["chunk_id"] for item in results}
    expanded = list(results)
    for item in results:
        row = item["row"]
        rows = connection.execute(
            "SELECT * FROM chunks WHERE relative_path = ? AND ordinal BETWEEN ? AND ? ORDER BY ordinal",
            (row["relative_path"], max(1, row["ordinal"] - distance), row["ordinal"] + distance),
        ).fetchall()
        for neighbor in rows:
            if neighbor["chunk_id"] in seen:
                continue
            seen.add(neighbor["chunk_id"])
            expanded.append({"row": neighbor, "score": item["score"] * 0.5, "reason": ["neighbor"]})
    return expanded


def serialize_result(item: dict[str, Any], max_chars: int) -> dict[str, Any]:
    row = item["row"]
    return {
        "chunk_id": row["chunk_id"],
        "path": row["relative_path"],
        "kind": row["source_kind"],
        "heading": row["heading"],
        "chapter_start": row["chapter_start"],
        "chapter_end": row["chapter_end"],
        "dimensions": json.loads(row["dimensions_json"]),
        "characters": json.loads(row["characters_json"]),
        "score": round(float(item["score"]), 8),
        "reasons": item["reason"],
        "vector_similarity": round(float(item["vector_similarity"]), 6) if "vector_similarity" in item else None,
        "content": row["content"][:max_chars],
    }


def print_payload(payload: Any, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if isinstance(payload, list):
        for item in payload:
            chapter = ""
            if item.get("chapter_start") is not None:
                chapter = f" · 第{item['chapter_start']}-{item['chapter_end']}章"
            print(f"## {item.get('heading') or item.get('label') or item.get('chunk_id')}\n")
            print(f"- 来源：`{item.get('path', '')}`{chapter}")
            if item.get("reasons"):
                print(f"- 命中：{', '.join(item['reasons'])}")
            print(f"\n{item.get('content', '')}\n")
        return
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def search_command(args: argparse.Namespace) -> None:
    workspace = args.workspace.resolve()
    index_path = resolve_index(workspace, args.index)
    with open_index(index_path) as connection:
        lexical = lexical_rank(connection, args.query, args)
        vectors: list[tuple[sqlite3.Row, float]] = []
        if args.query_vector:
            embeddings = Path(args.embeddings).expanduser().resolve() if args.embeddings else (workspace / DEFAULT_EMBEDDINGS)
            if not embeddings.is_file():
                raise ValueError(f"embeddings not found: {embeddings}")
            vectors = vector_rank(connection, embeddings, Path(args.query_vector).expanduser().resolve(), args)
        results = fuse_results(lexical, vectors, args.vector_weight)
        results = add_neighbors(connection, results[: args.limit], args.neighbor)
        payload = [serialize_result(item, args.max_chars) for item in results]
        print_payload(payload, args.format)


def graph_neighbors(connection: sqlite3.Connection, start: str, depth: int, relation: str | None, direction: str) -> dict[str, Any]:
    start = resolve_graph_node(connection, start)
    visited = {start}
    seen_edges: set[str] = set()
    queue: deque[tuple[str, int]] = deque([(start, 0)])
    edges: list[dict[str, Any]] = []
    while queue:
        current, current_depth = queue.popleft()
        if current_depth >= depth:
            continue
        clauses: list[str] = []
        values: list[Any] = []
        if direction in ("outgoing", "both"):
            clauses.append("source_id = ?")
            values.append(current)
        if direction in ("incoming", "both"):
            clauses.append("target_id = ?")
            values.append(current)
        sql = f"SELECT * FROM graph_edges WHERE ({' OR '.join(clauses)})"
        if relation:
            sql += " AND relation = ?"
            values.append(relation)
        for row in connection.execute(sql, values).fetchall():
            if row["edge_id"] in seen_edges:
                continue
            seen_edges.add(row["edge_id"])
            edge = dict(row)
            edges.append(edge)
            neighbor = row["target_id"] if row["source_id"] == current else row["source_id"]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, current_depth + 1))
    placeholders = ",".join("?" for _ in visited)
    nodes = [dict(row) for row in connection.execute(f"SELECT * FROM graph_nodes WHERE node_id IN ({placeholders})", tuple(visited)).fetchall()]
    return {"start": start, "depth": depth, "nodes": nodes, "edges": edges}


def trace_graph(connection: sqlite3.Connection, start: str, target: str, max_depth: int, relation: str | None) -> dict[str, Any]:
    start = resolve_graph_node(connection, start)
    target = resolve_graph_node(connection, target)
    queue: deque[tuple[str, list[dict[str, Any]]]] = deque([(start, [])])
    visited = {start}
    while queue:
        current, path = queue.popleft()
        if len(path) >= max_depth:
            continue
        sql = "SELECT * FROM graph_edges WHERE source_id = ?"
        values: list[Any] = [current]
        if relation:
            sql += " AND relation = ?"
            values.append(relation)
        for row in connection.execute(sql, values).fetchall():
            edge = dict(row)
            next_path = [*path, edge]
            if row["target_id"] == target:
                return {"from": start, "to": target, "found": True, "edges": next_path}
            if row["target_id"] not in visited:
                visited.add(row["target_id"])
                queue.append((row["target_id"], next_path))
    return {"from": start, "to": target, "found": False, "edges": []}


def resolve_graph_node(connection: sqlite3.Connection, value: str) -> str:
    exact = connection.execute("SELECT node_id FROM graph_nodes WHERE node_id = ?", (value,)).fetchone()
    if exact:
        return str(exact["node_id"])
    lowered = value.casefold()
    matches: list[str] = []
    for row in connection.execute("SELECT node_id, label, aliases_json FROM graph_nodes").fetchall():
        aliases = json.loads(row["aliases_json"])
        labels = [str(row["label"]), *(str(alias) for alias in aliases)]
        if any(label.casefold() == lowered for label in labels):
            matches.append(str(row["node_id"]))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(f"graph node label is ambiguous: {value}; use a stable node id")
    raise ValueError(f"graph node not found: {value}")


def node_search_command(args: argparse.Namespace) -> None:
    workspace = args.workspace.resolve()
    needle = args.query.casefold()
    with open_index(resolve_index(workspace, args.index)) as connection:
        matches: list[dict[str, Any]] = []
        for row in connection.execute("SELECT * FROM graph_nodes").fetchall():
            aliases = json.loads(row["aliases_json"])
            haystack = " ".join((row["node_id"], row["label"], *aliases)).casefold()
            if needle not in haystack or (args.type and row["node_type"] != args.type):
                continue
            matches.append({
                "id": row["node_id"],
                "type": row["node_type"],
                "label": row["label"],
                "aliases": aliases,
                "confidence": row["confidence"],
                "source_refs": json.loads(row["source_refs_json"]),
            })
        print_payload(matches[: args.limit], args.format)


def graph_command(args: argparse.Namespace) -> None:
    workspace = args.workspace.resolve()
    with open_index(resolve_index(workspace, args.index)) as connection:
        if args.command == "neighbors":
            payload = graph_neighbors(connection, args.node, args.depth, args.relation, args.direction)
        else:
            payload = trace_graph(connection, args.from_node, args.to_node, args.max_depth, args.relation)
        print_payload(payload, args.format)


def status_command(args: argparse.Namespace) -> None:
    workspace = args.workspace.resolve()
    index_path = resolve_index(workspace, args.index)
    with open_index(index_path) as connection:
        metadata = {row["key"]: row["value"] for row in connection.execute("SELECT key, value FROM meta").fetchall()}
        metadata["index"] = str(index_path)
        embeddings = workspace / DEFAULT_EMBEDDINGS
        metadata["embeddings"] = str(embeddings) if embeddings.is_file() else "not configured"
        print_payload(metadata, args.format)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and query a lightweight BookGraph and text index.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="Build a derived SQLite index from an analysis workspace")
    build.add_argument("workspace", type=Path)
    build.add_argument("--index")
    build.add_argument("--max-chars", type=int, default=6000)
    build.add_argument("--overlap", type=int, default=300)

    search = subparsers.add_parser("search", help="Search notes and analysis artifacts")
    search.add_argument("workspace", type=Path)
    search.add_argument("query")
    search.add_argument("--index")
    search.add_argument("--limit", type=int, default=8)
    search.add_argument("--kind", choices=("note", "section", "evidence", "pattern", "uncertainty", "manifest"))
    search.add_argument("--chapter", type=int)
    search.add_argument("--dimension")
    search.add_argument("--character")
    search.add_argument("--neighbor", type=int, default=1)
    search.add_argument("--query-vector")
    search.add_argument("--embeddings")
    search.add_argument("--vector-weight", type=float, default=0.35)
    search.add_argument("--max-chars", type=int, default=1200)
    search.add_argument("--format", choices=("markdown", "json"), default="markdown")

    nodes = subparsers.add_parser("nodes", help="Find BookGraph nodes by id, label, or alias")
    nodes.add_argument("workspace", type=Path)
    nodes.add_argument("query")
    nodes.add_argument("--index")
    nodes.add_argument("--type")
    nodes.add_argument("--limit", type=int, default=20)
    nodes.add_argument("--format", choices=("markdown", "json"), default="json")

    neighbors = subparsers.add_parser("neighbors", help="Traverse related BookGraph nodes")
    neighbors.add_argument("workspace", type=Path)
    neighbors.add_argument("node")
    neighbors.add_argument("--index")
    neighbors.add_argument("--depth", type=int, default=1)
    neighbors.add_argument("--relation")
    neighbors.add_argument("--direction", choices=("outgoing", "incoming", "both"), default="both")
    neighbors.add_argument("--format", choices=("markdown", "json"), default="json")

    trace = subparsers.add_parser("trace", help="Trace an outgoing BookGraph path")
    trace.add_argument("workspace", type=Path)
    trace.add_argument("from_node")
    trace.add_argument("to_node")
    trace.add_argument("--index")
    trace.add_argument("--max-depth", type=int, default=6)
    trace.add_argument("--relation")
    trace.add_argument("--format", choices=("markdown", "json"), default="json")

    status = subparsers.add_parser("status", help="Show index status")
    status.add_argument("workspace", type=Path)
    status.add_argument("--index")
    status.add_argument("--format", choices=("markdown", "json"), default="json")
    return parser


def validate_args(args: argparse.Namespace) -> None:
    if hasattr(args, "workspace") and not args.workspace.is_dir():
        raise ValueError(f"analysis workspace not found: {args.workspace}")
    if args.command == "build":
        if args.max_chars < 500:
            raise ValueError("--max-chars must be at least 500")
        if args.overlap < 0 or args.overlap >= args.max_chars:
            raise ValueError("--overlap must be non-negative and smaller than --max-chars")
    if args.command == "search":
        if args.limit < 1 or args.neighbor < 0 or args.max_chars < 1:
            raise ValueError("search limits must be positive and neighbor must be non-negative")
        if not 0 <= args.vector_weight <= 1:
            raise ValueError("--vector-weight must be between 0 and 1")
    if args.command == "nodes" and args.limit < 1:
        raise ValueError("--limit must be positive")
    if args.command in ("neighbors", "trace"):
        depth = args.depth if args.command == "neighbors" else args.max_depth
        if depth < 1:
            raise ValueError("graph depth must be at least 1")


def run() -> int:
    configure_utf8_output()
    args = build_parser().parse_args()
    validate_args(args)
    if args.command == "build":
        workspace = args.workspace.resolve()
        result = build_index(workspace, resolve_index(workspace, args.index), args.max_chars, args.overlap)
        print_payload(result, "json")
    elif args.command == "search":
        search_command(args)
    elif args.command == "nodes":
        node_search_command(args)
    elif args.command in ("neighbors", "trace"):
        graph_command(args)
    else:
        status_command(args)
    return 0


def main() -> None:
    try:
        raise SystemExit(run())
    except (OSError, sqlite3.Error, ValueError) as error:
        print(f"analysis retrieval failed: {error}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
