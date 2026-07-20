# 产物与状态合同

## 持久化模式

### 预览模式

预览模式只在对话中交付一个有边界的产物，不创建目录、不写状态文件，也不把对话历史当作可靠的长期记忆。适用于试题材、试钩子、单次改稿和尚未确认的方案。

### 工作区模式

工作区模式将已确认的小说产物保存为 Markdown，并用 `novel-state.yaml` 记录进度。用户要求保存、本地写作、跨任务续写、章节生产、保护编辑或长期推进时必须使用此模式。

### 从预览升级

当用户确认将预览内容纳入长期小说时：

1. 确认小说标题和工作区位置；未指定位置时使用当前工作目录下的 `novels/<规范化书名>/`。
2. 仅保存用户已接受的产物；未确认草稿不写入权威文件。
3. 创建 `novel-state.yaml`，将已保存产物标为 `ready`。
4. 将下一个尚未生成的里程碑写为唯一 `next_action`。
5. 向用户报告保存位置、已保存文件和下一步。

## 推荐目录

```text
<novel-workspace>/
├── novel-state.yaml
├── novel-brief.md
├── story-bible.md
├── world-bible.md
├── characters/
├── continuity/
│   ├── baseline.md
│   ├── fact-ledger.md
│   ├── payoff-ledger.md
│   ├── resource-ledger.md
│   └── chapter-deltas/
├── production/
│   ├── recovery.md
│   ├── quality-debt.md
│   ├── token-usage.jsonl
│   └── token-summary.json
├── volumes/
└── chapters/
```

章节目录使用稳定编号。每个章节目录至少包含 `plan.md`、`context-package.md`、`draft.md` 与 `review.md`，例如 `chapters/chapter-001/context-package.md`。卷文件使用 `volumes/volume-01.md`。不要依赖易变标题作为唯一文件名。

### 章节装配与模块权威

采用“模块为权威源，章节为装配包”的布局：`characters/`、`world-bible.md` 与 `continuity/` 分别保存跨章节复用的角色、世界与连续性事实；`chapters/chapter-XXX/` 集中保存该章的合同、最小上下文、正文和审查。

`context-package.md` 是为单章读取、写作和审查准备的约束装配包，不是新的事实仓库。它应列出必要约束、稳定 ID、来源路径和本章解释，不能复制完整角色档案、世界设定或账本，更不能与模块权威源形成第二份可编辑真相。长期事实变化时，先更新相应模块权威源，再重新生成或标记受影响章节的上下文包为 `stale`。

## 状态索引

保持 YAML 简短，只记录恢复所需事实，不复制大段创作内容。

```yaml
schema_version: 3
workspace:
  persistence_mode: "workspace"
  promoted_from_preview: true
novel:
  title: "待定"
  mode: "original"
  current_stage: "novel_brief"
opening_choices:
  status: "confirmed"
  channel: "男频"
  publication_format: "免费连载"
  primary_reader_reward: "成长与反转"
director:
  mode: "milestone_approval"
  status: "idle"
  run_id: null
  current_step: null
  current_target: null
  requested_range: null
  stop_reason: null
artifacts:
  novel_brief:
    path: "novel-brief.md"
    status: "in_progress"
    source: "ai_generated"
    protected: false
    depends_on: []
    sha256: null
    approval: "required"
    updated_at: "2026-07-16T00:00:00+08:00"
continuity:
  baseline_chapter: "chapter_005"
  last_committed_chapter: "chapter_005"
  recovery_path: "production/recovery.md"
  quality_debt_open_count: 0
usage:
  ledger_path: "production/token-usage.jsonl"
  summary_path: "production/token-summary.json"
  exact_tokens: 0
  estimated_tokens: 0
  unavailable_events: 0
next_action:
  type: "complete_novel_brief"
  target: "novel_brief"
  reason: "新工作区尚未建立书级简报"
  requires_approval: false
```

使用状态：`missing`、`in_progress`、`ready`、`stale`、`blocked`。不要用 `completed` 掩盖仍需用户确认或仍缺上游依赖的产物。

使用来源：`ai_generated`、`user_edited`、`imported`。只要用户修改过产物，就将 `protected` 设为 `true`，除非用户明确交还 AI 重写。

`usage` 是 `production/token-usage.jsonl` 的简短累计投影，不是计费权威。精确值、估算值和不可统计事件必须分开；投影与账本不一致时，以账本为准并用 `scripts/token_usage.py summarize <workspace> --write` 重建汇总。用量文件不得进入章节上下文包。完整合同见 [token-usage.md](token-usage.md)。

新书设置使用 [novel-brief.md](novel-brief.md) 的确认状态。含有关键 `AI 推荐待确认` 设置的简报只能保持预览或 `in_progress`；不得标为 `ready`，也不得成为正式世界观、卷规划或章节的稳定上游。`用户授权 AI 决定` 可以进入权威资产，但必须保留授权范围和 AI 采用的具体值，不能伪装成用户亲自选择。

`schema_version: 1` 和 `2` 工作区仍可只读。任何写状态、步骤转换或导演运行前，必须显式执行 `scripts/novelctl.py migrate <workspace>`；迁移先备份原状态，再补充 v3 导演投影、依赖、现有文件指纹和唯一下一步。不得借迁移重写历史正文、计划或审查记录。

