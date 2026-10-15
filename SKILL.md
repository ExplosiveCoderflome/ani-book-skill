---
name: produce-long-form-novel
description: Produce, maintain, analyze, and export long-form Chinese novels through staged, editable artifacts, with progressive confirmation of high-impact creative settings for novice authors. Use when Codex needs to turn an idea into a novel plan, guide choices such as audience channel or genre, analyze public ranking metadata for hot genres, deconstruct an authorized reference novel or diagnose a manuscript, write fanfic from an authorized analysis workspace, design or revise volumes, generate chapter plans or prose, continue an existing novel, audit and repair chapters, export ready chapters as a TXT file, or decide the next production step from an existing Markdown/YAML workspace. Do not use for generic app development, database operations, unauthorized bulk copying, or unrelated short-form copywriting.
---

# Produce Long-Form Novel

## Mission

Help a novice author move from a vague idea toward a complete long-form novel. Produce concrete, editable artifacts; preserve author decisions; and recommend one clear next step.

## Codex-Native Execution Boundary

**Codex is the only engine for creative understanding, planning, generation, review, and judgment.** This Skill is the process contract; Python scripts perform only deterministic state transitions, validation, indexing, conflict detection, and export. This repository is not an `AI-Novel-Writing-Assistant` runtime or submodule: do not add provider SDKs, Web APIs, database authorities, queues, or a custom agent runtime. `provider` and `model` fields are Token diagnostics only when the Codex host exposes them, never a generation dependency.

## Check Skill Currency Before Running

Treat the checked-out repository as the editable Skill source and the locally installed Skill as its runtime mirror. Resolve the installed mirror from `$env:CODEX_HOME\skills\produce-long-form-novel`; when `CODEX_HOME` is unset, use `<UserProfile>\.codex\skills\produce-long-form-novel`. Before the first production action in a task, compare the repository root with that mirror:

```powershell
python scripts/sync_skill_mirror.py check <repository-root> <installed-skill-directory>
```

- Report `missing`, `changed`, and `extra` files before relying on the mirror.
- After every functional edit to `SKILL.md`, `references/`, `scripts/`, `assets/`, `requirements.txt`, or `agents/`, run the repository's required compile, tests, and Skill quick validator. When they pass, automatically synchronize the repository to the resolved installed mirror and rerun `check`; do not ask for repeated authorization.
- Never synchronize failed or unvalidated functional changes. Keep synchronization additive and preserve mirror-only files. Do not hardcode a user-specific absolute path.
- This comparison and synchronization are deterministic maintenance operations; do not record them as creative model usage.

When a user explicitly says they have no story idea, do **not** begin with the three opening settings or a full premise. Read [opening-seeds.md](references/opening-seeds.md), run its private divergence and quality-gate process, then output exactly five non-authoritative, one-sentence opening seeds. Ask the user to choose one, edit one, or provide an original idea.

For a vague request without an explicit “no idea” statement, start with three high-impact choices: audience channel, publishing shape, and genre or primary reader reward. Do not ask about protagonist, style, or length in that first round or generate a full hook package. These choices remain provisional until the user confirms them or delegates the decision.

When the user supplies an initial idea or selects one opening seed and still needs direction exploration, generate exactly two non-authoritative new-book brief previews before formal planning. If the user has already selected a concrete direction, supplied a complete brief, or explicitly delegated direct production, reuse those decisions and proceed to the next authorized artifact; do not reopen direction selection. Each preview must include a working title, one-sentence premise, target reader/reward, protagonist path, core conflict, early hook, progression loop, and high-level ending direction. The two previews must differ materially in their selling point, conflict, protagonist path, progression loop, tone, or ending direction. Do not write either preview to `novel-brief.md`, mark it `ready`, or use it for world, volume, or chapter production until the user selects, combines, or delegates a direction.

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
7. **Write fanfic from an analysis**: use an authorized analysis workspace as canon facts, keep original names within the read scope, and produce a fanfic novel workspace with a handoff before chapter drafting.
8. **Analyze hot genre trends**: inspect public official chart metadata or user-provided chart captures, aggregate surface signals, and produce a chart-level report plus 3–5 opportunity cards without reading novel prose.
9. **Establish or adjust a writing style**: turn author preferences, the author's own writing, or transferable methods from authorized analysis into a small editable style contract; bind it to a novel only after confirmation or delegation, then use it for prose, review, and repair.

