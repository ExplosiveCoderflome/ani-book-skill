# Codex 原生长篇小说生产项目开发计划

## 目标

将 Ani Book Skill 建设为独立的 Codex 原生长篇小说生产系统。Codex 负责理解、规划、创作、审校和修复；Skill 提供流程与领域合同；确定性脚本负责状态、校验、连续性、Token、检查点和导出。

首版保留单一 `$produce-long-form-novel` Skill，使用 Markdown/YAML 作为权威数据，SQLite 仅作可重建索引，不引入模型 Provider、Web UI、数据库、任务队列或自研 Agent Runtime。

## 交付标准

- 从模糊灵感建立工作区，完成书级、卷级和逐章生产。
- 跨 Codex 任务读取权威状态，恢复到唯一下一步。
- 在用户批准的章节范围内串行推进，每章稳定后才规划下一章。
- 保护用户编辑和稳定正文；上游变化只让受影响的未写产物失效。
- 局部质量问题进入质量债，仅结构性失配或硬风险停止全局链。
- 每次模型生成调用记录为 `exact`、`estimated` 或 `unavailable`。
- 支持工作区校验、连续性检查点和稳定正文导出。

## 架构

```text
用户自然语言
  -> Codex
    -> produce-long-form-novel
      -> references 中的生成与验收合同
      -> novelctl 与专用确定性脚本
        -> Markdown/YAML 小说工作区
        -> 可重建 SQLite / 汇总 / 导出
```

旧应用仅用于蒸馏 Book Contract、卷规划、章节义务、读者体验、最小上下文、质量循环、连续性与恢复规则。不复制 TypeScript Runtime、Prompt 原文、数据库 Schema、HTTP 服务或任务队列。

## 公共接口

统一入口为 `python scripts/novelctl.py <command>`：

- `init`：创建 schema v3 工作区。
- `migrate`：备份后显式升级 v1/v2 状态。
- `status`、`next`、`validate`、`reconcile`：查看、恢复、校验和处理用户编辑影响。
- `start-step`、`finish-step`、`block-step`、`approve`：执行安全的步骤状态转换。
- `context`、`checkpoint`：复用连续性存储。
- `usage`、`export`：复用 Token 账本和正文导出。

`novel-state.yaml` schema v3 增加最小 `director` 投影、唯一 `next_action`、产物依赖、内容指纹和里程碑审批状态。v1/v2 可只读；迁移必须显式执行并创建备份。

## 生成主链

`novel_brief -> story_bible -> world_and_cast -> volume_strategy -> volume_skeleton -> beat_sheet -> chapter_plan -> context_package -> chapter_draft -> humanization_revision -> chapter_review -> chapter_repair -> continuity_update`

书级简报、故事发动机、卷战略和高风险重规划需要里程碑批准；用户可明确把批准权委托给 AI。章节范围获批后仍保持单 Agent 串行生产。局部修复最多一次，必要时最多升级一次整章修复。

## 开发阶段

1. 保护当前 Token 改动并建立功能分支。
2. 固化 Codex-only、生成合同、自动导演、恢复和旧应用蒸馏边界。
3. 实现工作区模板、schema v3 和 `novelctl`。
4. 更新主 Skill、README、元数据、发布说明和镜像校验。
5. 增加单元、集成、兼容、文档和前向测试；分阶段提交，不自动推送或发布。

跨书资产、章节生产接入、共享宇宙编年史与影响审查的当前进度及后续路线，见 [跨书知识图谱开发看板](cross-book-knowledge-graph-roadmap.md)。

## 验收

- Python 3.10/3.12 编译和全部测试通过。
- v1/v2 兼容读取、备份迁移、迁移失败恢复通过。
- `next` 正确处理 missing、stale、blocked、in-progress 和审批。
- 完成步骤严格遵循“产物验证 -> Token 记录 -> 原子状态更新”。
- 用户修改正文时不覆盖正文，并使依赖的审查、差分、上下文和恢复信息失效。
- SQLite 缺失时回退 YAML；质量债不触发重规划；导出只包含稳定正文。
- Skill quick validation 和安装镜像哈希检查通过。
