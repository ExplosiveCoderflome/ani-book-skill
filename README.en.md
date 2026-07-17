# Ani Book Skill

[![Validate](https://github.com/ExplosiveCoderflome/ani-book-skill/actions/workflows/validate.yml/badge.svg)](https://github.com/ExplosiveCoderflome/ani-book-skill/actions/workflows/validate.yml)
[中文](README.md) · [Changelog](docs/releases/release-notes.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

> Turn “I want to write a long novel” into a writing system that can keep going.

**Ani Book Skill** is a Codex workflow for long-form Chinese fiction. It connects market research, story design, chapter production, revision, and durable continuity into a local, recoverable process—so an author can still know what matters when the manuscript is dozens of chapters deep.

![Ani Book Skill workflow: idea and research, story architecture, drafting and review, continuity storage, and the next chapter loop](assets/workflow-hero.png)

*From the first spark to the next chapter: every commit makes the novel more coherent, not the context more chaotic.*

## What it helps you do

| Challenge | Workflow | Durable output |
| --- | --- | --- |
| Find a viable direction | Analyze public chart metadata without reading novel prose | Snapshots, reports, opportunity cards |
| Turn an idea into a serial engine | Confirm only the few creative choices that matter, then plan volumes and chapter obligations | Brief, bible, cast, volume plan, beats |
| Keep chapters from drifting | Plan → bounded context → complete draft → humanization → review → continuity commit | Prose, review, delta, next action |
| Keep long-running memory affordable | Treat YAML as authority and SQLite as a rebuildable index | Checkpoints, readable views, bounded context |

## Why this is more than a prompt collection

- Start with reader promise before expanding the setting.
- Commit one accepted chapter at a time; unreviewed candidates never become story facts.
- Preserve facts, resources, promises, character state, and relationships with stable IDs and chapter evidence.
- Keep manuscripts and research local, inspectable, editable, and portable.

## Start with one prompt

```text
Use $produce-long-form-novel to plan a long novel from my idea.
```

For an existing workspace:

```text
Use $produce-long-form-novel to continue novels/<novel-name>/ and determine the next safe production step.
```

For market research or authorized analysis:

```text
Use $produce-long-form-novel to analyze recent xianxia chart composition and create opportunity cards.
```

```text
Use $produce-long-form-novel to deconstruct this authorized novel text; establish coverage, segment notes, and an overview first.
```

## Built for the long run

```text
Idea → reader promise → world and cast → volume payoff
     → chapter contract → complete prose → review
     → continuity commit → next chapter
```

Migrated workspaces use YAML as the sole continuity authority for facts, promises, resources, dynamic character state, and relationships. Markdown ledgers are generated views; SQLite only accelerates retrieval and can be deleted or rebuilt without changing story truth. This keeps context bounded as the novel grows.

## Install and use local tools

Install this repository as a personal Codex Skill, then invoke `$produce-long-form-novel`. See [SKILL.md](SKILL.md) for the complete workflow contract.

Python 3.10+ is required. Install the YAML continuity dependency:

```powershell
python -m pip install -r requirements.txt
```

```powershell
python scripts/export_novel_txt.py novels/<novel-name>
python scripts/check_continuity_workspace.py novels/<novel-name>
python scripts/continuity_store.py migrate novels/<novel-name> --dry-run
python scripts/analysis_retrieval.py build analyses/<analysis-name>
python scripts/trend_snapshot.py validate trends/<scope>/snapshots/<date>/<platform>-<chart>.jsonl
```

`novels/`, `analyses/`, and `trends/` are ignored by default to protect private manuscripts, source texts, and research snapshots.

## Clear boundaries

- Chart research uses public metadata only; it does not infer guaranteed trends from a single snapshot.
- Reference analysis requires authorized material and produces transferable mechanisms, not close imitation.
- This is a writing workflow, not a hosting platform or a replacement for author judgment.

## Origin and license

This standalone, documentation-first Skill was distilled by the maintainer of [AI-Novel-Writing-Assistant](https://github.com/ExplosiveCoderflome/AI-Novel-Writing-Assistant) from long-form production experience. It does not include or depend on that project's frontend, backend, database, or runtime services.

Repository files are released under the [Apache License 2.0](LICENSE). See the [changelog](docs/releases/release-notes.md) for the latest updates.
