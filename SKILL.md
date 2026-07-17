---
name: produce-long-form-novel
description: Produce, maintain, analyze, and export long-form Chinese novels through staged, editable artifacts, with progressive confirmation of high-impact creative settings for novice authors. Use when Codex needs to turn an idea into a novel plan, guide choices such as audience channel or genre, analyze public ranking metadata for hot genres, deconstruct an authorized reference novel or diagnose a manuscript, design or revise volumes, generate chapter plans or prose, continue an existing novel, audit and repair chapters, export ready chapters as a TXT file, or decide the next production step from an existing Markdown/YAML workspace. Do not use for generic app development, database operations, unauthorized bulk copying, or unrelated short-form copywriting.
---

# Produce Long-Form Novel

## Mission

Help a novice author move from a vague idea toward a complete long-form novel. Produce concrete, editable artifacts; preserve author decisions; and recommend one clear next step.

For a completely vague request to create a novel, do **not** generate a full premise, hook package, cast, or chapter first. Use exactly three first-round choices: (1) audience channel, with male-oriented, female-oriented, broad-audience, and AI-recommended options; (2) publishing shape, with paid serial, free serial, and undecided options; and (3) genre or primary reader reward, with 2–4 concrete content options. Do not ask about protagonist, style, or length in this first round. Then wait for confirmation or AI delegation before formal planning.

Use Markdown for creative artifacts and a small `novel-state.yaml` file for progress. In a legacy workspace, keep continuity ledgers as readable Markdown. In a migrated workspace, YAML is the sole continuity authority and Markdown ledgers are generated read-only views; SQLite is a disposable local index. Do not require JSON unless the user explicitly requests machine integration or export.

## Choose Persistence Mode

Choose one mode before producing files:

- **Preview mode**: Return a bounded artifact in the conversation. Use for exploration, first-draft ideas, or any request without a confirmed save location. Do not create files or infer a workspace from chat history.
- **Workspace mode**: Write Markdown artifacts and a small YAML state index into one workspace. Use when the user asks to save, create a workspace, analyze a long source, retain ranking snapshots, continue across tasks, protect edits, generate chapters, or otherwise confirms durable production. Novel production uses `novel-state.yaml`; reference-book analysis uses `analysis-state.yaml`; ranking-trend analysis uses `trend-state.yaml`.
- **Promote preview**: When the user accepts two or more planning artifacts and wants to continue, recommend workspace mode once. After the user confirms, save the accepted artifacts first, create the state index, and resume from the recorded next action.

Do not create a workspace merely because a conversation has multiple turns. If workspace mode is confirmed but no location is supplied, use `novels/<normalized-title>/` for novel production, `analyses/<normalized-title>/` for reference-book analysis, or `trends/<normalized-scope>/` for ranking-trend analysis under the current working directory, then state the chosen path before writing.

## Route the Request

Choose one primary route before acting:

1. **Create a novel**: first route a vague idea through progressive confirmation; only after confirmation or AI delegation, turn it into positioning, a hook package, a story engine, and the first planning artifacts.
2. **Plan or revise volumes**: create or update volume strategy, skeletons, beat sheets, or chapter lists.
3. **Plan or draft a chapter**: create the chapter contract, draft prose, assess it, and update stable state.
4. **Audit or repair**: diagnose a supplied plan or chapter, apply the smallest useful repair, and preserve successful content.
5. **Continue an existing novel**: inspect current artifacts, recover the next valid production step, and continue without rewriting protected work.
6. **Analyze a reference work**: deconstruct an authorized local text, accessible online source, or the user's manuscript into evidence-backed notes, analysis sections, and reusable pattern cards without reproducing the source.
7. **Analyze hot genre trends**: inspect public official chart metadata or user-provided chart captures, aggregate surface signals, and produce a chart-level report plus 3–5 opportunity cards without reading novel prose.

Read [workflow-routing.md](references/workflow-routing.md) when the request spans routes, the next step is unclear, or an existing workspace may be incomplete.

Read [novel-brief.md](references/novel-brief.md) when creating or revising a novel brief. Keep its reader, length, narrative and writing-preference settings authoritative for later planning and chapter production.

## Guide Creative Decisions Progressively

Apply the progressive-confirmation contract in [novel-brief.md](references/novel-brief.md) across novel positioning, story engine, world and cast, volume planning, and the first chapter.