Read [workflow-routing.md](references/workflow-routing.md) when the request spans routes, the next step is unclear, or an existing workspace may be incomplete.

Read [novel-brief.md](references/novel-brief.md) when creating or revising a novel brief. Keep its reader, length, narrative and writing-preference settings authoritative for later planning and chapter production.

Read [fanfic.md](references/fanfic.md) when the user asks for fanfic, a continuation that keeps original names, or a new story that reuses an analyzed cast. Original novels still must not copy source names, recognizable appearance sets, or signature scenes from analysis cards.

Read [style-engine.md](references/style-engine.md) when the user asks to extract, save, reuse, or change a writing style, or to apply anti-AI expression rules. Keep style optional during onboarding: a confirmed book-level `writing-style.md` can be created from author preferences, the author's own writing, or transferable methods from authorized analysis. Do not copy a third-party author's recognizable voice. Use the same effective style rules for drafting, humanization, review, and targeted repair; style cannot override story facts or chapter obligations.

Read [remote-skill-sources.md](references/remote-skill-sources.md) when the user asks to obtain or update a writing-style or anti-AI Skill from GitHub. Treat `production/skill-sources.yaml` as an explicit, private source registry. Validate it with `scripts/skill_sources.py`, fetch candidates only on the user's request through the preinstalled `skill-installer`, pin an immutable commit before enabling, and require review plus author confirmation before merging rules into `writing-style.md`. Never fetch during ordinary chapter production, execute remote scripts, or let a remote `SKILL.md` override this Skill's contracts.

## Guide Creative Decisions Progressively

Apply the progressive-confirmation contract in [novel-brief.md](references/novel-brief.md) across novel positioning, story engine, world and cast, volume planning, and the first chapter.

- Before asking, extract explicit choices from the current request and read existing confirmation records and protected artifacts. Do not ask again about settings marked user-confirmed, delegated to AI, or not applicable.
- For an explicit no-idea request such as “I have no idea; help me start a novel,” use the five-opening-seed contract in Mission. For a supplied idea or selected seed that still needs exploration, use the two-brief-preview contract before asking for opening settings; reuse an explicitly selected direction or direct-production delegation. Do not silently select a genre, channel, platform, or length and then present an authoritative plan.
- For a vague request that does not explicitly say there is no idea, use the three-choice first round in Mission. At most, add one short illustrative premise marked non-authoritative.
- Ask only the 2–3 unresolved choices with the greatest downstream impact. Give exactly 2–4 mutually exclusive content options per choice, put one recommendation first, and explain its effect briefly. Keep custom input, accept-all, AI delegation, and skip as one shared instruction after the choices; do not inflate each option list with these controls.
- Treat “you decide,” “do not ask me about these,” or “generate directly” as revocable project-level delegation for the affected settings. Persist it in the novel brief when workspace mode is active.
- When the request already specifies the chosen direction, summarize it and proceed using existing choices or delegation. Offer two meaningfully different brief previews only when the user is exploring alternatives; ask only about material unresolved conflicts. After a direction is selected, ask only the unresolved opening settings required by the current milestone.
- For a bounded idea, title, name, or other preview request, ask only what that artifact needs; do not launch the full onboarding sequence.
- Allow unconfirmed AI recommendations in bounded conversation previews only after presenting the current confirmation choices. Do not save them as authoritative, mark their artifact `ready`, or build formal downstream assets from them until the user confirms or delegates the decision.
- When a confirmed high-impact setting changes, protect existing prose and immediately use the explicit `stale` status for each affected unwritten artifact; do not merely say it is “affected,” defer impact reporting, or silently rewrite it. A confirmed audience-channel or reading-promise change makes the existing unwritten volume strategy, volume skeleton, beat sheet, and chapter plans `stale` unless a dependency check proves a specific artifact unaffected.
- Treat male-oriented, female-oriented, and broad-audience channels as reader-promise and packaging signals, never as rigid gender stereotypes.
- Keep this confirmation sequence on the novel-creation route. Reference analysis, fanfic, and hot-genre trends retain their own scope and source-confirmation rules.

## Start from Facts

When a workspace exists:

