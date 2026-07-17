# 连续性账本与定稿回灌

在首次续写、章节定稿、恢复任务或连续性审查前读取本页。只在工作区模式使用这些产物。

如果工作区存在 `continuity/data/`，先读取 [structured-continuity-store.md](structured-continuity-store.md)：YAML 是唯一权威，以下 Markdown 账本仅是自动生成的只读视图。旧工作区继续使用本页的 Markdown 合同，直到显式迁移。

## 启用与基线

首次启用时，以最近一章稳定正文建立 `continuity/baseline.md`。基线只汇总当前可确认状态，不生成旧章节的逐章差分。

每份依赖稳定正文的产物都在顶部写入：

```markdown
<!-- source-hash: chapters/chapter-005/draft.md | SHA256_HEX -->
```

正文指纹变化时，保护正文，标记依赖产物 `stale`，再重新核对。

多子代理滚动预热已暂停。当前生产链只接受完成当前章的稳定正文；不得保留或采用任何旧的后续章节候选。当前章回灌后，从新的稳定资产串行规划下一章。

## 文件合同

### `fact-ledger.md`

每项包含：稳定 ID、事实、发生章节、证据位置、涉及角色、状态和后续约束。只收录已发生且会限制后文的事实。

### `payoff-ledger.md`

每项包含：稳定 ID、承诺/伏笔、来源、首次出现章、目标窗口、当前状态、最近推进、兑现证据、风险和下一次可触碰窗口。状态使用 `pending`、`advanced`、`paid_off`、`stale` 或 `retired`。

### `resource-ledger.md`

只记录跨章会影响行动边界的资源。每项包含：稳定 ID、资源、持有人、归属、可见性、当前状态、来源章节、使用窗口、风险和禁止误用。个人短期状态仍回写角色档案。

### `chapter-deltas/chapter-XXX.md`

每章包含：最终正文来源与指纹、审查结果、稳定事实、角色状态/知情变化、资源变化、关系变化、伏笔变化、质量债和已更新文件。它是变更证据，不是新的事实权威。

### `chapters/chapter-XXX/context-package.md`

每章包含：当前任务、已选来源及用途、必需约束、裁剪项、缺失项、风险与构造时间。它是章节装配包；长期角色、世界和连续性事实仍以各自模块为权威。不得复制长正文或完整设定，也不得在此创建独立的事实版本。

### `production/recovery.md`

记录最后稳定章、已提交连续性章、下一步、受保护资产、stale 资产、开放质量债与恢复前必读文件。

### `production/quality-debt.md`

每项包含：ID、来源章节、最终版本、问题与证据、影响、建议回收窗口、状态和是否允许继续。只收录 `continue_with_warning` 或修复预算耗尽但正文仍可读的问题。

## 回灌顺序

1. 仅在 `accepted` 或可继续的 `continue_with_warning` 后开始。
2. 写 chapter delta，先锁定最终正文来源与指纹。
3. 迁移后的工作区更新 YAML 事实、伏笔、资源与动态角色/关系状态，运行校验后重建 Markdown 视图和 SQLite；旧工作区直接更新 Markdown 台账。
4. 有非阻塞问题时写质量债；没有则明确“无新增质量债”。
5. 每十章或卷末生成 YAML checkpoint；更新 recovery 和 state，下一步只能保留一个明确动作。

不要把计划、推测、未验证证词或修复候选写入账本。不要以伏笔逾期、一般文风问题或单章次要缺口自动触发重规划。
