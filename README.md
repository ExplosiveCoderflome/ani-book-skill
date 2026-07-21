# Ani Book Skill

[![Validate](https://github.com/ExplosiveCoderflome/ani-book-skill/actions/workflows/validate.yml/badge.svg)](https://github.com/ExplosiveCoderflome/ani-book-skill/actions/workflows/validate.yml)
[English](README.en.md) · [更新记录](docs/releases/release-notes.md) · [贡献指南](CONTRIBUTING.md) · [安全政策](SECURITY.md)

> 用 Codex 把灵感、章节、连续性和跨书设定沉淀成一套可持续推进的小说生产系统。

当前版本：`0.3.1`（2026-07-22）

**Ani Book Skill** 是面向 Codex 的长篇中文小说生产系统：从模糊灵感开始，逐步形成故事发动机、卷与章节计划、稳定正文、连续性状态，以及可跨书复用的资产和共享 IP 正史。

它解决的不是“再写一段”，而是长篇最容易失控的三件事：每章为何值得读、几十章后事实如何不漂移、同一宇宙下多本书如何安全复用和审查设定。

## Codex 原生驱动，不是另一套 Agent 运行时

**Codex 本身是唯一的创作理解、规划、生成、审校与判断引擎。** Skill 定义过程合同；仓库里的 Python 只做确定性状态、校验、索引、冲突检测和导出。本项目不是 `AI-Novel-Writing-Assistant` 的运行时或子模块，不接入模型 Provider SDK、Web API、数据库权威、队列或自研 Agent Runtime；可见的 provider/model 信息仅用于 Codex 宿主实际暴露时的 Token 诊断。

```text
Codex：理解故事、提出设定与关系、规划、写作、审校、判断影响
  ↓
Skill / 合同：定义每个阶段必须消费什么、交付什么、如何验收
  ↓
Python：校验状态与证据、保护冲突、构建可重建索引、导出
  ↓
Markdown / YAML：作者可编辑的唯一权威；SQLite / JSONL：可丢弃派生物
```

维护本项目时，Skill 功能表面的修改只有在编译、完整测试和 Skill 校验通过后，才会自动同步到本机安装的 `produce-long-form-novel` Skill；同步完成后会再次检查一致性，并保留安装目录中的镜像专属文件。

![Ani Book Skill 工作流：灵感与选题、故事架构、正文审查、连续性存储构成一个可持续循环](assets/workflow-hero.png)

*从创意火花到跨书正史：每次定稿都留下可回读的依据，而不是失控地堆积上下文。*

## 现在能稳定完成什么

| 能力层 | 你得到的结果 | 保护机制 |
| --- | --- | --- |
| **从灵感到章节** | 读者定位、故事发动机、卷/章计划、正文、修订与审校 | 渐进确认、章节职责、章末牵引与质量债 |
| **长篇连续性** | 事实、伏笔、资源、角色和关系的可恢复状态 | 只有验收内容进入长期记忆；用户修改不会被覆盖 |
| **跨书知识图谱** | 可复用机制、共享角色/势力/道具、事件编年史与影响报告 | 每个节点有来源和指纹；图谱只给候选，不能替代权威工件 |
| **共享 IP 治理** | `fork` / `sync` 复用、正史候选、显式发布与可撤销委托 | 冲突不覆盖正文；影响审查只报告，不批量改写其他书 |

如果你是第一次写长篇，只需从灵感开始；如果你在维护一个系列或共享宇宙，可以从已有工作区和资产库继续。系统始终给出一个可恢复的下一步，而不是要求你手动拼接提示词和上下文。

## 核心生产链｜让小说、连续性与资产一起变稳

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

**关键原则：一次只稳定一章。** 不并行拼接同一章，不让未验收候选进入事实，也不把整本书塞入下一次上下文；定稿后才允许提炼为跨书资产或共享宇宙事件候选。

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

如果你明确表示“我没有想法”，Codex 会以顶尖连载网文作者兼商业责编的视角，先内部发散候选，再按读者幻想、核心杠杆、前三章兑现、长篇升级地图和追读承诺筛选，最后给你五条一句话开书种子：强钩子、人物成长、设定奇观、关系牵引和悬念追查。这五项是创意功能，不是机械分配的题材标签。你选中、混合或改写其中一条，或者给出自己的灵感后，Codex 会生成两份在冲突、主角路径、推进循环和调性上明显不同的新书简报预览。选择、混合或委托一份方向后，才确认频道、发布形态和主要阅读回报，并固化为 `novel-brief.md`。

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

### 跨书知识图谱与共享宇宙

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

### 2026-07-22

本次更新：把“无想法开书”从机械分类提升为经过商业网文质量筛选的五条灵感，并简化本机 Skill 镜像维护。

- 五条种子生成前先围绕读者幻想、核心杠杆、前三章兑现、升级地图和追读承诺发散与筛选，只向用户展示最终候选。
- 五种方向是强钩子、人物成长、设定奇观、关系牵引和悬念追查的创意功能，不再机械等同于题材标签。
- 当前检出的仓库直接作为可编辑 Skill 源；验证通过后自动同步到按环境解析的本机安装镜像，不再依赖固定机器路径。
- 跨书资产图谱、章节选择、共享宇宙编年史与影响审查仍保持上一版本的已交付能力与安全边界。

完整历史见 [更新记录](docs/releases/release-notes.md)。
