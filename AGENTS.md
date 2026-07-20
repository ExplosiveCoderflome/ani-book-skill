# Repository Guidance

## Product Boundary

- Keep this repository a Codex-native Skill project. Codex is the only creative generation and judgment engine; do not add model-provider SDKs, a web API, a database authority, or a custom agent runtime.
- Treat `SKILL.md`, `references/`, deterministic scripts, and local Markdown/YAML workspaces as the product surface.
- Use `D:\code\AI-Novel-Writing-Assistant-v2` only as a read-only source of production ideas. Never create a runtime dependency on it.

## Data Safety

- Treat user-edited artifacts and accepted prose as protected. Mark dependent unwritten artifacts `stale`; never rewrite protected content to repair state.
- Keep YAML and accepted Markdown authoritative. SQLite, summaries, rendered ledgers, and exports are rebuildable derivatives.
- Back up `novel-state.yaml` before schema migration and use atomic replacement for state writes.

## Development

- Use Python 3.10 or newer and UTF-8 explicitly.
- Add or update tests for every deterministic workflow change.
- Run `python -m compileall -q scripts`, `python -m unittest discover -s tests -v`, and the Skill quick validator before completion.
- Keep `G:\documents\ani-book-skill\ani-book-skill` authoritative. The sibling `produce-long-form-novel` directory is an installation mirror and must only be synchronized after verification.
