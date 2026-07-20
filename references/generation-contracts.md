# 生成步骤合同

## 目录

- 总体规则
- 步骤目录
- 章节循环
- 状态与失败
- Token 边界

## 总体规则

Codex 是唯一生成与创作判断引擎。每个生成步骤必须消费权威上游、产出一个有界工件、执行验收、记录本次模型调用，然后才能把工件标为可用。确定性脚本不得代写创意内容，也不得通过关键词规则替代语义判断。

使用以下稳定状态：`missing`、`in_progress`、`ready`、`stale`、`blocked`。用户编辑和已验收正文优先于状态投影；不得为了恢复状态覆盖内容。

## 步骤目录

| 步骤 ID | 必需上游 | 默认产物 | 核心验收 | 失败处理 |
| --- | --- | --- | --- | --- |
| `novel_brief` | 已确认或已委托的首轮选择 | `novel-brief.md` | 阅读承诺、故事发动机和关键确认状态明确 | 等待里程碑批准 |
| `story_bible` | 已批准简报 | `story-bible.md` | 长期对立、成长、揭示和结局方向可执行 | 回到简报冲突点 |
| `world_and_cast` | 简报、故事圣经 | `world-bible.md`、`characters/` | 世界硬规则和活跃角色硬事实可引用 | 缩小范围或补硬约束 |
| `volume_strategy` | 书级资产 | `volumes/volume-strategy.md` | 每卷职责、阶段回报和升级关系明确 | 等待卷级批准 |
| `volume_skeleton` | 已批准卷战略 | `volumes/volume-XX.md` | 当前卷关键节点和边界可执行 | 只重做当前卷 |
| `beat_sheet` | 当前卷骨架 | `volumes/volume-XX-beat-sheet.md` | 当前窗口节奏与回报分布明确 | 缩短规划窗口 |
| `chapter_plan` | 当前窗口、上一稳定章 | `chapters/chapter-XXX/plan.md` | 章节义务和读者体验合同完整 | 补计划，不写正文 |
| `context_package` | 章节计划、权威事实 | `chapters/chapter-XXX/context-package.md` | 必需来源、裁剪项和缺口可解释 | 缺硬约束时阻断 |
| `chapter_draft` | 计划、上下文包 | `draft.md` | 有可读正文并完成主要义务 | 无可用正文时阻断 |
| `humanization_revision` | 完整初稿 | `draft-humanized.md` | 保留事实与合同，减少成簇模板感 | 保留初稿并记录风险 |
| `chapter_review` | 最终正文候选、同一章节合同 | `review.md` | 给出结构化判定与证据 | 审查不可用记系统风险 |
| `chapter_repair` | review、保护清单 | 修订正文、更新 review | 局部一次、整章最多一次 | 可读则质量债，否则阻断 |
| `continuity_update` | 稳定正文、accepted 或安全 warning | delta、YAML/台账、recovery | 只提交已发生事实 | 失败时保持正文稳定、状态未提交 |

## 章节循环

用户批准一个章节范围后，对每章严格执行：

`计划 -> 最小上下文 -> 整章初稿 -> 一次人性化 -> 审查 -> 必要修复 -> 连续性提交`

当前章没有成为稳定事实源前，不得规划下一章、创建候选正文或让子代理预热。每十章或卷末创建检查点。

通过 `novelctl finish-step` 完成 `chapter_review` 时，必须记录 `--review-decision accepted`、`repair_required` 或 `stop_for_replan`。`accepted` 直接进入连续性提交；`repair_required` 先进入修复；`stop_for_replan` 是结构性阻断。修复步骤默认第一次为局部修复、第二次为整章修复，超过两次不得继续重写，应记录质量债或进入明确重规划。

## 状态与失败

- `continue_with_warning` 产生稳定连续性，同时新增质量债。
- `local_patch_plan` 只允许一次局部修复。
- 局部修复不可行时最多升级一次 `rewrite_needed`。
- 只有 `stop_for_replan`、缺失硬约束、无可用正文、保护资产冲突或状态完整性错误停止全局链。
- 里程碑等待批准时，产物可以存在，但下游不得启动。

## Token 边界

每次真实模型调用独立记录。Codex未暴露 usage 时使用 `unavailable` 和 `runtime_usage_not_exposed`；不得用字符数伪造 Token。索引、校验、文件复制、状态迁移和导出不记 Token。