- Before asking, extract explicit choices from the current request and read existing confirmation records and protected artifacts. Do not ask again about settings marked user-confirmed, delegated to AI, or not applicable.
- For a vague novel-creation request such as “help me write a novel,” use the exact three-choice first-round contract in Mission. Do not silently select a genre, channel, platform, or length and then present a complete hook package. At most, attach one short illustrative premise after the choices and label it non-authoritative.
- Ask only the 2–3 unresolved choices with the greatest downstream impact. Give exactly 2–4 mutually exclusive content options per choice, put one recommendation first, and explain its effect briefly. Keep custom input, accept-all, AI delegation, and skip as one shared instruction after the choices; do not inflate each option list with these controls.
- Treat “you decide,” “do not ask me about these,” or “generate directly” as revocable project-level delegation for the affected settings. Persist it in the novel brief when workspace mode is active.
- When the request is already specific, summarize the understood decisions and ask only about material conflicts or unresolved decisions required by the current milestone.
- For a bounded idea, title, name, or other preview request, ask only what that artifact needs; do not launch the full onboarding sequence.
- Allow unconfirmed AI recommendations in bounded conversation previews only after presenting the current confirmation choices. Do not save them as authoritative, mark their artifact `ready`, or build formal downstream assets from them until the user confirms or delegates the decision.
- When a confirmed high-impact setting changes, protect existing prose and immediately use the explicit `stale` status for each affected unwritten artifact; do not merely say it is “affected,” defer impact reporting, or silently rewrite it. A confirmed audience-channel or reading-promise change makes the existing unwritten volume strategy, volume skeleton, beat sheet, and chapter plans `stale` unless a dependency check proves a specific artifact unaffected.
- Treat male-oriented, female-oriented, and broad-audience channels as reader-promise and packaging signals, never as rigid gender stereotypes.
- Keep this confirmation sequence on the novel-creation route. Reference analysis and hot-genre trends retain their own scope and source-confirmation rules.

## Start from Facts

When a workspace exists:

1. Locate and read `novel-state.yaml`, `analysis-state.yaml`, or `trend-state.yaml` first according to the route.
2. Read only the artifacts required by the current route.
3. Treat user-edited files and existing prose as protected unless the user explicitly authorizes replacement.
4. Compare the current artifact with its upstream dependencies before extending it.
5. Mark affected downstream plans as stale instead of silently rewriting them.

When no workspace exists, remain in preview mode unless the user requests or confirms durable production. When promoting a preview, save only the artifacts the user has accepted; do not reconstruct unaccepted conversation drafts as authoritative files.

Read [artifact-contracts.md](references/artifact-contracts.md) before creating a workspace, changing artifact status, or deciding which downstream files become stale.

## Run the Production Loop

Follow this artifact chain, stopping at the milestone the user requested:

`idea -> novel brief -> story bible -> world and cast -> volume strategy -> volume skeleton -> beat sheet -> chapter plan -> context package -> chapter draft -> humanization revision -> review/repair -> continuity update`

For every step:

1. State necessary assumptions briefly. Apply confirmed or delegated defaults directly; present unconfirmed high-impact defaults as choices instead of silently treating them as authoritative.
2. Consume the authoritative upstream artifact rather than reconstructing it from chat history.
3. Produce one coherent artifact or one bounded batch.
4. Check its acceptance conditions.
5. Update `novel-state.yaml` only after the artifact is usable.
6. Report what was produced, what changed, what remains uncertain, and the recommended next action.

Do not attempt to generate an entire long novel in one response. Advance through resumable milestones and keep each deliverable editable.

## Analyze Reference Works

Read [book-analysis.md](references/book-analysis.md) before analyzing a reference novel, an online novel, a long uploaded manuscript, writing techniques, commercial hooks, character systems, plot structure, or a user's draft as a whole.

Read [book-analysis-retrieval.md](references/book-analysis-retrieval.md) before indexing or querying a long analysis workspace, building BookGraph nodes or edges, tracing story relationships, using full-text retrieval, or attaching optional embeddings.

- Persist analysis only under `analyses/<normalized-title>/` with `analysis-state.yaml` and the artifact layout defined in `book-analysis.md`. Do not use `novels/`, `novel-state.yaml`, or an invented competing layout for analysis unless the user explicitly asks to attach the results to an existing novel workspace.
- Accept user-provided text, local text files, existing workspaces, and lawfully accessible online pages. Do not bypass paywalls, login controls, captchas, anti-bot restrictions, or site access rules; request a user-supplied file when access is unavailable.
- Freeze the source scope and fingerprint before analysis. Distinguish full coverage from sampling, and state omitted ranges and blind spots.
- Build bounded segment notes first. Generate the overview before specialist sections so later judgments share one positioning anchor.
- After notes exist for a long source, run `scripts/analysis_retrieval.py build <analysis-workspace>`. Use graph traversal for explicit relationships, filtered lexical search for named facts, and optional vector recall only when compatible embeddings already exist.
- Treat `retrieval/analysis-index.sqlite3` and embeddings as disposable derived caches. Keep Markdown/YAML, graph JSONL, source fingerprints, and user edits authoritative.
- Separate source fact, supported inference, and open hypothesis. Bind important conclusions to chapter or segment evidence and preserve contrary evidence.
- Produce reusable mechanism cards rather than imitation instructions. Describe prerequisites, reader effect, failure modes, and a safe transformation direction; never reproduce substantial source text or promise stylistic cloning.
- Keep successful analysis sections when another section fails. Resume only missing or stale work, and mark downstream analysis stale when the source fingerprint or scope changes.
- When the source is the user's own manuscript, use diagnosis mode and recommend bounded repairs without modifying the manuscript unless explicitly authorized.

