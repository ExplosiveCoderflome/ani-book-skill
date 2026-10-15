<div align="center">

# Ani Book Skill

**Keep ideas, research, and long-form fiction moving in Codex.**

From finding a direction and planning a book to finishing chapters, preserving continuity, writing fanfic, and reusing canon across books.<br>
Your creative work remains in editable local files, with evidence and a clear next step.

[![Validate](https://github.com/ExplosiveCoderflome/ani-book-skill/actions/workflows/validate.yml/badge.svg)](https://github.com/ExplosiveCoderflome/ani-book-skill/actions/workflows/validate.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

[Get started](#get-started) · [Capabilities](#what-you-can-do) · [Local reader](#local-reader) · [Changelog](docs/releases/release-notes.md) · [中文](README.md)

</div>

![A creative loop from idea and story structure to chapter review and durable continuity](assets/workflow-hero.png)

> **In short:** Codex handles understanding, planning, writing, and judgment. The Skill defines the workflow. Local tools handle state, validation, retrieval, and export. The author can always inspect and edit the Markdown / YAML source.

## What you can do

| Starting point | Result |
| --- | --- |
| **No story yet** | If you explicitly have no idea, review five opening seeds with different creative angles. For a vague direction, first choose the audience channel, publishing format, and main reader reward; then compare two distinct book-brief previews. |
| **Looking for a promising genre** | Turn public chart metadata, such as titles, tags, and descriptions, into snapshots, trend reports, and opportunity cards. |
| **Analyzing a reference book** | Estimate the length and segmentation of an authorized text, choose full or partial coverage, then build evidence-based segment notes, character cards, and searchable craft mechanisms using a book-specific analysis lens. |
| **Writing fanfic** | Work from authorized facts within the read scope. Continue from the last fully documented chapter ending or write a new story using the established canon. Complete `fanfic-handoff.md` before entering a separate novel workspace. |
| **Serializing a long novel** | Move from the story engine and volume plan to complete chapter prose, humanization, review, continuity updates, and a recoverable next action. |
| **Keeping a consistent voice** | Distill an editable style contract from your own writing, accepted chapters, or authorized analysis; apply it across drafting, anti-template revision, review, and targeted repair. |
| **Writing a series or shared universe** | Reuse accepted assets through `fork` / `sync`, check canon timelines and impact, and keep publication and conflict decisions with the author. |

### Turn research into writing decisions

A reference analysis is more than a long report. The size estimate helps you choose a practical reading scope. `analysis-lens.md` compares core reader promises first, then keeps the subject matter, psychological progression, relationship structure, and surface payoff axes separate. Segment notes and character cards retain evidence, while retrieval helps find it again. Source text is used only for authorized analysis; search results do not replace verifiable notes.

The local reader's analysis dashboard shows planned and actual coverage, gaps, focused analyses, mechanisms, and evidence health. It can prepare a request for a target novel and chapter. Codex then proposes an **original adaptation**, validates pinned references, adds bounded craft guidance to chapter context, and checks the outcome during review. See the [analysis guide](references/book-analysis.md), [retrieval guide](references/book-analysis-retrieval.md), and [analysis-to-novel workflow](references/analysis-to-novel.md).

### Stabilize one chapter at a time

`Direction → story engine → volume/chapter plan → complete chapter → revision and review → continuity → next chapter`

Each chapter loads only the context it needs. Facts, promises, resources, character state, and relationships enter durable memory after acceptance; unreviewed candidates never become story facts. YAML and accepted Markdown are authoritative. SQLite indexes and reader views are rebuildable. User edits to prose and artifacts are protected, and older workspaces can be checked, backed up, and explicitly migrated.

An optional [writing-style contract](references/style-engine.md) keeps a small, reviewable set of positive style choices and anti-template concerns. Beginners can write their first chapter without configuring it. When selected, it guides the first draft; review and repair use evidence from the prose rather than detector scores or blanket word bans.

For optional external help, a novel workspace can register GitHub writing-style or humanization Skills. Candidates are fetched into a private directory, pinned to a commit, reviewed, and author-approved before activation; chapter production never silently fetches remote content, and remote rules cannot override the local contract.

## Get started

Install this repository as a personal Codex Skill, then invoke `$produce-long-form-novel` in Codex. Python 3.10+ is required; install the YAML continuity dependency before using that storage:

```powershell
python -m pip install -r requirements.txt
```

Start with the prompt that matches your situation:

| Starting point | Example for Codex |
| --- | --- |
| No idea | “Use `$produce-long-form-novel`. I do not have a novel idea yet; show me opening seeds.” |
| An idea | “Use `$produce-long-form-novel` to plan a long novel from this idea: …” |
| Genre research | “Use `$produce-long-form-novel` to analyze recent public xianxia charts and create opportunity cards.” |
| Reference analysis | “Use `$produce-long-form-novel` to analyze this text I am authorized to use. Estimate its size and confirm the reading scope and analysis focus first.” |
| Fanfic | “Use `$produce-long-form-novel` to plan a fanfic continuation from this completed authorized analysis and its read scope.” |
| Existing novel | “Use `$produce-long-form-novel` to continue `novels/<novel-name>/`. Check its state and next action first.” |

**New books begin with progressive choices.** The five no-idea seeds emphasize a strong hook, character growth, setting wonder, relationship pull, and mystery investigation. After you choose, combine, or revise one, Codex presents two briefs with different conflicts, protagonist paths, progression loops, and tones. For a merely vague request, the first round asks only about audience, publishing format, and primary reader reward. `novel-brief.md` becomes authoritative after a direction is chosen.

You can also inspect a local workspace from the command line:

```powershell
python scripts/novelctl.py init novels/<novel-name> --title "<novel-title>"
python scripts/novelctl.py status novels/<novel-name> --format markdown
python scripts/novelctl.py next novels/<novel-name>
python scripts/novelctl.py validate novels/<novel-name>
python scripts/novelctl.py export novels/<novel-name>
```

For an older workspace, run `python scripts/novelctl.py migrate novels/<novel-name> --dry-run` first. See [SKILL.md](SKILL.md), [workflow routing](references/workflow-routing.md), and [artifact contracts](references/artifact-contracts.md) for the full process.

## Local reader

The optional **ANI Local Reader** offers read-only browser access to `novels/` and `analyses/`: a bookshelf, full file tree, Chinese full-text search, headings, font and theme controls, chapter navigation, and analysis coverage and evidence views. It refreshes when files change. The Skill also works without it.

With Node.js 22.18+ installed, run this from the repository root:

```powershell
./apps/workspace-reader/start-local.ps1
```

Open <http://127.0.0.1:8790>. Pass `-Roots 'C:/writing', 'D:/research'` to read existing workspaces elsewhere. The reader accesses only configured local roots, does not call a model, and does not modify manuscripts or state. [Read the reader guide](apps/workspace-reader/README.md).

## What keeps long-form work under control

- **Editable local source.** `novels/`, `analyses/`, `trends/`, and `libraries/` are Git-ignored by default to protect manuscripts, source texts, research snapshots, and private assets.
- **Recoverable state.** Accepted chapters, checkpoints, validation, and one next action make interrupted work resumable. Token usage distinguishes exact measurements, estimates, and values unavailable from the runtime.
- **Governed cross-book reuse.** `libraries/` holds reusable mechanisms and shared-IP canon. `sync` reports changes or conflicts without overwriting prose. Timeline checks and impact review only report effects; canon publication needs author approval or active delegation. See the [cross-book asset graph contract](references/cross-book-asset-graph.md).
- **Traceable research.** Chart research uses public metadata. Reference analysis uses authorized texts, records coverage and evidence, and does not treat source prose as copy-ready output.

## Repository map

```text
SKILL.md                 Codex workflow entry point
references/              Contracts for new books, analysis, fanfic, chapters, and cross-book assets
scripts/                 Deterministic state, validation, retrieval, asset graphs, and export
apps/workspace-reader/   Optional local read-only reader
novels/ analyses/        Private writing and research workspaces (Git-ignored)
trends/ libraries/       Private trend snapshots and cross-book assets (Git-ignored)
```

Codex is the sole creative understanding, generation, and judgment engine. This project has no separate model provider, agent runtime, or database authority. It was distilled by the maintainer of [AI-Novel-Writing-Assistant](https://github.com/ExplosiveCoderflome/AI-Novel-Writing-Assistant) from long-form production experience, but does not depend on that project's frontend, backend, or services.

Code and documentation use the [Apache License 2.0](LICENSE). See the [changelog](docs/releases/release-notes.md), [contribution guide](CONTRIBUTING.md), and [security policy](SECURITY.md).

## Latest update

### 2026-10-15

- **Added:** Local content, size, and version checks for GitHub writing-style and humanization Skill candidates.
- **Improved:** Core reader promises carry from analysis into writing, author corrections persist, and selected directions can proceed directly with relevant genre dimensions.
- **Fixed:** Accepted-prose protection, review version binding, required inputs, chapter volume selection, continuity recovery, and stable exports.

See the [changelog](docs/releases/release-notes.md) for the full history.
