#!/usr/bin/env python3
"""Validate, summarize, and compare metadata-only ranking snapshots."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


REQUIRED_FIELDS = (
    "platform",
    "chart",
    "window",
    "captured_at",
    "rank",
    "title",
    "author",
    "source_url",
    "access_level",
)
SIGNAL_DIMENSIONS = {
    "genre",
    "subgenre",
    "protagonist_identity",
    "core_mechanism",
    "emotional_promise",
    "hook_pattern",
    "audience_signal",
}
EVIDENCE_FIELDS = {"title", "tags", "synopsis"}
CONFIDENCE_LEVELS = {"high", "medium", "low"}


class SnapshotError(ValueError):
    """Raised when a snapshot violates the trend data contract."""


def _configure_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _parse_date(value: Any, field: str, line_number: int) -> str:
    if not _nonempty_string(value):
        raise SnapshotError(f"line {line_number}: {field} must be a YYYY-MM-DD string")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise SnapshotError(f"line {line_number}: invalid {field}: {value!r}") from exc
    if parsed.isoformat() != value:
        raise SnapshotError(f"line {line_number}: {field} must use YYYY-MM-DD")
    return value


def _validate_updated_at(value: Any, line_number: int) -> None:
    if value is None:
        return
    if not _nonempty_string(value):
        raise SnapshotError(f"line {line_number}: updated_at must be an ISO date or datetime")
    try:
        if len(value) == 10:
            date.fromisoformat(value)
        else:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SnapshotError(f"line {line_number}: invalid updated_at: {value!r}") from exc


def _validate_url(value: Any, line_number: int) -> None:
    if not _nonempty_string(value):
        raise SnapshotError(f"line {line_number}: source_url must be a public HTTP(S) URL")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SnapshotError(f"line {line_number}: source_url must be a public HTTP(S) URL")


def _field_has_evidence(record: dict[str, Any], field: str) -> bool:
    value = record.get(field)
    if field == "tags":
        return isinstance(value, list) and any(_nonempty_string(item) for item in value)
    return _nonempty_string(value)


def _validate_signals(record: dict[str, Any], line_number: int) -> None:
    signals = record.get("signals", [])
    if not isinstance(signals, list):
        raise SnapshotError(f"line {line_number}: signals must be a list")
    seen: set[tuple[str, str]] = set()
    for index, signal in enumerate(signals, start=1):
        prefix = f"line {line_number}, signal {index}"
        if not isinstance(signal, dict):
            raise SnapshotError(f"{prefix}: signal must be an object")
        dimension = signal.get("dimension")
        value = signal.get("value")
        confidence = signal.get("confidence")
        evidence_fields = signal.get("evidence_fields")
        if dimension not in SIGNAL_DIMENSIONS:
            raise SnapshotError(f"{prefix}: unsupported dimension {dimension!r}")
        if not _nonempty_string(value):
            raise SnapshotError(f"{prefix}: value must be a non-empty string")
        if confidence not in CONFIDENCE_LEVELS:
            raise SnapshotError(f"{prefix}: confidence must be high, medium, or low")
        if not isinstance(evidence_fields, list) or not evidence_fields:
            raise SnapshotError(f"{prefix}: evidence_fields must be a non-empty list")
        if any(field not in EVIDENCE_FIELDS for field in evidence_fields):
            raise SnapshotError(f"{prefix}: evidence_fields may only use title, tags, synopsis")
        if any(not _field_has_evidence(record, field) for field in evidence_fields):
            raise SnapshotError(f"{prefix}: every evidence field must contain source metadata")
        key = (dimension, value.strip().casefold())
        if key in seen:
            raise SnapshotError(f"{prefix}: duplicate signal {dimension}:{value}")
        seen.add(key)


def load_snapshot(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise SnapshotError(f"snapshot not found: {path}")
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            if not raw_line.strip():
                continue
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise SnapshotError(f"line {line_number}: invalid JSON: {exc.msg}") from exc
            if not isinstance(record, dict):
                raise SnapshotError(f"line {line_number}: each JSONL entry must be an object")
            _validate_record(record, line_number)
            records.append(record)
    if not records:
        raise SnapshotError("snapshot contains no records")
    _validate_snapshot_consistency(records)
    return records


def _validate_record(record: dict[str, Any], line_number: int) -> None:
    missing = [field for field in REQUIRED_FIELDS if field not in record]
    if missing:
        raise SnapshotError(f"line {line_number}: missing required fields: {', '.join(missing)}")
    for field in ("platform", "chart", "window", "title", "author"):
        if not _nonempty_string(record[field]):
            raise SnapshotError(f"line {line_number}: {field} must be a non-empty string")
    _parse_date(record["captured_at"], "captured_at", line_number)
    rank = record["rank"]
    if isinstance(rank, bool) or not isinstance(rank, int) or rank < 1:
        raise SnapshotError(f"line {line_number}: rank must be a positive integer")
    _validate_url(record["source_url"], line_number)
    if record["access_level"] != "metadata_only":
        raise SnapshotError(f"line {line_number}: access_level must be metadata_only")
    if "tags" in record and (
        not isinstance(record["tags"], list)
        or any(not _nonempty_string(item) for item in record["tags"])
    ):
        raise SnapshotError(f"line {line_number}: tags must be a list of non-empty strings")
    for field in ("category", "synopsis", "status"):
        if field in record and record[field] is not None and not _nonempty_string(record[field]):
            raise SnapshotError(f"line {line_number}: {field} must be a non-empty string when present")
    if "word_count" in record:
        count = record["word_count"]
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise SnapshotError(f"line {line_number}: word_count must be a non-negative integer")
    _validate_updated_at(record.get("updated_at"), line_number)
    _validate_signals(record, line_number)


def _validate_snapshot_consistency(records: list[dict[str, Any]]) -> None:
    anchor = records[0]
    for field in ("platform", "chart", "window", "captured_at"):
        values = {str(record[field]).strip().casefold() for record in records}
        if len(values) != 1:
            raise SnapshotError(f"snapshot entries must share one {field}")
    works: set[tuple[str, str]] = set()
    ranks: set[int] = set()
    for record in records:
        work_key = (record["title"].strip().casefold(), record["author"].strip().casefold())
        if work_key in works:
            raise SnapshotError(f"duplicate work: {record['title']} / {record['author']}")
        works.add(work_key)
        if record["rank"] in ranks:
            raise SnapshotError(f"duplicate rank in {anchor['platform']} / {anchor['chart']}: {record['rank']}")
        ranks.add(record["rank"])


def rank_weight(rank: int) -> float:
    return 1.0 / math.log2(rank + 1)


def _snapshot_identity(records: list[dict[str, Any]]) -> dict[str, Any]:
    first = records[0]
    return {
        "platform": first["platform"],
        "chart": first["chart"],
        "window": first["window"],
        "captured_at": first["captured_at"],
        "entry_count": len(records),
    }


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        for signal in record.get("signals", []):
            key = (signal["dimension"], signal["value"].strip().casefold())
            group = groups.setdefault(
                key,
                {
                    "dimension": signal["dimension"],
                    "value": signal["value"].strip(),
                    "works": set(),
                    "platforms": set(),
                    "ranks": [],
                    "rank_weight": 0.0,
                },
            )
            group["works"].add((record["title"].casefold(), record["author"].casefold()))
            group["platforms"].add(record["platform"])
            group["ranks"].append(record["rank"])
            group["rank_weight"] += rank_weight(record["rank"])
    signals = []
    for group in groups.values():
        signals.append(
            {
                "dimension": group["dimension"],
                "value": group["value"],
                "work_count": len(group["works"]),
                "platform_count": len(group["platforms"]),
                "platforms": sorted(group["platforms"]),
                "average_rank": round(sum(group["ranks"]) / len(group["ranks"]), 4),
                "rank_weight": round(group["rank_weight"], 6),
            }
        )
    signals.sort(key=lambda item: (-item["rank_weight"], item["dimension"], item["value"]))
    return {
        "snapshot": _snapshot_identity(records),
        "ranking_weight_formula": "1 / log2(rank + 1)",
        "supports_trend_claims": False,
        "signals": signals,
    }


def _work_map(records: Iterable[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (record["title"].strip().casefold(), record["author"].strip().casefold()): record
        for record in records
    }


def _signal_weights(records: Iterable[dict[str, Any]]) -> dict[tuple[str, str], tuple[str, float]]:
    weights: dict[tuple[str, str], tuple[str, float]] = {}
    for record in records:
        for signal in record.get("signals", []):
            key = (signal["dimension"], signal["value"].strip().casefold())
            display, total = weights.get(key, (signal["value"].strip(), 0.0))
            weights[key] = (display, total + rank_weight(record["rank"]))
    return weights


def compare(older: list[dict[str, Any]], newer: list[dict[str, Any]]) -> dict[str, Any]:
    old_id = _snapshot_identity(older)
    new_id = _snapshot_identity(newer)
    for field in ("platform", "chart", "window"):
        if str(old_id[field]).strip().casefold() != str(new_id[field]).strip().casefold():
            raise SnapshotError(f"cannot compare snapshots with different {field}")
    if date.fromisoformat(old_id["captured_at"]) >= date.fromisoformat(new_id["captured_at"]):
        raise SnapshotError("older snapshot date must be earlier than newer snapshot date")

    old_works = _work_map(older)
    new_works = _work_map(newer)
    entrants = [new_works[key] for key in new_works.keys() - old_works.keys()]
    exits = [old_works[key] for key in old_works.keys() - new_works.keys()]
    rank_changes = []
    for key in old_works.keys() & new_works.keys():
        old_rank = old_works[key]["rank"]
        new_rank = new_works[key]["rank"]
        if old_rank != new_rank:
            rank_changes.append(
                {
                    "title": new_works[key]["title"],
                    "author": new_works[key]["author"],
                    "older_rank": old_rank,
                    "newer_rank": new_rank,
                    "rank_change": old_rank - new_rank,
                }
            )
    entrants.sort(key=lambda item: item["rank"])
    exits.sort(key=lambda item: item["rank"])
    rank_changes.sort(key=lambda item: (-item["rank_change"], item["newer_rank"]))

    old_weights = _signal_weights(older)
    new_weights = _signal_weights(newer)
    signal_changes = []
    for dimension, normalized_value in sorted(old_weights.keys() | new_weights.keys()):
        old_value, old_weight = old_weights.get((dimension, normalized_value), (normalized_value, 0.0))
        new_value, new_weight = new_weights.get((dimension, normalized_value), (old_value, 0.0))
        signal_changes.append(
            {
                "dimension": dimension,
                "value": new_value,
                "older_weight": round(old_weight, 6),
                "newer_weight": round(new_weight, 6),
                "weight_change": round(new_weight - old_weight, 6),
            }
        )
    signal_changes.sort(key=lambda item: (-abs(item["weight_change"]), item["dimension"], item["value"]))
    return {
        "older_snapshot": old_id,
        "newer_snapshot": new_id,
        "ranking_weight_formula": "1 / log2(rank + 1)",
        "interpretation_included": False,
        "entrants": [
            {"title": item["title"], "author": item["author"], "rank": item["rank"]}
            for item in entrants
        ],
        "exits": [
            {"title": item["title"], "author": item["author"], "rank": item["rank"]}
            for item in exits
        ],
        "rank_changes": rank_changes,
        "signal_weight_changes": signal_changes,
    }


def _markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    if not rows:
        return "_无_"
    output = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    output.extend("| " + " | ".join(str(cell) for cell in row) + " |" for row in rows)
    return "\n".join(output)


def summary_markdown(data: dict[str, Any]) -> str:
    snapshot = data["snapshot"]
    rows = [
        [item["dimension"], item["value"], item["work_count"], item["platform_count"], item["average_rank"], item["rank_weight"]]
        for item in data["signals"]
    ]
    return "\n".join(
        [
            "# 当前榜单构成",
            "",
            f"- 平台：{snapshot['platform']}",
            f"- 榜单：{snapshot['chart']}",
            f"- 统计周期：{snapshot['window']}",
            f"- 快照日期：{snapshot['captured_at']}",
            f"- 条目数：{snapshot['entry_count']}",
            "- 限制：单次快照不支持上升、下降、持续热门或新晋题材判断。",
            "",
            _markdown_table(["维度", "信号", "作品数", "平台数", "平均名次", "排名权重"], rows),
        ]
    )


def compare_markdown(data: dict[str, Any]) -> str:
    old = data["older_snapshot"]
    new = data["newer_snapshot"]
    entrant_rows = [[item["rank"], item["title"], item["author"]] for item in data["entrants"]]
    exit_rows = [[item["rank"], item["title"], item["author"]] for item in data["exits"]]
    rank_rows = [
        [item["title"], item["author"], item["older_rank"], item["newer_rank"], item["rank_change"]]
        for item in data["rank_changes"]
    ]
    signal_rows = [
        [item["dimension"], item["value"], item["older_weight"], item["newer_weight"], item["weight_change"]]
        for item in data["signal_weight_changes"]
    ]
    return "\n".join(
        [
            "# 可比榜单快照差值",
            "",
            f"- 范围：{old['platform']} / {old['chart']} / {old['window']}",
            f"- 日期：{old['captured_at']} → {new['captured_at']}",
            "- 说明：以下仅为事实差值，不包含趋势或机会判断；名次变化正数表示名次向前。",
            "",
            "## 新增作品",
            "",
            _markdown_table(["新名次", "作品", "作者"], entrant_rows),
            "",
            "## 退出作品",
            "",
            _markdown_table(["旧名次", "作品", "作者"], exit_rows),
            "",
            "## 名次变化",
            "",
            _markdown_table(["作品", "作者", "旧名次", "新名次", "变化"], rank_rows),
            "",
            "## 信号权重变化",
            "",
            _markdown_table(["维度", "信号", "旧权重", "新权重", "差值"], signal_rows),
        ]
    )


def _emit(data: dict[str, Any], output_format: str, markdown_renderer: Any) -> None:
    if output_format == "json":
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(markdown_renderer(data))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate", help="validate one JSONL snapshot")
    validate_parser.add_argument("snapshot", type=Path)
    summarize_parser = subparsers.add_parser("summarize", help="aggregate factual signals from one snapshot")
    summarize_parser.add_argument("snapshot", type=Path)
    summarize_parser.add_argument("--format", choices=("json", "markdown"), default="json")
    compare_parser = subparsers.add_parser("compare", help="compare two snapshots from the same chart")
    compare_parser.add_argument("older", type=Path)
    compare_parser.add_argument("newer", type=Path)
    compare_parser.add_argument("--format", choices=("json", "markdown"), default="json")
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_output()
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            records = load_snapshot(args.snapshot)
            print(json.dumps({"valid": True, **_snapshot_identity(records)}, ensure_ascii=False, indent=2))
        elif args.command == "summarize":
            _emit(summarize(load_snapshot(args.snapshot)), args.format, summary_markdown)
        else:
            _emit(compare(load_snapshot(args.older), load_snapshot(args.newer)), args.format, compare_markdown)
    except SnapshotError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
