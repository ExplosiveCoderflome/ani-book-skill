#!/usr/bin/env python3
"""Estimate source-token range from novel length before book analysis starts."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


SEGMENT_TARGET_CHARS = 10_000
# ponytail: 8 segments ≈ 80k chars; raise only if short books start prompting.
CONFIRM_SEGMENT_THRESHOLD = 8
TEXT_SUFFIXES = {".txt", ".md", ".text"}


def configure_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


def read_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"无法用 utf-8 或 gb18030 读取：{path}")


def source_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise ValueError(f"未找到原文：{path}")
    if (path / "analysis-state.yaml").is_file():
        raise ValueError("请传入小说原文文件或章节目录，不要传入 analyses 工作区")
    files = [
        item
        for item in path.rglob("*")
        if item.is_file() and item.suffix.lower() in TEXT_SUFFIXES and "retrieval" not in item.parts
    ]
    if not files:
        raise ValueError(f"目录中没有 txt 或 md 原文：{path}")
    return sorted(files)


def measure(text: str) -> dict[str, int]:
    cjk = punctuation = other = 0
    for char in text:
        if char.isspace():
            continue
        code = ord(char)
        if 0x3400 <= code <= 0x9FFF:
            cjk += 1
        elif 0x3000 <= code <= 0x303F or 0xFF00 <= code <= 0xFFEF:
            punctuation += 1
        else:
            other += 1
    # ponytail: CJK 1–2 and punctuation 1 token/char span common chat tokenizers; use a model tokenizer when a billable count is required.
    return {
        "cjk_chars": cjk,
        "punctuation_chars": punctuation,
        "other_chars": other,
        "content_chars": cjk + punctuation + other,
        "source_tokens_low": cjk + punctuation + other // 4,
        "source_tokens_high": cjk * 2 + punctuation + (other + 1) // 2,
    }


def estimate(path: Path) -> dict[str, object]:
    files = source_files(path)
    totals = {
        "cjk_chars": 0,
        "punctuation_chars": 0,
        "other_chars": 0,
        "content_chars": 0,
        "source_tokens_low": 0,
        "source_tokens_high": 0,
    }
    for file in files:
        counts = measure(read_text(file))
        for key in totals:
            totals[key] += counts[key]
    if totals["content_chars"] == 0:
        raise ValueError("原文没有可读字符")
    planned = max(1, math.ceil(totals["content_chars"] / SEGMENT_TARGET_CHARS))
    confirm_required = planned >= CONFIRM_SEGMENT_THRESHOLD
    return {
        "measurement": "length_estimate",
        "source": str(path),
        "file_count": len(files),
        "segment_target_chars": SEGMENT_TARGET_CHARS,
        "planned_segments": planned,
        "confirm_required": confirm_required,
        "confirm_segment_threshold": CONFIRM_SEGMENT_THRESHOLD,
        **totals,
    }


def render_text(data: dict[str, object]) -> str:
    return "\n".join(
        (
            "原文预估（length_estimate，不是模型账单）",
            f"文件数：{data['file_count']}",
            (
                f"内容字符：{data['content_chars']}"
                f"（汉字 {data['cjk_chars']}，标点 {data['punctuation_chars']}，其他 {data['other_chars']}）"
            ),
            f"计划切段：{data['planned_segments']}（按约 {data['segment_target_chars']} 字一段）",
            f"原文 token 区间：{data['source_tokens_low']}–{data['source_tokens_high']}",
            "笔记阶段大约把原文读入模型 1 遍，输入落在这个区间。",
            "后续总览和专项读的是笔记，不要把这个区间再乘小节数。",
            (
                f"范围确认：必须先问用户选全文拆解还是部分拆解（切段 ≥ {data['confirm_segment_threshold']}）"
                if data["confirm_required"]
                else "范围确认：篇幅未过阈值，用户未指定时可按全文拆解继续。"
            ),
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="按原文长度预估拆书前的 token 区间。")
    parser.add_argument("source", type=Path, help="小说原文文件，或只含章节 txt/md 的目录")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_utf8_output()
    args = build_parser().parse_args(argv)
    try:
        data = estimate(args.source.expanduser().resolve())
    except (OSError, ValueError) as error:
        print(f"预估失败：{error}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(render_text(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
