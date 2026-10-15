<div align="center">

# Ani Book Skill

**让灵感、拆书研究和长篇连载在 Codex 中持续推进。**

从选题与开书，到章节定稿、连续性维护、同人创作和跨书设定复用。<br>
创作留在你可编辑的本地文件里，每一步都有依据和下一步。

[![Validate](https://github.com/ExplosiveCoderflome/ani-book-skill/actions/workflows/validate.yml/badge.svg)](https://github.com/ExplosiveCoderflome/ani-book-skill/actions/workflows/validate.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

[开始使用](#开始使用) · [能力一览](#能做什么) · [本地阅读台](#本地阅读台) · [更新记录](docs/releases/release-notes.md) · [English](README.en.md)

</div>

![从灵感、故事架构到章节审查与连续性沉淀的创作循环](assets/workflow-hero.png)

> **一句话概括：** Codex 负责理解、规划、写作与判断；Skill 规定创作流程；本地工具负责状态、校验、检索与导出。作者始终可以阅读和修改 Markdown / YAML 原稿。

## 能做什么

| 从哪里开始 | 可以得到什么 |
| --- | --- |
| **还没有故事** | 明确说“没有想法”时，先看五条不同创意角度的开书种子；只有模糊方向时，先确认读者频道、发布形态和主要阅读回报，再比较两份差异明确的新书简报。 |
| **想找有潜力的题材** | 根据公开榜单的标题、标签、简介等元数据整理快照、趋势报告和机会卡；把市场线索转成创作选择。 |
| **想拆解一部作品** | 对有权使用的文本先估算长度与切段量，确认全文或部分范围，再按本书分析视角建立分段笔记、角色卡、证据与可检索的机制。 |
| **想写同人** | 基于已授权、已读范围内的原作事实，选择从最后一个完整记录的章末续写，或沿用设定写新故事；先完成 `fanfic-handoff.md`，再进入独立小说工作区。 |
| **正在连载长篇** | 从故事发动机、卷纲和章节职责，推进到完整正文、人性化修订、审查和连续性回灌；中断后可恢复到明确的下一步。 |
| **想稳定作品写法** | 从作者样文、已验收章节或授权拆书结论提炼可编辑的写法合同；本书选用后，在初稿、反模板化二稿、审校和定点修文中持续使用。 |
| **在写系列或共享宇宙** | 从已定稿内容提炼可复用资产，按 `fork` / `sync` 引用，检查正史时间线与影响范围，并由作者控制发布和冲突处理。 |

### 让研究真正进入创作

拆书结果不只是一份长报告。范围估算帮助决定本次读到哪里；`analysis-lens.md` 先比较核心阅读承诺，再把题材核心、心理推进、关系结构和表层兑现轴分开固定；分段笔记与角色卡保存证据，检索索引帮助找回相关内容。原文只用于已授权分析，检索结果也不能替代笔记中的可核实依据。

在本地阅读台的拆书工作台中，可以查看计划范围、实际覆盖、缺口、专项分析和机制证据，并为指定小说与章节准备接入请求。Codex 会结合目标书的计划提出**原创改造**，把确认过的参考清单装入章节上下文，并在审校时检查实际采用效果。参见[拆书规则](references/book-analysis.md)、[检索说明](references/book-analysis-retrieval.md)与[拆书接入小说](references/analysis-to-novel.md)。

### 一章一章地稳定推进

`方向 → 故事发动机 → 卷/章计划 → 当前章正文 → 修订与审查 → 连续性 → 下一章`

每章只装配当前需要的上下文。事实、伏笔、资源、角色动态与关系约束在验收后进入长期状态；未验收候选不会成为故事事实。YAML 与已定稿 Markdown 是权威，SQLite 和阅读视图可以重建。用户对正文和工件的修改受到保护；旧工作区可以检查、备份并显式迁移。

可选的 [写法资产与表达合同](references/style-engine.md) 把“本书该怎么写”和“哪些模板化表达要避免”记录为少量可审阅规则。首次开书无需配置；需要时可绑定本书写法，在章节生成时就应用，审校只按具体正文证据提出修改，不用检测器分数或机械禁词决定成稿。

需要外部增强时，可在小说工作区登记 GitHub 上的写法或去 AI 化 Skill。系统先把候选下载到私有目录，固定 commit、审阅规则并经作者确认后才启用；章节生产不会静默联网，远端内容也不能覆盖本地合同。

## 开始使用

将本仓库安装为个人 Codex Skill 后，在 Codex 中调用 `$produce-long-form-novel`。需要 Python 3.10+；使用 YAML 连续性存储前安装依赖：

```powershell
python -m pip install -r requirements.txt
```

按你的起点直接提出任务：

| 你的起点 | 给 Codex 的示例 |
| --- | --- |
| 没有想法 | “使用 `$produce-long-form-novel`，我还没有小说想法，先给我开书种子。” |
| 有一个灵感 | “使用 `$produce-long-form-novel`，根据这个灵感规划长篇小说：……” |
| 查找题材 | “使用 `$produce-long-form-novel`，分析近期公开男频玄幻榜单的题材构成，生成机会卡。” |
| 拆解参考作品 | “使用 `$produce-long-form-novel`，拆解这份我有权使用的小说文本，先估算规模、确认阅读范围和分析重点。” |
| 写同人 | “使用 `$produce-long-form-novel`，基于这份已完成拆书的原作，按已读范围设计同人续篇。” |
| 继续已有小说 | “使用 `$produce-long-form-novel`，继续 `novels/<小说名>/`，先判断当前状态和下一步。” |

**新书引导会逐步确认关键选择。** 明确“没有想法”时，五条种子分别侧重强钩子、人物成长、设定奇观、关系牵引和悬念追查；选中、混合或改写后，再看两份在冲突、主角路径、推进循环和调性上不同的简报。只给模糊请求时，首轮仅确认读者频道、发布形态和主要阅读回报，不会一次抛出完整问卷。方向选定后才固化为 `novel-brief.md`。

也可以从命令行检查本地工作区：

```powershell
python scripts/novelctl.py init novels/<小说名> --title "<小说名>"
python scripts/novelctl.py status novels/<小说名> --format markdown
python scripts/novelctl.py next novels/<小说名>
python scripts/novelctl.py validate novels/<小说名>
python scripts/novelctl.py export novels/<小说名>
```

已有工作区需要迁移时，先运行 `python scripts/novelctl.py migrate novels/<小说名> --dry-run`。完整流程和工件约束见 [SKILL.md](SKILL.md)、[工作流路由](references/workflow-routing.md)与[工件合同](references/artifact-contracts.md)。

## 本地阅读台

可选的 **ANI 本地阅读台** 在浏览器中只读展示 `novels/` 和 `analyses/`：书架、完整文件树、中文全文搜索、页内目录、字号与明暗主题、正文上下章导航，以及拆书覆盖和机制证据视图。文件变化后会自动刷新；不安装阅读台也能使用 Skill。

需要 Node.js 22.18+。在仓库根目录运行：

```powershell
./apps/workspace-reader/start-local.ps1
```

打开 <http://127.0.0.1:8790>。已有其他位置的工作区可用 `-Roots 'C:/writing', 'D:/research'` 指定；阅读台只读取明确配置的本地目录，不调用模型，也不改写稿件或状态。[查看阅读台说明](apps/workspace-reader/README.md)。

## 长期创作如何保持可控

- **本地文件可编辑。** `novels/`、`analyses/`、`trends/`、`libraries/` 默认不提交到 Git，保护真实稿件、来源文本、研究快照和私有资产。
- **状态可恢复。** 章节验收、检查点、状态校验和唯一下一步让长篇中断后能继续；Token 用量分别记录精确值、估算值或运行时不可获取，不混为一谈。
- **跨书复用有边界。** `libraries/` 管理可复用机制和共享 IP 正史；`sync` 报告更新或冲突，不覆盖正文。时间线校验和影响审查只报告范围，正史发布需要作者批准或有效委托。[查看跨书资产图谱合同](references/cross-book-asset-graph.md)。
- **研究有来源。** 榜单路线只用公开元数据；拆书只用有权使用的文本，记录覆盖与证据，不把原作措辞当成可直接搬用的正文。

## 项目结构

```text
SKILL.md                 Codex 创作流程入口
references/              新书、拆书、同人、章节与跨书工件合同
scripts/                 确定性状态、校验、检索、资产图谱与导出
apps/workspace-reader/   可选的本地只读阅读台
novels/ analyses/        本地私有创作与研究工作区（默认忽略）
trends/ libraries/       本地私有趋势快照与跨书资产（默认忽略）
```

Codex 本身是唯一的创作理解、规划、生成、审校与判断引擎；本项目没有独立的模型 Provider、Agent 运行时或数据库权威。它由 [AI-Novel-Writing-Assistant](https://github.com/ExplosiveCoderflome/AI-Novel-Writing-Assistant) 维护者基于长篇生产经验整理，但不依赖原项目的前后端或服务。

代码与文档采用 [Apache License 2.0](LICENSE)。更多细节见[更新记录](docs/releases/release-notes.md)、[贡献指南](CONTRIBUTING.md)和[安全政策](SECURITY.md)。

## 最新更新

### 2026-10-15

- 新增：GitHub 写法与去 AI 化 Skill 候选的内容、大小及版本核验。
- 优化：核心承诺贯穿拆书与创作，作者纠正持续生效；已选方向可以直接推进，题材专属机制按需采用。
- 修复：定稿保护与审校版本绑定、必需上游和多卷检查、连续性恢复及稳定正文导出。

完整历史见[更新记录](docs/releases/release-notes.md)。
