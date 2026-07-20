# 跨书资产图谱（第一期）

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