1. Locate and read `novel-state.yaml`, `analysis-state.yaml`, or `trend-state.yaml` first according to the route.
2. Read only the artifacts required by the current route.
3. Treat user-edited files and existing prose as protected unless the user explicitly authorizes replacement.
4. Compare the current artifact with its upstream dependencies before extending it.
5. Mark affected downstream plans as stale instead of silently rewriting them.

When no workspace exists, remain in preview mode unless the user requests or confirms durable production. When promoting a preview, save only the artifacts the user has accepted; do not reconstruct unaccepted conversation drafts as authoritative files.

Read [artifact-contracts.md](references/artifact-contracts.md) before creating a workspace, changing artifact status, or deciding which downstream files become stale.

Read [token-usage.md](references/token-usage.md) before recording or reporting model usage. In workspace mode, account for every actual model generation call as `exact`, `estimated`, or `unavailable`; never invent a number when the runtime does not expose usage.

Read [generation-contracts.md](references/generation-contracts.md) before running or changing the full production chain. Read [auto-director-and-recovery.md](references/auto-director-and-recovery.md) when the user delegates decisions, requests a chapter range, resumes an interrupted run, reaches a milestone approval, or encounters a blocking condition.

Read [cross-book-asset-graph.md](references/cross-book-asset-graph.md) before publishing, importing, syncing, or resolving reusable assets or shared-IP canon. Only schema-v3 workspaces may link cross-book assets; graph results are candidates and the referenced YAML/Markdown remains authoritative.

When a novel workspace has `production/skill-sources.yaml`, check its source status before applying any remote writing guidance. `candidate` and `update_available` entries are review material only; only an `enabled` entry with a confirmed fixed commit may contribute rules, and those rules still enter the local book snapshot before drafting.

当章节使用跨书资产时，Codex 先从计划和活跃链接提出 `context-packages/chapter-XXX.assets.yaml`，由脚本校验其固定快照、用途和约束；再通过 `novelctl context --asset-library ... --asset-selection ...` 生成有限上下文。选中资产的同步冲突会阻断上下文、正文和审校；共享更新只提示，默认继续使用本书锁定快照。只有正文验收且连续性提交后，才可在 `production/asset-candidates/` 形成待发布资产候选。

一个私有跨书资产库默认是一个共享 IP 宇宙。对 `universe` / `event` 候选，Codex 必须先基于已验收来源明确提出 `content.canon.sequence`、参与资产、影响和可选先后关系，再运行 `asset_graph.py canon-check` 与 `impact ... --workspace <明确工作区>`；影响报告只作风险审查，不能改写任何书或自动升级快照。只有作者批准、按资产委托或未撤销的宇宙级 Codex 委托之一成立时，才能用既有 `publish` 提交正史；`reusable` 资产不接受宇宙级委托。时间线与图谱均为 YAML/JSONL 的可重建派生物，不能替代回读权威 YAML/Markdown。

In a schema-v3 workspace, use `scripts/novelctl.py` as the deterministic control surface for state transitions, validation, recovery, context, checkpoints, usage, and export. Codex remains the only creative generation engine; do not add or invoke a model-provider SDK from this skill.

## Run the Production Loop

Follow this artifact chain, stopping at the milestone the user requested:

`idea -> novel brief -> story bible -> world and cast -> volume strategy -> volume skeleton -> beat sheet -> chapter plan -> context package -> chapter draft -> humanization revision -> review/repair -> continuity update`

For every step:

1. State necessary assumptions briefly. Apply confirmed or delegated defaults directly; present unconfirmed high-impact defaults as choices instead of silently treating them as authoritative.
2. Consume the authoritative upstream artifact rather than reconstructing it from chat history.
3. Produce one coherent artifact or one bounded batch.
4. Check its acceptance conditions.
5. Record the generation call in `production/token-usage.jsonl` before marking the artifact usable. Keep exact, estimated, and unavailable measurements distinct; do not count deterministic file or index operations.
6. Update `novel-state.yaml` only after the artifact is usable.
7. Report what was produced, what changed, the step's available Token usage, what remains uncertain, and the recommended next action.

Book-level direction, the story engine, volume strategy, structural replanning, and any protected overwrite are milestone approvals by default. After the user approves a chapter range, continue serially within that range and stop at its end. A project-level AI delegation may satisfy these approvals until the user revokes it.