新工作区使用 `schema_version: 3`。导演模式使用 `milestone_approval` 或用户明确委托的 `auto`；导演状态使用 `idle`、`running`、`waiting_approval`、`blocked`、`completed`。`approval` 使用 `required`、`approved`、`delegated`、`not_required`。

`opening_choices` 是 `novel_brief` 的语义门槛，只保存频道、发布形态、主要阅读回报及其确认状态。状态为 `pending` 时唯一下一步必须是 `collect_opening_choices`，且控制器必须拒绝启动 `novel_brief`。用户说“由你决定”时记录为 `delegated`；含既有稳定简报的旧工作区迁移时可记录 `legacy_migrated`，不得反向猜测原选择。

`sha256` 记录最近一次已知文件内容。检测到用户修改时，先把该产物标记为 `source: user_edited` 和 `protected: true`，更新其指纹，再把依赖旧内容且未受保护的下游产物标为 `stale`。不得反向覆盖用户文件。

## 权威性顺序

当状态与文件冲突时，按以下顺序判断：

1. 用户明确指令。
2. 用户编辑且受保护的产物。
3. 稳定正文和已确认事实。
4. 当前上游规划文件。
5. `novel-state.yaml` 的进度投影。
6. 对话历史中的旧描述。

不要因为状态仍是 `in_progress` 就覆盖已经存在的正文。

## 依赖关系

- `novel-brief.md`：书级定位、读者频道倾向、阅读承诺、主角幻想、核心冲突、故事发动机、叙事与节奏偏好、篇幅预算、更新节奏和内容边界。它是后续世界、角色、卷规划和章节生产的书级约束来源。
- `story-bible.md`：长期对立、成长路径、揭示梯度、关系主线和结局方向。
- `world-bible.md`：会约束剧情的世界规则、势力、舞台、准入限制、代价和当前公共状态。每个可被章节调用的规则、势力或舞台都使用稳定 ID；正文和计划引用 ID，而不是凭模糊名称猜测。
- `characters/*`：角色欲望、功能、关系、硬事实、可变状态，以及可用于正文识别的外貌与呈现信息。
- `volumes/*`：卷职责、阶段回报、主要压力、转折、损失与卷末牵引。
- `chapters/*/plan.md`：本章任务、读者体验和义务合同。
- `chapters/*/draft.md`：正文事实源。
- `chapters/*/review.md`：针对某一正文版本的评估和修复记录。
- `continuity/baseline.md`：首次启用连续性时的起始快照；不是逐章历史补写。
- `continuity/fact-ledger.md`：稳定正文已发生的不可逆事实。
- `continuity/payoff-ledger.md`：承诺、伏笔、目标窗口、推进和兑现状态。
- `continuity/resource-ledger.md`：跨章关键资源的持有人、归属、可见性、状态和使用窗口。
- `continuity/chapter-deltas/*`：稳定章节对事实、角色、资源、关系、知情边界和伏笔的变更记录。
- `chapters/*/context-package.md`：某章实际使用的上下文来源、选择、裁剪、缺失和风险；它是章节装配包，不保存大段正文，也不取代角色、世界或连续性模块的权威事实。
- `production/recovery.md`：最后稳定章节、下一步、受保护资产、stale 资产和恢复风险。
- `production/quality-debt.md`：可继续生产但尚待回收的局部问题。
- `production/token-usage.jsonl`：每次模型生成调用的追加式用量账本；失败和重试也分别记录。
- `production/token-summary.json`：可从用量账本重建的精确、估算和不可统计分组汇总。

## 变更传播

- 修改新书定位：重新检查全部规划，但不自动改写正文。
- 修改故事宏观规划：将依赖它的未写卷战略标为 stale。
- 修改卷战略：将该卷旧骨架、节奏板和未写章节计划标为 stale。
- 修改节奏板：只影响对应节奏段内未写章节。
- 修改角色或世界硬事实：标记尚未写作且受影响的计划；已写正文进入审查，不自动覆盖。
- 修改正文：使基于旧正文的 review 和连续性摘要失效。
- 修改已提交的稳定正文：使依赖它的 chapter delta、相关 ledger 条目、context package 与 recovery 摘要变为 stale；先保护正文，再重新核对连续性。

## 写入规则

1. 预览模式不得写入文件；只有用户确认工作区模式后才能创建新工作区。
2. 写入前确认目标文件和影响范围。
3. 对受保护产物先提出修改方案；获得授权后再替换。
4. 先保存产物，再更新状态索引。
5. 写入失败时不要把状态标为 ready。
6. 每次只设置一个明确的 `next_action`。
7. 未确认的高影响推荐只保留在对话预览或 `in_progress` 草稿中；用户确认或授权 AI 决定后才能固化并推进依赖它的下游。
8. 工作区模式下，在生成产物可用后记录该次模型调用，再刷新用量汇总；运行时未暴露 usage 时记录 `unavailable` 原因，不得用字符数伪造 Token。
9. schema v3 的写状态操作通过 `scripts/novelctl.py` 执行；先验证产物，再记录模型用量，最后原子替换状态文件。
