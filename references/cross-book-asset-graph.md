# 跨书资产图谱（第一至三期）

在用户要求复用题材机制、共享 IP 设定、跨书角色或世界正史时读取本页。它只适用于已经迁移为 `novel-state.yaml` schema v3 的小说工作区。

## Codex 原生边界

- **Codex 是唯一的创作理解、规划、生成、审校与判断引擎。** `SKILL.md` 是过程合同；Python 命令只处理确定性状态、校验、索引、冲突检测和导出。
- 本项目不是 `AI-Novel-Writing-Assistant` 的运行时或子模块。不得接入模型 Provider SDK、Web API、队列、数据库权威源或自研 Agent Runtime。
- `provider`、`model` 等字段仅在 Codex 宿主实际提供用量数据时用于 Token 诊断；它们从不构成生成依赖。

## 私有资产库与权威源

默认库根目录为仓库内被 Git 忽略的 `libraries/`，只供本机使用；共享或发布必须由作者显式导出。先运行：

```powershell
python scripts/asset_graph.py init libraries
```

库包含两个命名空间：

- `reusable`：题材机制、角色原型、世界模板、写法约束和研究机制卡等可复用资产。
- `universe`：共享 IP 的角色、势力、世界规则、道具、事件与正史关系。

每份 `assets/<stable-id>.yaml` 必须有稳定 ID、命名空间、类型、版本、状态、内容、内容指纹、治理模式、可见范围及来源工作区/章节/工件/证据。来源必须明确标记为 `accepted: true`。计划、猜测、未验收正文和无证据关系不得发布为事实资产。

`asset_graph.py publish` 会验证候选、计算内容指纹并写入资产库。共享正史默认 `author_approval`，发布时需要 `--author-approved`；作者可对指定资产执行 `delegate <id> --enabled`，将其改为可由 Codex 定稿发布的 `codex_delegated`。再次执行 `delegate <id>` 即撤销该委托。

## 导入、同步与冲突保护

```powershell
python scripts/asset_graph.py import libraries novels/<book> <asset-id> --mode fork
python scripts/asset_graph.py import libraries novels/<book> <asset-id> --mode sync
python scripts/asset_graph.py reconcile libraries novels/<book>
```

导入会在 `continuity/data/asset-links.yaml` 写入资产 ID、导入模式、库版本与哈希、本书快照哈希和链接状态，同时保留 `cross-book-assets/<asset-id>.yaml` 本书快照。

- `fork`：本书获得独立资产，保留来源记录，之后不会自动影响其他小说。
- `sync`：保留对库版本的链接。库有新版本时只标记 `update_available`；本书快照被改动、缺失或事实冲突时标记 `conflict`。两种情况都不会覆盖正文、YAML 权威资料或本书快照。
- 冲突必须显式处理：`resolve ... --action keep-local` 将本书保留版本转为分叉；`adopt-shared` 明确采用共享版本；`publish-local` 仅在作者批准或该资产仍被委托给 Codex 时提交共享正史更新。任何命令都不静默改写受保护正文。

## 派生图谱与上下文

资产库使用 `graph/nodes.jsonl`、`graph/edges.jsonl` 与可重建的 SQLite 索引；单书使用 `continuity/graph/` 下的同名派生物。运行：

```powershell
python scripts/asset_graph.py build libraries
python scripts/asset_graph.py build-workspace libraries novels/<book>
python scripts/asset_graph.py neighbors libraries/graph <node-id> --depth 2
python scripts/asset_graph.py context libraries novels/<book> --assets <id-1,id-2> --max-depth 2 --max-chars 4000
```

节点和边仅从已验收连续性、已批准资产或明确委托的 Codex 定稿资产派生；边必须记录来源、证据、版本、0–1 置信度和状态。JSONL/YAML 是可核验的派生输入，SQLite 仅为可丢弃索引；索引缺失或过期时可以重建，不得阻塞恢复。

图谱查询只返回有限邻域的**候选**。在安排或写作章节前，Codex 必须回读相应的 YAML/Markdown 权威源，不能把节点或边直接当成事实上下文。`BookGraph` 仍只服务于拆书分析；本图谱只通过作者明确选择的机制卡或资产与其建立来源关系。

## 第二期：章节生产接入

