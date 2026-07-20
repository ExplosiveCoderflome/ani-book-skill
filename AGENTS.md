# Repository Guidance

## Product Boundary

- Keep this repository a Codex-native Skill project. Codex is the only creative generation and judgment engine; do not add model-provider SDKs, a web API, a database authority, or a custom agent runtime.
- This repository is driven by Codex itself, not by `AI-Novel-Writing-Assistant`; that project may be read only for ideas and is never a runtime, submodule, or production dependency.
- Treat Skills as process contracts. Keep Python limited to deterministic state, validation, indexes, conflict detection, and export; provider/model metadata is diagnostics only when the Codex host exposes it.
- Treat `SKILL.md`, `references/`, deterministic scripts, and local Markdown/YAML workspaces as the product surface.
- Use `D:\code\AI-Novel-Writing-Assistant-v2` only as a read-only source of production ideas. Never create a runtime dependency on it.

## Data Safety

- Treat user-edited artifacts and accepted prose as protected. Mark dependent unwritten artifacts `stale`; never rewrite protected content to repair state.
- Keep YAML and accepted Markdown authoritative. SQLite, summaries, rendered ledgers, and exports are rebuildable derivatives.
- Back up `novel-state.yaml` before schema migration and use atomic replacement for state writes.

## Development

- Use Python 3.10 or newer and UTF-8 explicitly.
- Add or update tests for every deterministic workflow change.
- Run `python -m compileall -q scripts`, `python -m unittest discover -s tests -v`, and the Skill quick validator (`python -X utf8 <skill-creator>/scripts/quick_validate.py .` on Windows) before completion.
- Keep `G:\documents\ani-book-skill\ani-book-skill` authoritative. The sibling `produce-long-form-novel` directory is an installation mirror and must only be synchronized after verification.
- On the first Skill run in a task, and whenever the Skill surface changes, check source/mirror currency before creative or stateful production with `python scripts/sync_skill_mirror.py check <source-skill-directory> <installed-skill-directory>`.
- Treat `missing` or `changed` results as an explicit maintenance finding; do not silently run against a stale installed mirror. After compile, tests, and the Skill quick validator pass, synchronize with `python scripts/sync_skill_mirror.py sync <source-skill-directory> <installed-skill-directory>` and rerun `check`.
- If the configured authoritative source path is unavailable, report that blocker and identify the explicit fallback source before syncing; never silently replace the authority.