Do not attempt to generate an entire long novel in one response. Advance through resumable milestones and keep each deliverable editable.

## Analyze Reference Works

Read [book-analysis.md](references/book-analysis.md) before analyzing a reference novel, an online novel, a long uploaded manuscript, writing techniques, commercial hooks, character systems, plot structure, or a user's draft as a whole.

Read [book-analysis-retrieval.md](references/book-analysis-retrieval.md) before indexing or querying a long analysis workspace, building BookGraph nodes or edges, tracing story relationships, using full-text retrieval, or attaching optional embeddings.

- Persist analysis only under `analyses/<normalized-title>/` with `analysis-state.yaml` and the artifact layout defined in `book-analysis.md`. Do not use `novels/`, `novel-state.yaml`, or an invented competing layout for analysis unless the user explicitly asks to attach the results to an existing novel workspace.
- Accept user-provided text, local text files, existing workspaces, and lawfully accessible online pages. Do not bypass paywalls, login controls, captchas, anti-bot restrictions, or site access rules; request a user-supplied file when access is unavailable.
- On an authorized, accessible source, record the core reader promise and the visible payoff separately. A genre fantasy, psychological reward, or relationship triangle can be the core even when its delivery is a sequence of bodily, investigative, or power changes. Record rules, identity, and information gaps when they enable or block that promise; keep source facts and short quotes accurate.
- Freeze the source scope and fingerprint before analysis. Copy a user-supplied local file or chapter directory into private `source/` as a snapshot, and never index `source/` in retrieval. Distinguish full coverage from sampling, and state omitted ranges and blind spots.
- Before the first segment note, run `scripts/estimate_analysis_tokens.py` on the local source. Report the character count, planned segment count, and source-token range as a length estimate, separate from model usage. If it sets `confirm_required`, ask for full analysis or a bounded partial window; record `remaining_scope` for later incremental analysis.
- After coverage is confirmed and before the first note batch, draft `analysis-lens.md` from 2–3 evidence-backed core candidates, then separate the selected core reader promise from its surface progression axes and gates. Include a counterfactual check for essential relationships or viewing positions. Self-check it, show the candidates, the selected promise, the progression axes, and primary questions, set it to `pending_confirm`, and wait for acceptance before notes. Existing notes without a lens remain intact; add the lens before the next batch.
- If `character_sync.status` is `unconfirmed`, ask whether to maintain individual `characters/<CHAR-ID>.md` cards. When enabled, update relevant cards after each note batch, using only observed details and chapter evidence.
- Build bounded segment notes first. Generate the overview before specialist sections and before handing an analysis into a novel so later judgments share a positioning anchor that includes the core promise, psychological engine, relationship structure, surface progression, and coverage limits.
- After notes exist for a long source, run `scripts/analysis_retrieval.py build <analysis-workspace>`. Use graph traversal for explicit relationships, filtered lexical search for named facts, and optional vector recall only when compatible embeddings already exist.
- Treat `retrieval/analysis-index.sqlite3` and embeddings as disposable derived caches. Keep Markdown/YAML, graph JSONL, source fingerprints, and user edits authoritative.
- Separate source fact, supported inference, and open hypothesis. Bind important conclusions to chapter or segment evidence and preserve contrary evidence.
- Produce reusable mechanism cards rather than imitation instructions. Describe the core promise, mechanism, prerequisites, reader effect, failure modes, and original transformation. Add stimulus object, viewing position, psychological progression, or return/attachment only when the source evidence makes those dimensions relevant; never reproduce substantial source text or promise stylistic cloning.
- When using analysis resources in a new or continuing novel, read [analysis-to-novel.md](references/analysis-to-novel.md). Select mechanisms against the current book/chapter need, propose an original adaptation, and validate the pinned evidence before adding craft references to chapter context. Reference conclusions never become this novel's continuity facts.
- Keep successful analysis sections when another section fails. Resume only missing or stale work, and mark downstream analysis stale when the source fingerprint or scope changes.
- When the source is the user's own manuscript, use diagnosis mode and recommend bounded repairs without modifying the manuscript unless explicitly authorized.

## Write Fanfic from an Analysis