Codex 根据章节计划、已导入资产和图谱候选，显式提出可编辑的选择清单：`context-packages/chapter-XXX.assets.yaml`。每项必须声明资产 ID、用途、约束、导入模式、锁定库版本/哈希和本书快照路径/哈希；图谱邻居只能提示“可考虑导入”，不能越过该清单成为事实。

```powershell
python scripts/asset_graph.py validate-selection libraries novels/<book> novels/<book>/context-packages/chapter-001.assets.yaml
python scripts/novelctl.py context novels/<book> --chapter 1 --asset-library libraries --asset-selection context-packages/chapter-001.assets.yaml --output context-packages/chapter-001.md
```

`novelctl context` 总预算不变，其中跨书资产最多占 35%、且不超过 2500 字符。选中的 `sync` 链接出现 `conflict` 时，`context_package`、正文和审校不能开始；`update_available` 则继续固定使用本书快照，并在上下文中报告待处理更新。未选资产的冲突只在 `novelctl status` 的跨书资产统计中可见，不阻断章节。

章节正文已验收并提交连续性后，Codex 可在 `production/asset-candidates/chapter-XXX/` 创建候选 YAML。候选来源须带 `continuity_committed: true`、章节、工件相对路径、当前 SHA-256 与证据；先验证，再按既有治理发布：

```powershell
python scripts/asset_graph.py verify-candidate novels/<book> novels/<book>/production/asset-candidates/chapter-001/<asset-id>.yaml
python scripts/asset_graph.py publish libraries novels/<book>/production/asset-candidates/chapter-001/<asset-id>.yaml --source-workspace novels/<book> --author-approved
```

候选在通过 `publish` 前不进入资产图、不影响其他小说。共享正史仍需作者批准，除非该资产已有未撤销的 Codex 委托。

## 第三期：单宇宙编年史、影响审查与正史治理

一个私有资产库默认对应一个共享 IP 宇宙：新库在 `library.yaml` 写入 `universe_id: <library_id>` 与 `universe_governance: author_approval`；旧库读取时自动以 `library_id` 作为宇宙 ID。作者可以显式启用或撤销 IP 级 Codex 委托：

```powershell
python scripts/asset_graph.py delegate-universe libraries --enabled
python scripts/asset_graph.py delegate-universe libraries
```

`universe` 命名空间的发布许可满足以下任一项即可：作者使用 `--author-approved`、该资产的 `governance: codex_delegated`，或未撤销的 `universe_governance: codex_delegated`。这项宇宙级委托不会改变 `reusable` 资产的按资产治理。

已发布的 `universe` / `event` 资产才是正史事件源，且 `content.canon` 必须包含稳定整数 `sequence`、非空 `participants`（已发布且活跃的同库宇宙资产 ID）和非空 `effects`；可选 `precedes` / `follows` 只能指向已发布的同库正史事件。事件来源仍必须绑定已验收正文、已提交连续性和证据指纹。脚本不会从正文推断事件、因果或影响。

```powershell
# 先对候选做结构、端点、顺序与循环审查，再显式发布
python scripts/asset_graph.py canon-check libraries
python scripts/asset_graph.py timeline libraries
python scripts/asset_graph.py impact libraries <event-or-asset-candidate.yaml> --workspace novels/<book-a> --workspace novels/<book-b>
python scripts/asset_graph.py publish libraries <event-or-asset-candidate.yaml> --author-approved
```

`timeline` 以 `(sequence, event_id)` 稳定排序，同序事件可并列。`canon-check` 检查失效端点、非宇宙引用、缺证据、顺序倒置与事件环。`impact` 只检查命令中明确传入的 schema-v3 工作区，报告受影响的 `sync` 链接、章节资产选择和直接时间线邻域；它返回 `writes: false`，绝不改写正文、本书快照、选择清单、链接或库资产。待审正史影响在章节上下文中只是“需审查”风险；它不会自动升级快照或阻断生产，只有既有的选中 `sync/conflict` 规则继续阻断。

编年史和影响报告从 YAML/JSONL 权威输入派生；SQLite 仍只是可随时重建的索引。通过审查不等于发布：Codex 提出事件、因果和影响结论，作者或有效的可撤销委托再通过既有 `publish` 进行显式正史提交，且不会批量覆盖任何其他小说的本地快照。
