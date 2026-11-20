"""Verify an unabridged, reviewed manuscript before delivering the complete book."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

from export_novel_txt import chapter_content, safe_filename


REVIEW_PATH = "production/book-review.md"


def body_han_count(body: str) -> int:
    prose = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    lines = (line for line in prose.splitlines() if not re.match(r"^ {0,3}#{1,6}(?:\s|$)", line))
    return sum(char == "〇" or unicodedata.name(char, "").startswith(("CJK UNIFIED IDEOGRAPH-", "CJK COMPATIBILITY IDEOGRAPH-"))
               for line in lines for char in line)


def accepted_chapters(workspace: Path, state: dict, last: int):
    from novelctl import accepted_review_inputs, artifact_location, chapter_target, ensure_dependencies_ready, step_from_key

    used = set()
    artifacts = state["artifacts"]
    for number in range(1, last + 1):
        target = chapter_target(number)
        review, delta = target + "_review", target + "_delta"
        ensure_dependencies_ready(artifacts, [review, delta], workspace)
        if artifacts[review].get("review_decision") != "accepted":
            raise ValueError(f"{target}: chapter review is not accepted")
        snapshot = accepted_review_inputs(workspace, state, target)
        prose = next(item for key, item in snapshot.items() if step_from_key(key) in {
            "chapter_draft", "humanization_revision", "chapter_repair"})
        path = artifact_location(workspace, prose).resolve()
        if path in used:
            raise ValueError(f"{target}: chapter prose is already used by another chapter")
        used.add(path)
        heading, body = chapter_content(number, path)
        if not body.strip() or all(re.match(r"^#{1,6}(?:\s|$)", line.strip()) for line in body.splitlines() if line.strip()):
            raise ValueError(f"{target}: chapter has no prose")
        yield number, heading, body, [snapshot, artifacts[review]["sha256"], artifacts[delta]["sha256"]]


def length_progress(workspace: Path, state: dict) -> dict:
    from novelctl import chapter_number

    last = chapter_number(state["continuity"].get("last_committed_chapter")) or 0
    counts = {number: body_han_count(body) for number, _, body, _ in accepted_chapters(workspace, state, last)}
    total = sum(counts.values())
    minimum = state["novel"].get("minimum_body_han")
    return {"body_han": total, "minimum_body_han": minimum, "remaining_body_han": max(0, minimum - total) if minimum else None,
            "chapter_body_han": counts}


def manuscript(workspace: Path, state: dict) -> tuple[str, str, int]:
    from novelctl import chapter_number, ensure_dependencies_ready, step_from_key

    novel = state["novel"]
    end = novel.get("final_chapter")
    last = chapter_number(state["continuity"].get("last_committed_chapter"))
    if type(end) is not int or end < 1 or last != end:
        raise ValueError("finish-book requires a declared and committed final chapter")
    parts = [novel["title"]]
    bindings = []
    artifacts = state["artifacts"]
    planning_keys = ["novel_brief", "story_bible", "volume_strategy"]
    planning_keys.extend(key for key in artifacts if step_from_key(key) in {"volume_skeleton", "beat_sheet"}
                         and artifacts[key].get("status") == "ready")
    ensure_dependencies_ready(artifacts, planning_keys, workspace)
    planning = {key: artifacts[key]["sha256"] for key in planning_keys}
    total = 0
    for _, heading, body, binding in accepted_chapters(workspace, state, end):
        parts.append(f"{heading}\n\n{body}")
        bindings.append(binding)
        total += body_han_count(body)
    text = "\n\n".join(parts) + "\n"
    evidence = [novel.get("idea"), planning, bindings, text]
    minimum = novel.get("minimum_body_han")
    if minimum is not None:
        if total < minimum:
            raise ValueError(f"accepted prose has {total} Han characters; minimum {minimum}, short by {minimum - total}")
        evidence.append({"minimum_body_han": minimum})
    signature = json.dumps(evidence, ensure_ascii=False, sort_keys=True)
    return text, hashlib.sha256(signature.encode("utf-8")).hexdigest(), total


def finish(workspace: Path, state: dict, reviewed_version: str | None) -> dict:
    from novelctl import atomic_write_text, file_sha256

    if state["director"].get("status") == "blocked":
        raise ValueError("resolve the director blocker before finishing the book")
    text, version, total = manuscript(workspace, state)
    marker = f"manuscript-version: {version}"
    if reviewed_version is None:
        return {"final_chapter": state["novel"]["final_chapter"], "body_han": total, "version": version,
                "review": REVIEW_PATH, "review_marker": marker}
    if version != reviewed_version:
        raise ValueError("manuscript changed since whole-book review; check and review again")
    review = workspace / REVIEW_PATH
    if not review.is_file():
        raise ValueError(f"record the conclusion of the whole-book review in {REVIEW_PATH}")
    lines = review.read_text(encoding="utf-8-sig").splitlines()
    markers = [line for line in lines if line.startswith("manuscript-version:")]
    if markers != [marker] or not any(line.strip() and line != marker for line in lines):
        raise ValueError(f"record the review conclusion and current review_marker in {REVIEW_PATH}")
    name = safe_filename(state["novel"]["title"])
    relative = f"exports/{name}-全本-{version[:12]}.txt"
    output = workspace / relative
    rendered = "\ufeff" + text
    digest = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    if output.exists():
        if file_sha256(output) != digest:
            raise ValueError(f"export has been edited; preserve it at another path first: {relative}")
    else:
        atomic_write_text(output, rendered)
    return {"version": version, "path": relative, "body_han": total, "sha256": digest, "review_sha256": file_sha256(review)}


def current(workspace: Path, state: dict) -> bool:
    from novelctl import artifact_location, file_sha256

    receipt = state["novel"]["completion"]
    if not isinstance(receipt, dict):
        return False
    try:
        return (file_sha256(workspace / REVIEW_PATH) == receipt["review_sha256"]
                and file_sha256(artifact_location(workspace, receipt)) == receipt["sha256"]
                and manuscript(workspace, state)[1] == receipt["version"])
    except (KeyError, OSError, ValueError):
        return False
