#!/usr/bin/env python3
"""Validate a novel workspace's continuity assets without modifying it."""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path


SOURCE_HASH = re.compile(
    r"<!--\s*source-hash:\s*([^|]+?)\s*\|\s*([0-9A-Fa-f]{64})\s*-->",
)
SCHEMA_VERSION = re.compile(r"^schema_version:\s*(\d+)\s*$", re.MULTILINE)

REQUIRED_FILES = (
    "continuity/baseline.md",
    "continuity/fact-ledger.md",
    "continuity/payoff-ledger.md",
    "continuity/resource-ledger.md",
    "production/recovery.md",
    "production/quality-debt.md",
)
REQUIRED_CONTINUITY_KEYS = (
    "baseline_chapter",
    "last_committed_chapter",
    "recovery_path",
    "quality_debt_open_count",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def markdown_files(workspace: Path) -> list[Path]:
    roots = (
        workspace / "continuity",
        workspace / "context-packages",
        workspace / "production",
    )
    files: list[Path] = []
    for root in roots:
        if root.exists():
            files.extend(root.rglob("*.md"))
    return sorted(files)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check continuity assets and source fingerprints without writing files.",
    )
    parser.add_argument("workspace", type=Path, help="Novel workspace path")
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    errors: list[str] = []
    stale: list[str] = []
    state_path = workspace / "novel-state.yaml"

    if not state_path.is_file():
        errors.append("missing novel-state.yaml")
    else:
        state_text = state_path.read_text(encoding="utf-8")
        version_match = SCHEMA_VERSION.search(state_text)
        if not version_match or int(version_match.group(1)) < 2:
            errors.append("novel-state.yaml must use schema_version: 2 or newer")
        for key in REQUIRED_CONTINUITY_KEYS:
            if not re.search(rf"^\s{{2}}{re.escape(key)}:\s*", state_text, re.MULTILINE):
                errors.append(f"novel-state.yaml is missing continuity.{key}")

    for relative in REQUIRED_FILES:
        if not (workspace / relative).is_file():
            errors.append(f"missing {relative}")

    baseline = workspace / "continuity/baseline.md"
    if baseline.is_file() and "基线章节" not in baseline.read_text(encoding="utf-8"):
        errors.append("baseline.md must name its baseline chapter")

    for artifact in markdown_files(workspace):
        text = artifact.read_text(encoding="utf-8")
        for source_text, expected_hash in SOURCE_HASH.findall(text):
            source_parts = [
                part for part in source_text.strip().replace("\\", "/").split("/") if part
            ]
            source = workspace.joinpath(*source_parts)
            label = artifact.relative_to(workspace).as_posix()
            if not source.is_file():
                errors.append(f"{label}: source is missing: {source_text.strip()}")
                continue
            actual_hash = sha256(source)
            if actual_hash != expected_hash.upper():
                stale.append(f"{label}: {source_text.strip()} changed")

    if errors:
        print("CONTINUITY CHECK FAILED")
        for item in errors:
            print(f"- {item}")
        if stale:
            print("STALE DEPENDENCIES")
            for item in stale:
                print(f"- {item}")
        return 1

    if stale:
        print("CONTINUITY CHECK: STALE")
        for item in stale:
            print(f"- {item}")
        print("Protect the changed prose, mark dependent artifacts stale, then rebuild them.")
        return 2

    print("CONTINUITY CHECK: OK")
    print("All required assets exist and recorded stable sources still match their fingerprints.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
