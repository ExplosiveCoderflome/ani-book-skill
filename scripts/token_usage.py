#!/usr/bin/env python3
"""Record, validate, and summarize per-step model token usage."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# CLI output can include an absolute workspace path. On Windows that path can
# contain non-ASCII account names, so use UTF-8 even when the inherited console
# code page is not UTF-8.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")


SCHEMA_VERSION = 1
MEASUREMENTS = {"exact", "estimated", "unavailable"}
STATUSES = {"succeeded", "failed", "partial"}
TOKEN_FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_tokens",
    "total_tokens",
)
NAME = re.compile(r"^[a-z][a-z0-9_.-]{1,63}$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def relative_artifact(value: str | None) -> str | None:
    if value is None:
        return None
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("artifact must be a workspace-relative path without '..'")
    return path.as_posix()


def validate_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {"schema_version", "event_id", "recorded_at", "route", "step", "status", "measurement"}
    missing = sorted(required - record.keys())
    if missing:
        errors.append(f"missing required fields: {', '.join(missing)}")
        return errors
    if record["schema_version"] != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    for field in ("route", "step"):
        if not isinstance(record[field], str) or not NAME.fullmatch(record[field]):
            errors.append(f"{field} must match {NAME.pattern}")
    if record["status"] not in STATUSES:
        errors.append(f"status must be one of {sorted(STATUSES)}")
    measurement = record["measurement"]
    if measurement not in MEASUREMENTS:
        errors.append(f"measurement must be one of {sorted(MEASUREMENTS)}")
    try:
        uuid.UUID(str(record["event_id"]))
    except (ValueError, TypeError, AttributeError):
        errors.append("event_id must be a UUID")
    try:
        datetime.fromisoformat(str(record["recorded_at"]).replace("Z", "+00:00"))
    except ValueError:
        errors.append("recorded_at must be an ISO-8601 timestamp")
    for field in TOKEN_FIELDS:
        value = record.get(field)
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
            errors.append(f"{field} must be a non-negative integer or null")
    if measurement == "unavailable":
        if any(record.get(field) is not None for field in TOKEN_FIELDS):
            errors.append("unavailable records cannot contain token counts")
        if not record.get("reason"):
            errors.append("unavailable records require reason")
    else:
        if all(record.get(field) is None for field in ("input_tokens", "output_tokens", "total_tokens")):
            errors.append("measured records require input_tokens, output_tokens, or total_tokens")
        input_tokens = record.get("input_tokens")
        output_tokens = record.get("output_tokens")
        total_tokens = record.get("total_tokens")
        if input_tokens is not None and output_tokens is not None and total_tokens is not None:
            if input_tokens + output_tokens != total_tokens:
                errors.append("total_tokens must equal input_tokens + output_tokens")
        cached = record.get("cached_input_tokens")
        if cached is not None and input_tokens is not None and cached > input_tokens:
            errors.append("cached_input_tokens cannot exceed input_tokens")
        reasoning = record.get("reasoning_tokens")
        if reasoning is not None and output_tokens is not None and reasoning > output_tokens:
            errors.append("reasoning_tokens cannot exceed output_tokens")
    artifact = record.get("artifact")
    if artifact is not None:
        try:
            relative_artifact(artifact)
        except ValueError as exc:
            errors.append(str(exc))
    return errors


def usage_path(workspace: Path) -> Path:
    return workspace / "production" / "token-usage.jsonl"


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as temporary:
            json.dump(value, temporary, ensure_ascii=False, indent=2)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def read_records(workspace: Path) -> tuple[list[dict[str, Any]], list[str]]:
    path = usage_path(workspace)
    if not path.is_file():
        return [], [f"missing ledger: {path}"]
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, raw_line in enumerate(stream, start=1):
            if not raw_line.strip():
                continue
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                errors.append(f"line {line_number}: invalid JSON: {exc.msg}")
                continue
            if not isinstance(record, dict):
                errors.append(f"line {line_number}: record must be an object")
                continue
            for error in validate_record(record):
                errors.append(f"line {line_number}: {error}")
            records.append(record)
    return records, errors


def command_record(args: argparse.Namespace) -> int:
    workspace = args.workspace.resolve()
    if not workspace.is_dir():
        raise ValueError(f"workspace does not exist: {workspace}")
    total = args.total_tokens
    if total is None and args.input_tokens is not None and args.output_tokens is not None:
        total = args.input_tokens + args.output_tokens
    record = {
        "schema_version": SCHEMA_VERSION,
        "event_id": str(uuid.uuid4()),
        "recorded_at": utc_now(),
        "route": args.route,
        "step": args.step,
        "status": args.status,
        "measurement": args.measurement,
        "provider": args.provider,
        "model": args.model,
        "run_id": args.run_id,
        "request_id": args.request_id,
        "artifact": relative_artifact(args.artifact),
        "input_tokens": args.input_tokens,
        "cached_input_tokens": args.cached_input_tokens,
        "output_tokens": args.output_tokens,
        "reasoning_tokens": args.reasoning_tokens,
        "total_tokens": total,
        "reason": args.reason,
    }
    errors = validate_record(record)
    if errors:
        raise ValueError("; ".join(errors))
    path = usage_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(serialized)
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"recorded": True, "ledger": str(path), "event": record}, ensure_ascii=False, indent=2))
    return 0


def build_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    buckets: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "events": 0,
            "succeeded": 0,
            "failed": 0,
            "partial": 0,
            "exact_events": 0,
            "exact_tokens": 0,
            "estimated_events": 0,
            "estimated_tokens": 0,
            "unavailable_events": 0,
        }
    )

    def add(bucket: dict[str, Any], record: dict[str, Any]) -> None:
        bucket["events"] += 1
        bucket[record["status"]] += 1
        measurement = record["measurement"]
        bucket[f"{measurement}_events"] += 1
        if measurement in {"exact", "estimated"}:
            bucket[f"{measurement}_tokens"] += record.get("total_tokens") or 0

    total = buckets["__total__"]
    by_step: dict[str, dict[str, Any]] = {}
    by_model: dict[str, dict[str, Any]] = {}
    for record in records:
        add(total, record)
        step_key = f"{record['route']}.{record['step']}"
        step_bucket = by_step.setdefault(step_key, buckets[step_key])
        add(step_bucket, record)
        model_key = "/".join(filter(None, (record.get("provider"), record.get("model")))) or "unknown"
        model_bucket = by_model.setdefault(model_key, buckets[f"model:{model_key}"])
        add(model_bucket, record)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "totals": total,
        "by_step": dict(sorted(by_step.items())),
        "by_model": dict(sorted(by_model.items())),
    }


def command_validate(args: argparse.Namespace) -> int:
    records, errors = read_records(args.workspace.resolve())
    result = {"valid": not errors, "record_count": len(records), "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


def command_summarize(args: argparse.Namespace) -> int:
    workspace = args.workspace.resolve()
    records, errors = read_records(workspace)
    if errors:
        raise ValueError("; ".join(errors))
    summary = build_summary(records)
    if args.write:
        summary_path = workspace / "production" / "token-summary.json"
        atomic_write_json(summary_path, summary)
        summary["written_to"] = str(summary_path)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def add_token_arguments(parser: argparse.ArgumentParser) -> None:
    for field in TOKEN_FIELDS:
        parser.add_argument(f"--{field.replace('_', '-')}", type=int)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    record = subparsers.add_parser("record", help="append one model-generation usage event")
    record.add_argument("workspace", type=Path)
    record.add_argument("--route", required=True)
    record.add_argument("--step", required=True)
    record.add_argument("--status", choices=sorted(STATUSES), default="succeeded")
    record.add_argument("--measurement", choices=sorted(MEASUREMENTS), required=True)
    record.add_argument("--provider")
    record.add_argument("--model")
    record.add_argument("--run-id")
    record.add_argument("--request-id")
    record.add_argument("--artifact")
    record.add_argument("--reason")
    add_token_arguments(record)
    record.set_defaults(handler=command_record)

    validate = subparsers.add_parser("validate", help="validate the usage ledger")
    validate.add_argument("workspace", type=Path)
    validate.set_defaults(handler=command_validate)

    summarize = subparsers.add_parser("summarize", help="aggregate usage without mixing exact and estimated totals")
    summarize.add_argument("workspace", type=Path)
    summarize.add_argument("--write", action="store_true", help="write production/token-summary.json")
    summarize.set_defaults(handler=command_summarize)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.handler(args)
    except ValueError as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
