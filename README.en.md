# Ani Book Skill

[中文](README.md) · [Changelog](docs/releases/release-notes.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

Ani Book Skill is a Codex workflow for producing long-form Chinese web novels, analyzing hot-genre rankings, and deconstructing authorized reference works. It turns ranking research, story planning, drafting, review, and continuity into editable, recoverable artifacts.

## Origin and relationship

This project was distilled by the maintainer of [AI-Novel-Writing-Assistant](https://github.com/ExplosiveCoderflome/AI-Novel-Writing-Assistant) from its long-form production workflow, creative methodology, and practical experience. It packages reusable writing practices as a lightweight, documentation-first Codex Skill.

- This is a standalone Skill, not a mirror or runtime distribution of the original project. It does not include that project's frontend, backend, database, agent services, or desktop code.
- The [Apache License 2.0](LICENSE) applies only to the files in this repository. Refer to the original repository for its license and commercial-authorization policy.
- The original project is cited for origin and attribution only; this Skill has no runtime dependency on any version of it.

## Highlights

- Move from an idea to a novel brief, story bible, world, cast, volume plan, and chapters.
- Guide beginners through progressive confirmation: ask only 2–3 high-impact choices per round, explain one recommendation, and remember decisions that are confirmed, delegated to AI, or marked unnecessary.
- Analyze titles, tags, and synopses from public official charts to describe current chart composition, compare like-for-like dates, and create 3–5 opportunity cards without reading novel prose.
- Deconstruct authorized local texts, accessible online sources, or your own manuscript into evidence-backed sections, coverage maps, and safely reusable mechanism cards.
- Query long analyses through a lightweight BookGraph, local SQLite text search, and optional vector fusion without bundling an embedding model or vector database.
- Preserve long-form continuity with chapter contracts, context packages, and readable ledgers.
- Optionally migrate continuity to YAML authority with generated Markdown views, a rebuildable SQLite index, and bounded context assembly.
- Revise and review drafts while protecting accepted facts and author-written prose.
- Export completed chapters to TXT and check workspace continuity with included Python tools.
- Keep content local and portable with Markdown and YAML.

## Use it

Install this repository as a personal Codex Skill, then invoke it in Codex:

```text
Use $produce-long-form-novel to plan a long novel from my idea.
```

For an underspecified idea, the skill presents a small set of choices—such as audience channel, platform shape, and primary reader reward—instead of a full questionnaire. Recommendations may be previewed, but they do not become authoritative planning inputs until you confirm them or delegate the decision to AI for the current project.

Read [SKILL.md](SKILL.md) for the complete workflow contract. The primary documentation is maintained in Chinese because the workflow targets Chinese fiction.

For reference analysis, invoke the same skill with an authorized source and ask it to establish scope, segment notes, and an overview before deeper conclusions.

For hot-genre research, specify a platform and audience channel. The skill defaults to the top 20 entries from up to three charts and falls back to user-provided screenshots, tables, or text when public pages are unavailable.

## Local tools

Python 3.10+ is required. Install the YAML continuity dependency with `python -m pip install -r requirements.txt`.

```powershell
python scripts/export_novel_txt.py novels/<novel-name>
python scripts/check_continuity_workspace.py novels/<novel-name>
python scripts/continuity_store.py migrate novels/<novel-name> --dry-run
python scripts/analysis_retrieval.py build analyses/<analysis-name>
python scripts/analysis_retrieval.py search analyses/<analysis-name> "升级循环"
python scripts/trend_snapshot.py validate trends/<scope>/snapshots/<date>/<platform>-<chart>.jsonl
python scripts/trend_snapshot.py summarize <snapshot.jsonl> --format markdown
python scripts/trend_snapshot.py compare <older.jsonl> <newer.jsonl> --format json
```

`novels/`, `analyses/`, and `trends/` are ignored by default to protect manuscripts, analysis sources, and ranking research. Trend snapshots are metadata-only and never enable BookGraph, RAG, or vector retrieval. Put only authorized, sanitized examples in `examples/` if you choose to publish them.

## Contributing and license

Please read [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and [SECURITY.md](SECURITY.md). This project is released under the [Apache License 2.0](LICENSE).