## Analyze Hot Genre Trends

Read [hot-genre-trends.md](references/hot-genre-trends.md) before handling popular-ranking themes, hot genres, recent market directions, chart composition, or track opportunities.

- Keep this route under `trends/<normalized-scope>/`; never mix its source material with `novels/` or `analyses/`.
- If the platform or audience channel is missing, ask for the target channel first. Default to the top 20 entries per chart and no more than 3 charts per request.
- Use only public official chart metadata or screenshots, tables, and text supplied by the user. Set `access_level` to `metadata_only`; do not bypass access controls or fetch novel prose.
- Follow this order: confirm platform/channel/time window, capture the chart, save the snapshot, extract surface signals from title/tags/synopsis, aggregate facts, then create 3–5 opportunity cards.
- Run `scripts/trend_snapshot.py validate` before reporting. Use `summarize` for one snapshot and `compare` only for two dates from the same platform, chart, and statistical window.
- Call a single snapshot “current chart composition.” Require at least two comparable dates before claiming rise, decline, persistence, or new entry.
- Do not infer whole-book pacing, character arcs, foreshadowing payoff, prose quality, or middle-to-late performance from metadata.
- Move only an explicitly selected opportunity card into `novel-brief.md`. Never inject raw charts, synopses, reports, or unselected cards into novel-production context.
- If the user requests analysis of a specific work, stop this route, explain the upgrade to reference-book analysis, and request an authorized source without automatically fetching prose.

## Build Story and Volume Plans

Read [story-and-volume-planning.md](references/story-and-volume-planning.md) when creating or changing positioning, the hook package, story engine, world rules, cast, volume strategy, beat sheets, or chapter lists.

Read [world-bible.md](references/world-bible.md) when creating, revising, or consuming the novel's world rules, faction constraints, or story stages. Treat its rule IDs and protected limits as chapter-level hard constraints, not decorative setting text.

Read [character-asset-layout.md](references/character-asset-layout.md) when creating, splitting, migrating, reading, or updating character assets in a workspace.

Preserve these priorities:

- Lock the reading promise before expanding world detail.
- Give the protagonist an active desire, repeatable action loop, escalating opposition, and visible rewards.
- Separate volume strategy from volume skeleton.
- Plan early volumes more firmly than distant volumes.
- Protect user-fixed volume counts, milestones, and written chapters.
- Generate chapter lists by the current beat or volume window when that reduces waiting and rework.
- Use layered character presentation: a compact roster anchor for reserve roles, a complete identity and visual profile for active core roles, and a chapter-specific current presentation for participants. Do not leave an active character without a usable identity, appearance, dress/prop, voice or habitual action, and first-impression guidance.
- In a workspace with recurring characters, keep a compact `characters/character-roster.md` index and one profile file per active core character. Read the index plus only the profiles relevant to the current chapter.

## Produce Chapters

Read [chapter-production.md](references/chapter-production.md) before planning, drafting, continuing, reviewing, or repairing a chapter.

When the user asks to continue multiple chapters, finish a long chapter range, improve generation speed, work in parallel, or use subagents, keep the chapter-production route serial. The responsibility-specific subagent experiment is paused: do not create child agents or speculative next-chapter candidates. Produce, review, and commit one chapter before planning the next.

Read [continuity-ledgers.md](references/continuity-ledgers.md) before bootstrapping continuity for an existing workspace, creating a context package, accepting a chapter, updating a ledger, recording quality debt, or recovering after an interruption.

Read [structured-continuity-store.md](references/structured-continuity-store.md) when `continuity/data/` exists or when migrating continuity to YAML, rebuilding its SQLite index, creating a checkpoint, or assembling bounded long-form context.

Read [chinese-novel-humanization.md](references/chinese-novel-humanization.md) before generating a complete chapter draft, producing a comparison rewrite, or reviewing prose for template-like machine patterns. Apply its protected-facts and no-artificial-noise rules.

Use one shared chapter contract across drafting, acceptance, and repair. Include:

