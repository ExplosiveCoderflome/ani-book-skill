---
name: produce-long-form-novel
description: Produce, maintain, and export long-form Chinese novels through staged, editable artifacts. Use when Codex needs to turn an idea into a novel plan, design or revise volumes, generate chapter plans or prose, continue an existing novel, audit and repair chapters, export ready chapters as a TXT file, or decide the next production step from an existing Markdown/YAML novel workspace. Do not use for generic app development, database operations, or unrelated short-form copywriting.
---

# Produce Long-Form Novel

## Mission

Help a novice author move from a vague idea toward a complete long-form novel. Produce concrete, editable artifacts; preserve author decisions; and recommend one clear next step.

Use Markdown for creative artifacts and a small `novel-state.yaml` file for progress. In workspace mode, keep continuity ledgers, chapter deltas, context-package manifests, recovery status, and quality debt as readable Markdown. Do not require JSON unless the user explicitly requests machine integration or export.

## Choose Persistence Mode

Choose one mode before producing files:

- **Preview mode**: Return a bounded artifact in the conversation. Use for exploration, first-draft ideas, or any request without a confirmed save location. Do not create files or infer a workspace from chat history.
- **Workspace mode**: Write Markdown artifacts and `novel-state.yaml` into one novel workspace. Use when the user asks to save, create a workspace, write locally, continue across tasks, protect edits, generate chapters, or otherwise confirms durable production.
- **Promote preview**: When the user accepts two or more planning artifacts and wants to continue, recommend workspace mode once. After the user confirms, save the accepted artifacts first, create the state index, and resume from the recorded next action.

Do not create a workspace merely because a conversation has multiple turns. If workspace mode is confirmed but no location is supplied, use a safe `novels/<normalized-title>/` directory under the current working directory, then state the chosen path before writing.

## Route the Request

Choose one primary route before acting:

1. **Create a novel**: turn an idea into positioning, a hook package, a story engine, and the first planning artifacts.
2. **Plan or revise volumes**: create or update volume strategy, skeletons, beat sheets, or chapter lists.
3. **Plan or draft a chapter**: create the chapter contract, draft prose, assess it, and update stable state.
4. **Audit or repair**: diagnose a supplied plan or chapter, apply the smallest useful repair, and preserve successful content.
5. **Continue an existing novel**: inspect current artifacts, recover the next valid production step, and continue without rewriting protected work.

Read [workflow-routing.md](references/workflow-routing.md) when the request spans routes, the next step is unclear, or an existing workspace may be incomplete.

Read [novel-brief.md](references/novel-brief.md) when creating or revising a novel brief. Keep its reader, length, narrative and writing-preference settings authoritative for later planning and chapter production.

## Start from Facts

When a workspace exists:

1. Locate and read `novel-state.yaml` first.
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

1. State necessary assumptions briefly; use sensible defaults instead of blocking on expert terminology.
2. Consume the authoritative upstream artifact rather than reconstructing it from chat history.
3. Produce one coherent artifact or one bounded batch.
4. Check its acceptance conditions.
5. Update `novel-state.yaml` only after the artifact is usable.
6. Report what was produced, what changed, what remains uncertain, and the recommended next action.

Do not attempt to generate an entire long novel in one response. Advance through resumable milestones and keep each deliverable editable.

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

Read [continuity-ledgers.md](references/continuity-ledgers.md) before bootstrapping continuity for an existing workspace, creating a context package, accepting a chapter, updating a ledger, recording quality debt, or recovering after an interruption.

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

Before drafting a new chapter in a continuity-enabled workspace, create its concise context package. It must identify selected authority sources, required constraints, deliberately omitted material, and any missing hard constraint. Do not copy long prose into the package.

After a complete draft, run one constrained Chinese-novel humanization pass by default. Preserve the chapter contract and all protected facts, then reduce clustered template patterns, explanatory narration, mechanically even cadence, and undifferentiated character voices. Keep the original draft when the user requests an experiment or comparison. Never promise a detector score or use a detector score as the sole acceptance criterion.

After review, commit continuity only when the final prose is `accepted`, or is `continue_with_warning` and still safe to continue. Write one chapter delta, then update the ledgers, affected character assets, quality debt, recovery record, and state index. Do not commit planned events, local-patch candidates, rewrite-needed drafts, or replan-blocked drafts as facts.

## Manage Context and Continuity

Read [context-and-continuity.md](references/context-and-continuity.md) when the request involves continuation, long-running consistency, character state, world rules, prior chapters, references, style, facts, resources, or payoffs.

For a continuity-enabled workspace, read the recovery record and only the ledgers, profiles, world entries, prior tail, and volume assets relevant to the current chapter. If a source fingerprint no longer matches its stable source, mark the dependent delta, ledger entry, and context package stale; never overwrite user-edited prose to make them match.

Prefer the smallest context package that preserves coherence. Never load every chapter merely because it exists. Prioritize hard constraints, the current task, the previous handoff, relevant character facts, the active volume window, and unresolved promises.

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

## Finish Clearly

End each completed production action with:

- artifact created or updated;
- important assumptions or protected decisions;
- quality or continuity risks;
- state transition performed;
- one recommended next action.