Read [fanfic.md](references/fanfic.md) before continuing an analyzed novel under its original names or writing a new story with its cast. Use only facts covered by an authorized analysis workspace, confirm continuation versus a new story, and keep `fanfic-handoff.md` in progress until its source scope, branch point, storyline, and pace are ready. A continuation branches from the last fully noted chapter ending. Write fanfic prose only in its own `novels/` workspace and do not treat unread chapters as canon.

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

Before writing prose, read [style-engine.md](references/style-engine.md) if `writing-style.md` exists in the novel workspace. Apply its positive guidance and the small anti-template baseline to the first draft; record chapter-specific expression overrides in the plan and context package. Keep the effective contract available for the final review and any repair.

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

After a complete draft, run one constrained Chinese-novel humanization pass by default. Preserve the chapter contract, effective writing style, and all protected facts; change only passages where a clustered expression problem harms reading, and leave sound passages intact. Keep the original draft when the user requests an experiment or comparison. Never promise a detector score or use a detector score as the sole acceptance criterion.

After review, commit continuity only when the final prose is `accepted`, or is `continue_with_warning` and still safe to continue. In a migrated workspace, update and validate YAML first, then regenerate Markdown views and SQLite; in a legacy workspace, update the Markdown ledgers directly. Then update affected character assets, quality debt, recovery record, and state index. Do not commit planned events, local-patch candidates, rewrite-needed drafts, or replan-blocked drafts as facts.

## Manage Context and Continuity

Read [context-and-continuity.md](references/context-and-continuity.md) when the request involves continuation, long-running consistency, character state, world rules, prior chapters, references, style, facts, resources, or payoffs.

For a continuity-enabled workspace, read the recovery record and only the YAML-selected facts (or legacy ledgers), profiles, world entries, prior tail, and volume assets relevant to the current chapter. If a source fingerprint no longer matches its stable source, mark the dependent delta, ledger entry, and context package stale; never overwrite user-edited prose to make them match.

Prefer the smallest context package that preserves coherence. Never load every chapter merely because it exists. Prioritize hard constraints, the current task, the previous handoff, relevant character facts, the active volume window, and unresolved promises.

Keep durable facts in their authoritative modules (`characters/`, `world-bible.md`, and `continuity/`), while each `chapters/chapter-XXX/` directory holds that chapter's plan, context package, prose, and review. The chapter context package is a minimal assembly of references and chapter-specific obligations, never a duplicated or competing fact store.

## Export Ready Chapters

When the user asks to merge, compile, or export generated chapters as a TXT file, run `scripts/novelctl.py export <workspace>` against the confirmed novel workspace. It exports only committed chapters whose accepted review still matches the prose and contract.

- Export only chapter prose. Never include plans or reviews.
- Default to `--source auto`: use the actual accepted prose path, including an accepted repair. The standalone exporter also defaults to stable chapters; use its `--include-drafts` only when the user explicitly requests unaccepted drafts.
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

This skill is a Codex-native writing workflow, not the runtime of `AI-Novel-Writing-Assistant-v2`. Read [ai-novel-writing-assistant-v2-adapter.md](references/ai-novel-writing-assistant-v2-adapter.md) only when the user asks to compare, align, import, export, distill production ideas, or develop against that project.

Do not directly operate its database, task queue, HTTP routes, or production runtime unless the user separately authorizes an implementation task.

## Skill Maintenance

For changes to analysis, adaptation, author corrections, or humanization, use the small [behavioral regression cases](references/behavioral-regressions.md) alongside deterministic tests. Check actual decisions and output evidence; field presence and successful scripts do not establish story quality. Honor the user's delegation preference when validating.

When maintaining this skill, treat a user's explicit acceptance of a proposed workflow, artifact, directory, or constraint change as authorization to update the relevant skill instructions in the same task. Update `SKILL.md` and the directly affected reference contracts together, then run a focused consistency check for conflicting paths, duplicate authority, and stale terminology. Do not treat an unconfirmed recommendation as a specification change, and preserve unrelated user edits.

## Finish Clearly

End each completed production action with:

- artifact created or updated;
- important assumptions or protected decisions;
- quality or continuity risks;
- state transition performed;
- Token usage for the completed model-generation step, separated into exact, estimated, or unavailable;
- one recommended next action.
