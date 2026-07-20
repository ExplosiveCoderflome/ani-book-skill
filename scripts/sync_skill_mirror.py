#!/usr/bin/env python3
"""Check or synchronize an installed Skill mirror without deleting extra files."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


SURFACES = ("SKILL.md", "requirements.txt", "agents", "assets", "scripts", "references")


def included_files(root: Path) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for surface in SURFACES:
        path = root / surface
        if path.is_file():
            result[path.relative_to(root).as_posix()] = path
        elif path.is_dir():
            for candidate in path.rglob("*"):
                if not candidate.is_file() or "__pycache__" in candidate.parts or candidate.suffix == ".pyc":
                    continue
                result[candidate.relative_to(root).as_posix()] = candidate
    return result


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare(source: Path, mirror: Path) -> dict[str, list[str]]:
    source_files = included_files(source)
    mirror_files = included_files(mirror) if mirror.is_dir() else {}
    missing = sorted(set(source_files) - set(mirror_files))
    changed = sorted(
        relative
        for relative in set(source_files) & set(mirror_files)
        if digest(source_files[relative]) != digest(mirror_files[relative])
    )
    extra = sorted(set(mirror_files) - set(source_files))
    return {"missing": missing, "changed": changed, "extra": extra}


def command_check(args: argparse.Namespace) -> int:
    result = compare(args.source.resolve(), args.mirror.resolve())
    result["in_sync"] = not result["missing"] and not result["changed"]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["in_sync"] else 1


def command_sync(args: argparse.Namespace) -> int:
    source = args.source.resolve()
    mirror = args.mirror.resolve()
    if source == mirror:
        raise ValueError("source and mirror must be different directories")
    mirror.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for relative, path in included_files(source).items():
        target = mirror / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.is_file() or digest(path) != digest(target):
            shutil.copy2(path, target)
            copied.append(relative)
    result = compare(source, mirror)
    print(json.dumps({"copied": sorted(copied), **result}, ensure_ascii=False, indent=2))
    return 0 if not result["missing"] and not result["changed"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name, handler in (("check", command_check), ("sync", command_sync)):
        command = commands.add_parser(name)
        command.add_argument("source", type=Path)
        command.add_argument("mirror", type=Path)
        command.set_defaults(handler=handler)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if not args.source.is_dir():
            raise ValueError(f"source directory not found: {args.source}")
        return args.handler(args)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
