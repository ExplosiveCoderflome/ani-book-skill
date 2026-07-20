from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml


CHAPTER_PATTERN = re.compile(r"^chapter-(\d+)$")
INVALID_FILENAME = re.compile(r'[<>:"/\\|?*]')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="按章节编号导出小说正文为 TXT。")
    parser.add_argument("workspace", type=Path, help="小说工作区路径")
    parser.add_argument("--start", type=int, help="起始章节编号")
    parser.add_argument("--end", type=int, help="结束章节编号")
    parser.add_argument(
        "--source",
        choices=("auto", "humanized", "draft"),
        default="auto",
        help="正文来源：auto 优先二稿，其次初稿",
    )
    parser.add_argument("--output", type=Path, help="自定义输出 TXT 路径")
    parser.add_argument("--dry-run", action="store_true", help="只显示将要导出的章节")
    parser.add_argument("--stable-only", action="store_true", help="仅导出状态中已提交连续性的稳定正文")
    return parser.parse_args()


def read_book_title(workspace: Path) -> str:
    state_file = workspace / "novel-state.yaml"
    if state_file.exists():
        text = state_file.read_text(encoding="utf-8")
        match = re.search(r'^\s*title:\s*["\']?(.+?)["\']?\s*$', text, re.MULTILINE)
        if match:
            return match.group(1).strip().strip('"\'')
    return workspace.name


def safe_filename(value: str) -> str:
    cleaned = INVALID_FILENAME.sub("-", value).strip().rstrip(".")
    return cleaned or "novel"


def choose_draft(chapter_dir: Path, source: str) -> Path | None:
    choices = {
        "auto": ("draft-humanized.md", "draft.md"),
        "humanized": ("draft-humanized.md",),
        "draft": ("draft.md",),
    }
    for filename in choices[source]:
        candidate = chapter_dir / filename
        if candidate.is_file():
            return candidate
    return None


def stable_export_projection(workspace: Path) -> tuple[set[int], set[str]]:
    state_file = workspace / "novel-state.yaml"
    if not state_file.is_file():
        raise ValueError("稳定导出需要 novel-state.yaml")
    state = yaml.safe_load(state_file.read_text(encoding="utf-8")) or {}
    artifacts = state.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("稳定导出需要有效的 artifacts 状态")
    stable_chapters: set[int] = set()
    ready_paths: set[str] = set()
    for key, artifact in artifacts.items():
        if not isinstance(artifact, dict) or artifact.get("status") != "ready":
            continue
        path = artifact.get("path")
        if isinstance(path, str):
            ready_paths.add(Path(path).as_posix())
        match = re.fullmatch(r"chapter_(\d+)_delta", str(key))
        if match:
            stable_chapters.add(int(match.group(1)))
    return stable_chapters, ready_paths


def chapter_content(chapter_number: int, draft_file: Path) -> tuple[str, str]:
    content = draft_file.read_text(encoding="utf-8").replace("\r\n", "\n").strip()
    heading_match = re.match(r"^#\s+(.+?)\s*\n+", content)
    if heading_match:
        return heading_match.group(1).strip(), content[heading_match.end() :].strip()
    return f"第{chapter_number}章", content


def collect_chapters(args: argparse.Namespace) -> tuple[list[tuple[int, Path, str, str]], list[str]]:
    chapters_root = args.workspace / "chapters"
    if not chapters_root.is_dir():
        raise ValueError(f"未找到章节目录：{chapters_root}")
    if args.start is not None and args.start < 1:
        raise ValueError("--start 必须大于 0")
    if args.end is not None and args.end < 1:
        raise ValueError("--end 必须大于 0")
    if args.start is not None and args.end is not None and args.start > args.end:
        raise ValueError("--start 不能大于 --end")

    collected: list[tuple[int, Path, str, str]] = []
    skipped: list[str] = []
    stable_chapters: set[int] | None = None
    ready_paths: set[str] | None = None
    if args.stable_only:
        stable_chapters, ready_paths = stable_export_projection(args.workspace)
    for chapter_dir in sorted(chapters_root.iterdir(), key=lambda item: item.name):
        if not chapter_dir.is_dir():
            continue
        match = CHAPTER_PATTERN.match(chapter_dir.name)
        if not match:
            continue
        number = int(match.group(1))
        if args.start is not None and number < args.start:
            continue
        if args.end is not None and number > args.end:
            continue
        if stable_chapters is not None and number not in stable_chapters:
            skipped.append(f"第{number:03d}章：连续性尚未稳定提交")
            continue
        draft_file = choose_draft(chapter_dir, args.source)
        if draft_file is None:
            skipped.append(f"第{number:03d}章：缺少所选正文来源")
            continue
        relative_draft = draft_file.relative_to(args.workspace).as_posix()
        if ready_paths is not None and relative_draft not in ready_paths:
            skipped.append(f"第{number:03d}章：正文状态不是 ready")
            continue
        heading, body = chapter_content(number, draft_file)
        if not body:
            skipped.append(f"第{number:03d}章：正文为空")
            continue
        collected.append((number, draft_file, heading, body))
    return collected, skipped


def default_output(workspace: Path, title: str, chapters: list[tuple[int, Path, str, str]]) -> Path:
    first = chapters[0][0]
    last = chapters[-1][0]
    filename = f"{safe_filename(title)}-已生成章节-{first:03d}至{last:03d}.txt"
    return workspace / "exports" / filename


def run() -> int:
    args = parse_args()
    workspace = args.workspace.expanduser().resolve()
    if not workspace.is_dir():
        raise ValueError(f"未找到小说工作区：{workspace}")
    args.workspace = workspace
    chapters, skipped = collect_chapters(args)
    if not chapters:
        raise ValueError("没有可导出的章节正文")

    title = read_book_title(workspace)
    output = args.output.expanduser().resolve() if args.output else default_output(workspace, title, chapters)
    chapter_lines = [f"第{number:03d}章：{draft_file.name}" for number, draft_file, _, _ in chapters]

    if args.dry_run:
        print("将导出：")
        print("\n".join(chapter_lines))
        if skipped:
            print("跳过：")
            print("\n".join(skipped))
        print(f"输出路径：{output}")
        return 0

    parts = [title]
    for _, _, heading, body in chapters:
        parts.append(f"{heading}\n\n{body}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n\n".join(parts).strip() + "\n", encoding="utf-8-sig")

    total_characters = sum(len(body) for _, _, _, body in chapters)
    print(f"已导出 {len(chapters)} 章，正文 {total_characters} 字符。")
    print(f"输出文件：{output}")
    print("来源：")
    print("\n".join(chapter_lines))
    if skipped:
        print("跳过：")
        print("\n".join(skipped))
    return 0


def main() -> None:
    try:
        raise SystemExit(run())
    except ValueError as error:
        print(f"导出失败：{error}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