- immediate chapter goal and resistance;
- required events, facts, appearances, and payoff touches;
- protected facts and forbidden crossings;
- reader question, promised reward, key turn, net change, and ending pull;
- previous-chapter handoff and current continuity constraints.
- the relevant world-rule, faction, and stage IDs, plus any current state that limits this chapter.
- a chapter-length contract: target length, acceptable range, its source in the book brief or an approved chapter override, and scene-level budget allocation.

Generate the whole chapter as one coherent draft by default. Use scene beats for planning and targeted repair, not as a reason to stitch together many disconnected mini-drafts.

For a multi-chapter request, repeat the complete single-agent chapter loop: plan and context package, one coherent draft, humanization, review, then continuity commit. Do not prepare later chapter candidates until the current chapter has become the stable source of truth.

Before drafting a new chapter in a continuity-enabled workspace, create its concise context package. It must identify selected authority sources, required constraints, deliberately omitted material, and any missing hard constraint. Do not copy long prose into the package.

After a complete draft, run one constrained Chinese-novel humanization pass by default. Preserve the chapter contract and all protected facts, then reduce clustered template patterns, explanatory narration, mechanically even cadence, and undifferentiated character voices. Keep the original draft when the user requests an experiment or comparison. Never promise a detector score or use a detector score as the sole acceptance criterion.

After review, commit continuity only when the final prose is `accepted`, or is `continue_with_warning` and still safe to continue. In a migrated workspace, update and validate YAML first, then regenerate Markdown views and SQLite; in a legacy workspace, update the Markdown ledgers directly. Then update affected character assets, quality debt, recovery record, and state index. Do not commit planned events, local-patch candidates, rewrite-needed drafts, or replan-blocked drafts as facts.

## Manage Context and Continuity

Read [context-and-continuity.md](references/context-and-continuity.md) when the request involves continuation, long-running consistency, character state, world rules, prior chapters, references, style, facts, resources, or payoffs.

For a continuity-enabled workspace, read the recovery record and only the YAML-selected facts (or legacy ledgers), profiles, world entries, prior tail, and volume assets relevant to the current chapter. If a source fingerprint no longer matches its stable source, mark the dependent delta, ledger entry, and context package stale; never overwrite user-edited prose to make them match.

Prefer the smallest context package that preserves coherence. Never load every chapter merely because it exists. Prioritize hard constraints, the current task, the previous handoff, relevant character facts, the active volume window, and unresolved promises.

Keep durable facts in their authoritative modules (`characters/`, `world-bible.md`, and `continuity/`), while each `chapters/chapter-XXX/` directory holds that chapter's plan, context package, prose, and review. The chapter context package is a minimal assembly of references and chapter-specific obligations, never a duplicated or competing fact store.

## Export Ready Chapters

When the user asks to merge, compile, or export generated chapters as a TXT file, run `scripts/export_novel_txt.py` against the confirmed novel workspace.

- Export only chapter prose. Never include plans or reviews.
- Default to `--source auto`: prefer `draft-humanized.md`, then use `draft.md` when no humanized version exists.
- Preserve numeric chapter order. Use `--start` and `--end` only when the user specifies a chapter range.
- Run with `--dry-run` before a non-default range or source selection; otherwise export directly to the workspace `exports/` folder.
- Report the exported chapter range, source selected for each chapter, skipped chapters, and final output path.

## Audit and Repair

Read [quality-and-repair.md](references/quality-and-repair.md) before evaluating quality, rewriting prose, repairing continuity, or recommending replanning.

Apply this escalation order:

1. Accept usable content.
2. Record non-blocking quality debt.
3. Apply a targeted patch when the problem is local.
4. Rewrite the chapter only when local repair cannot satisfy the chapter contract.
5. Recommend neighboring-plan or volume replanning only when the chapter responsibility itself is structurally impossible or misplaced.

Do not discard a usable chapter because of a local style flaw. Do not create endless review-repair loops.

## Project Adapter Boundary

This skill is a Codex writing workflow, not the runtime of `AI-Novel-Writing-Assistant-v2`. Read [ai-novel-writing-assistant-v2-adapter.md](references/ai-novel-writing-assistant-v2-adapter.md) only when the user asks to compare, align, import, export, or develop against that project.

Do not directly operate its database, task queue, HTTP routes, or production runtime unless the user separately authorizes an implementation task.

## Skill Maintenance

When maintaining this skill, treat a user's explicit acceptance of a proposed workflow, artifact, directory, or constraint change as authorization to update the relevant skill instructions in the same task. Update `SKILL.md` and the directly affected reference contracts together, then run a focused consistency check for conflicting paths, duplicate authority, and stale terminology. Do not treat an unconfirmed recommendation as a specification change, and preserve unrelated user edits.

## Finish Clearly

End each completed production action with:

- artifact created or updated;
- important assumptions or protected decisions;
- quality or continuity risks;
- state transition performed;
- one recommended next action.
