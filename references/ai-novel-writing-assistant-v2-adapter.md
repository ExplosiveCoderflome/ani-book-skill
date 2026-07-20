# AI-Novel-Writing-Assistant-v2 适配边界

仅在用户明确要求与 `D:\code\AI-Novel-Writing-Assistant-v2` 对齐、导入、导出或开发集成时读取本页。

该项目也可作为本 Skill 的只读生产经验来源。蒸馏时只迁移稳定的领域方法、产物合同、验收边界和恢复原则；不要复制运行时实现或制造源码依赖。

## 概念映射

| Skill 产物 | 项目概念 |
| --- | --- |
| `novel-brief.md` / `story-bible.md` | 小说基础信息、Story Macro、Book Contract |
| `world-bible.md` | 本书世界、StoryWorldSlice、World Context |
| `characters/*` | 角色阵容、角色硬事实、角色动态 |
| 卷战略与卷骨架 | `VolumeStrategyPlan`、`VolumePlan` |
| 节奏板 | `VolumeBeatSheet` |
| 章节计划 | task sheet、scene cards、Chapter Obligation Contract |
| 读者体验 | `ReaderExperienceContract` |
| 章节正文 | `Chapter.content` / chapter draft artifact |
| 审查与修复 | acceptance、audit、patch repair、heavy repair、quality debt |
| 连续性更新 | fact ledger、artifact delta、resource/payoff/relation updates |
| `analyses/*/source-manifest.md` 与 `coverage-map.md` | 拆书 source range、document version、source scope 与章节缓存 |
| `analyses/*/notes/*` | `BookAnalysisSourceCache` 中按来源范围和模型参数缓存的 segment notes |
| `analyses/*/sections/*` | `BookAnalysisSection` 的 Markdown、structured data 与 evidence |
| `evidence-ledger.md` | 字段级 evidence、章节锚点与原文 offset；Skill 额外记录置信度和反例 |
| `pattern-cards.md` | 从拆书结论提炼的原创机制卡；项目侧可映射到写法资产或续写上下文 |
| `graph/nodes.jsonl` 与 `graph/edges.jsonl` | Skill 的轻量 BookGraph；导入项目时映射到当前知识图谱或结构化 RAG 合同，不直接写数据库 |
| `retrieval/analysis-index.sqlite3` | 可重建的本地派生索引，不作为项目数据库或知识库权威源 |

## 必须保持的项目边界

- 把本 Skill 当成 Codex 写作方法，不当成应用运行时。
- 新产品级 Prompt 继续通过 `server/src/prompting/`、Prompt Registry 和 runner 管理。
- 手动、批量和自动导演正文生产继续汇入统一章节 Runtime。
- Prompt 只声明上下文需求；Context Broker / Resolver 负责读取、预算和组装。
- 创作语义判断使用 AI-first 结构化理解；确定性逻辑只做结构、安全和已结构化输出后的处理。
- 局部章节质量问题不应自动阻断整本自动导演。
- 已有正文和用户编辑资产必须受保护。
- 拆书总览先于其他小节生成并作为定位锚点；其他小节仍须由各自 notes 支撑。
- 只续跑缺失或失败的小节，保留成功小节、来源范围、预算用量和证据绑定。
- Skill 的事实/推断/假设、反例与覆盖地图是文件层增强项；导入项目时不得塞入不兼容字段，应先做显式映射。

## 可蒸馏能力

| 旧项目经验 | Skill 落点 |
| --- | --- |
| 自动导演阶段与恢复 | `auto-director-and-recovery.md`、`novel-state.yaml` 导演投影 |
| Book Contract / Story Macro | `novel-brief.md`、`story-bible.md` |
| 卷战略、骨架与节奏窗口 | `story-and-volume-planning.md` 与卷产物 |
| Chapter Obligation Contract | `chapter-production.md` 的共享章节合同 |
| Reader Experience Contract | 读者问题、回报、转折、净变化与章末牵引 |
| Context Broker | 最小 `context-package.md` 与确定性上下文装配 |
| acceptance / repair / debt | `quality-and-repair.md` 的有限质量循环 |
| 状态、资源与伏笔回灌 | YAML 连续性权威源和章节 delta |
| Token 与任务诊断 | 追加式 Token 账本、状态校验和恢复报告 |

明确不迁移 React、Express、Prisma、HTTP 路由、任务队列、Provider 适配层、自研 Agent Runtime、Prompt Workbench UI 和桌面打包代码。

## 集成前检查

1. 读取目标仓库的 `AGENTS.md`。
2. 读取相关 Wiki，而不是复制旧实现：
   - `docs/wiki/product/beginner-first-novel-completion.md`
   - `docs/wiki/workflows/volume-planning.md`
   - `docs/wiki/workflows/chapter-production-chain.md`
   - `docs/wiki/workflows/reader-experience-contract.md`
   - `docs/wiki/prompts/prompt-registry-and-structured-output.md`
   - `docs/wiki/rag/knowledge-and-context-assembly.md`
   - 与拆书、Prompt Registry、结构化输出和知识发布相关的当前 Wiki 页面
3. 使用当前共享类型和 Prompt schema 作为机器合同，不把 Markdown 标题直接当成 API schema。
4. 先设计显式导入/导出映射，再操作数据库或生产任务。
5. 未经用户单独授权，不修改目标项目、不调用生产 API、不启动自动导演任务。

## 导出原则

Markdown/YAML 是 Codex 工作区合同，不是项目数据库合同。需要导入项目时，先解析为项目当前共享类型，经过 schema 校验和用户确认，再交给现有 service/runtime。不要让 Skill 绕过项目的 Prompt Registry、StepModule、状态落库或恢复边界。
