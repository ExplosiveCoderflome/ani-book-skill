# AI-Novel-Writing-Assistant-v2 适配边界

仅在用户明确要求与 `D:\code\AI-Novel-Writing-Assistant-v2` 对齐、导入、导出或开发集成时读取本页。

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

## 必须保持的项目边界

- 把本 Skill 当成 Codex 写作方法，不当成应用运行时。
- 新产品级 Prompt 继续通过 `server/src/prompting/`、Prompt Registry 和 runner 管理。
- 手动、批量和自动导演正文生产继续汇入统一章节 Runtime。
- Prompt 只声明上下文需求；Context Broker / Resolver 负责读取、预算和组装。
- 创作语义判断使用 AI-first 结构化理解；确定性逻辑只做结构、安全和已结构化输出后的处理。
- 局部章节质量问题不应自动阻断整本自动导演。
- 已有正文和用户编辑资产必须受保护。

## 集成前检查

1. 读取目标仓库的 `AGENTS.md`。
2. 读取相关 Wiki，而不是复制旧实现：
   - `docs/wiki/product/beginner-first-novel-completion.md`
   - `docs/wiki/workflows/volume-planning.md`
   - `docs/wiki/workflows/chapter-production-chain.md`
   - `docs/wiki/workflows/reader-experience-contract.md`
   - `docs/wiki/prompts/prompt-registry-and-structured-output.md`
   - `docs/wiki/rag/knowledge-and-context-assembly.md`
3. 使用当前共享类型和 Prompt schema 作为机器合同，不把 Markdown 标题直接当成 API schema。
4. 先设计显式导入/导出映射，再操作数据库或生产任务。
5. 未经用户单独授权，不修改目标项目、不调用生产 API、不启动自动导演任务。

## 导出原则

Markdown/YAML 是 Codex 工作区合同，不是项目数据库合同。需要导入项目时，先解析为项目当前共享类型，经过 schema 校验和用户确认，再交给现有 service/runtime。不要让 Skill 绕过项目的 Prompt Registry、StepModule、状态落库或恢复边界。
