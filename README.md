# Ani Book Skill

[![Validate](https://github.com/ExplosiveCoderflome/ani-book-skill/actions/workflows/validate.yml/badge.svg)](https://github.com/ExplosiveCoderflome/ani-book-skill/actions/workflows/validate.yml)
[English](README.en.md) · [更新记录](docs/releases/release-notes.md) · [贡献指南](CONTRIBUTING.md) · [安全政策](SECURITY.md)

> 把“我想写一部长篇”变成一条能持续跑下去的创作生产线。

**Ani Book Skill** 是面向 Codex 的长篇中文小说工作流。它不只替你补一段正文，而是把选题判断、故事发动机、章节推进、审校修复和长期连续性连接成一套可恢复、可追溯、始终由作者掌控的本地流程。

从一个模糊灵感开始，到几十章以后仍知道人物此刻知道什么、伏笔该在哪里兑现、这一章为什么值得读——这正是它要解决的问题。

## Codex 原生驱动，不是另一套 Agent 运行时

**Codex 本身是唯一的创作理解、规划、生成、审校与判断引擎。** Skill 定义过程合同；仓库里的 Python 只做确定性状态、校验、索引、冲突检测和导出。本项目不是 `AI-Novel-Writing-Assistant` 的运行时或子模块，不接入模型 Provider SDK、Web API、数据库权威、队列或自研 Agent Runtime；可见的 provider/model 信息仅用于 Codex 宿主实际暴露时的 Token 诊断。

![Ani Book Skill 工作流：灵感与选题、故事架构、正文审查、连续性存储构成一个可持续循环](assets/workflow-hero.png)

*从创意火花到下一章：每次回灌都让小说更完整，而不是让上下文更失控。*

## 核心工作流｜让小说越写越稳

这不是“生成一段，再生成一段”的线性对话，而是一个每章都会校准、积累并恢复的创作闭环：

| 阶段 | 你在推进什么 | 系统帮你守住什么 |
| --- | --- | --- |
| **01 · 找到方向** | 读者频道、阅读回报、榜单机会或已有故事的真正问题 | 不把模糊灵感过早固化成大纲 |
| **02 · 搭好发动机** | 主角欲望、世界规则、角色关系、卷级承诺 | 每一卷都有明确的追读动力和回报窗口 |
| **03 · 完成一章** | 章节合同、最小上下文、完整正文、人性化修订与审查 | 当前章目标、人物边界、转折与章末牵引不丢失 |
| **04 · 变成下一章的底座** | 事实、伏笔、资源、关系变化和恢复检查点 | 只有验收过的内容进入长期记忆，下一章从可信状态开始 |

```text
方向判断 → 故事发动机 → 章节计划 → 完整正文 → 审查回灌
    ↑                                                    ↓
    └─────────────── 连续性状态与下一章 ───────────────┘
```

**关键原则：一次只稳定一章。** 不并行拼接同一章，不让未验收候选进入事实，也不把整本书塞入下一次上下文。

## 你会得到什么

| 你正在面对的问题 | Ani Book Skill 的做法 | 最终留下什么 |
| --- | --- | --- |
| “这个题材现在还有没有机会？” | 分析公开榜单的标题、标签与简介，只给基于元数据的方向判断 | 榜单快照、趋势报告、机会卡 |
| “我有设定，但不知道第一卷怎么拉住人。” | 用渐进确认锁定读者回报，再建立故事发动机、卷级承诺和章节职责 | 可编辑的简介、世界观、角色、卷纲与节奏板 |
| “章节能写，但越写越散。” | 每章固定经过计划 → 上下文 → 完整正文 → 人性化二稿 → 审查 → 回灌 | 正文、审查、差分与唯一下一步 |
| “写到五十章后，上下文会不会爆？” | YAML 保存权威事实，SQLite 只做可重建检索；按当前章筛选有限上下文 | 可恢复的连续性状态、检查点与只读台账视图 |
| “每一步到底用了多少 Token？” | 每次模型生成调用独立记录，严格区分精确值、tokenizer 估算和运行时不可获取 | 追加式用量账本与按步骤、模型汇总 |

## 它和普通提示词有什么不同？

- **先锁定读者期待，再扩写世界。** 模糊需求不会被一次性问卷淹没；每轮只处理 2–3 个真正影响后续的选择。
- **一章一章地稳定推进。** 不拼接多个片段，也不让未验收的后续候选污染故事事实。
- **把长期记忆当成工程问题处理。** 事实、资源、伏笔、角色动态和关系约束都有稳定 ID、来源章节与恢复路径。
- **内容留在你的本地工作区。** 小说、拆书来源和趋势快照默认不提交到公开仓库；你可以审阅、修改、迁移和备份所有工件。

## 三种开始方式

### 从一个灵感开始

```text
使用 $produce-long-form-novel 帮我从一个灵感开始规划长篇小说。
```

它会先帮你确定读者频道、连载形态和主要阅读回报，而不是立刻抛出一份不可控的万字大纲。

### 把已有小说继续写下去

```text
使用 $produce-long-form-novel 继续 novels/<小说名>/，先判断上一章稳定后下一步该做什么。
```

它会读取必要的恢复记录、上章承接、参与角色和活跃伏笔，只装配当前章真正需要的上下文。

### 找方向或拆解已授权作品

```text
使用 $produce-long-form-novel 分析近期男频玄幻榜单的题材构成，并生成机会卡。
```

```text
使用 $produce-long-form-novel 拆解这份有权使用的小说文本，先建立覆盖范围、分段笔记和快速总览。
```

## 为长篇而设计的连续性

当小说进入长期续写阶段，可将连续性迁移为：

```text
YAML 权威事实
   ├── 事实 / 伏笔 / 资源 / 角色动态 / 关系约束
   ├── 每 10 章或卷末检查点
   └── Markdown 可读台账视图

SQLite 可重建索引
   └── 只负责检索和上下文候选；丢失或过期时直接回退 YAML
```

这意味着章节越多，并不需要把整本书塞进模型上下文；索引也永远不能反向修改你的故事事实。

### 跨书资产图谱（第一至三期）

可在本机私有的、默认不提交 Git 的 `libraries/` 中管理两类已定稿资产：可复用的题材/机制卡（`reusable`）和共享 IP 正史（`universe`）。每本 schema v3 小说可以按资产选择 `fork`（独立副本）或 `sync`（受保护的共享链接）。同步只报告更新或冲突，不会覆盖正文；作者可显式保留本书、采用共享版本，或在已批准/委托时提交正史更新。

```powershell
python scripts/asset_graph.py init libraries
python scripts/asset_graph.py publish libraries <accepted-candidate.yaml> --author-approved
python scripts/asset_graph.py import libraries novels/<小说名> <资产ID> --mode sync
python scripts/asset_graph.py reconcile libraries novels/<小说名>
python scripts/asset_graph.py context libraries novels/<小说名> --assets <资产ID> --max-depth 2 --max-chars 4000

# 为某章锁定已选资产、装配有限上下文，并在定稿后验证候选
python scripts/asset_graph.py validate-selection libraries novels/<小说名> novels/<小说名>/context-packages/chapter-001.assets.yaml
python scripts/novelctl.py context novels/<小说名> --chapter 1 --asset-library libraries --asset-selection context-packages/chapter-001.assets.yaml --output context-packages/chapter-001.md
python scripts/asset_graph.py verify-candidate novels/<小说名> novels/<小说名>/production/asset-candidates/chapter-001/<资产ID>.yaml

# 单个资产库默认对应一个共享 IP 宇宙；先审查事件与影响，再显式发布
python scripts/asset_graph.py delegate-universe libraries --enabled
python scripts/asset_graph.py canon-check libraries
python scripts/asset_graph.py timeline libraries
python scripts/asset_graph.py impact libraries <正史候选.yaml> --workspace novels/<小说名>
```

每个库默认是一个共享 IP 宇宙。已发布的 `universe/event` 用稳定序号、参与资产、影响和可选先后关系派生正史编年史；`canon-check` 检查端点、证据、顺序与环，`impact` 仅报告命令中明确列出的小说会受到的同步链接、章节选择和时间线邻域，绝不改写任何工件。正史仍需作者批准、按资产委托或未撤销的宇宙级 Codex 委托；图谱只从验收连续性和已批准/委托的定稿资产派生，并且只返回有限候选，写作前 Codex 会回读 YAML/Markdown 权威源。完整规则见 [跨书资产图谱合同](references/cross-book-asset-graph.md)。

## 安装与本地工具

将本仓库安装为个人 Codex Skill 后，直接在 Codex 中使用 `$produce-long-form-novel`。完整行为契约见 [SKILL.md](SKILL.md)。

需要 Python 3.10+；使用 YAML 连续性存储前安装依赖：

```powershell
python -m pip install -r requirements.txt
```

```powershell
# 从灵感建立 schema v3 工作区，并查看唯一下一步
python scripts/novelctl.py init novels/<小说名> --title "<小说名>"
python scripts/novelctl.py set-opening-choices novels/<小说名> --channel "男频" --publication-format "免费连载" --primary-reader-reward "成长与反转"
python scripts/novelctl.py status novels/<小说名> --format markdown
python scripts/novelctl.py next novels/<小说名>

# 显式迁移旧工作区；正式迁移前会保留状态备份
python scripts/novelctl.py migrate novels/<小说名> --dry-run
python scripts/novelctl.py migrate novels/<小说名>

# 恢复中断、校验用户编辑，并授权连续写作范围
python scripts/novelctl.py validate novels/<小说名>
python scripts/novelctl.py reconcile novels/<小说名>
python scripts/novelctl.py approve novels/<小说名> --target chapter_range --range-start 1 --range-end 5

# 导出所有稳定章节
python scripts/novelctl.py export novels/<小说名>

# 导出已完成章节
python scripts/export_novel_txt.py novels/<小说名>

# 校验连续性来源与状态
python scripts/check_continuity_workspace.py novels/<小说名>

# 将旧 Markdown 台账安全迁移为 YAML 权威数据
python scripts/continuity_store.py migrate novels/<小说名> --dry-run
python scripts/continuity_store.py migrate novels/<小说名>

# 为已授权参考作品建立本地检索
python scripts/analysis_retrieval.py build analyses/<名称>

# 校验和比较榜单元数据快照
python scripts/trend_snapshot.py validate trends/<范围>/snapshots/<日期>/<platform>-<chart>.jsonl

# 记录并汇总一次模型生成调用的 Token 用量
python scripts/token_usage.py record novels/<小说名> --route novel --step chapter_draft --measurement unavailable --reason runtime_usage_not_exposed
python scripts/token_usage.py summarize novels/<小说名> --write
```

`novels/`、`analyses/`、`trends/` 和 `libraries/` 默认被忽略，避免把真实小说、来源文本、研究快照或私有资产库误推送到公开仓库。

## 清晰的边界

- 榜单路线只处理公开元数据，不读取小说正文，也不伪造“趋势必然上涨”的结论。
- 拆书只处理你有权使用的文本，输出可迁移的机制，不提供贴近原作的仿写。
- 这不是小说托管平台，也不会替代作者对作品、隐私和发布的最终判断。

## 来源与许可

本项目由 [AI-Novel-Writing-Assistant](https://github.com/ExplosiveCoderflome/AI-Novel-Writing-Assistant) 的维护者，基于其中的长篇生产经验蒸馏而成；它是独立、文档优先的 Codex Skill，不包含原项目的前后端、数据库或运行时服务，也不存在运行时依赖。

本仓库文件采用 [Apache License 2.0](LICENSE)。欢迎提交经过授权、脱敏的示例、测试和工作流改进；提交前请阅读 [贡献指南](CONTRIBUTING.md) 与 [行为准则](CODE_OF_CONDUCT.md)。

最新变化请见 [更新记录](docs/releases/release-notes.md)。

## 最新更新

### 2026-07-20

重大更新：跨书资产图谱现已覆盖章节生产、共享宇宙编年史与影响审查，并持续完善长篇生产控制与逐生成步骤 Token 记账。

- 本机私有的 `libraries/` 可保存已定稿的可复用机制和共享 IP 正史；每本 schema v3 小说按资产选择独立 `fork` 或受保护的 `sync`。
- 同步只报告更新或冲突，不覆盖正文；作者可显式保留本书、采用共享版本，或在批准/委托后提交正史更新。
- 图谱只从验收连续性及已批准/委托的资产派生，查询只返回有限候选，写作前仍回读 YAML/Markdown 权威源。
- 跨书资产现在可被章节显式选择并锁定版本；选中资产冲突会阻断上下文、正文和审校，定稿后的提炼资产仍须验证证据并走既有治理发布。
- 每个私有资产库默认对应一个共享 IP 宇宙；已发布的 `universe/event` 可以用稳定序号、参与资产、影响与先后关系派生正史时间线。
- `canon-check`、`timeline` 与 `impact` 先审查事件端点、顺序、循环和明确工作区影响；影响报告只给出风险，不改写正文、选择清单或本书快照。
- 宇宙级 Codex 委托可显式启用或撤销，且不改变可复用资产的按资产治理；正史仍须走作者批准或有效委托的显式发布。
- `novelctl.py` 统一负责工作区初始化、唯一下一步、校验、恢复、步骤转换、上下文、检查点、用量和稳定正文导出。
- `novel-state.yaml` 升级为 schema v3；旧 v1/v2 工作区只读兼容，必须显式迁移并先备份。
- 用户修改过的正文和规划会被保护，其未写下游只标记为 `stale`，不会被自动覆盖。
- 每次模型调用独立记账，失败和重试不会被最终产物总数掩盖。
- 精确值、兼容 tokenizer 估算和不可获取事件严格分开，缓存与推理 Token 不重复累加。
- 用量账本不进入小说创作上下文，不把 Token 数误当成质量或统一账单。

完整历史见 [更新记录](docs/releases/release-notes.md)。
