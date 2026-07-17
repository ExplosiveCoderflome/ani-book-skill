# 结构化连续性存储

在工作区已经存在 `continuity/data/`，或用户要求长期续写、迁移 YAML 连续性、SQLite 检索或恢复检查点时读取本页。

## 权威边界

- `continuity/data/*.yaml` 是唯一连续性事实来源；只由章节验收后的主代理更新。
- `continuity/index.sqlite3`、`continuity/*.md` 与章节上下文包均为派生物。不得从 SQLite 或 Markdown 反写事实。
- 角色档案、`world-bible.md` 与已验收正文仍分别拥有其原有的事实边界；结构化存储只收录跨章动态状态、事实、伏笔、资源和关系约束。

## 数据与命令

- `manifest.yaml`：版本、修订号、最后验收章节和检查点策略。
- `baseline.yaml`、`facts.yaml`、`payoffs.yaml`、`resources.yaml`、`character-state.yaml`、`relationships.yaml`：各自以稳定 ID、章节来源、证据和状态保存数据。
- 运行 `python scripts/continuity_store.py migrate <workspace> --dry-run` 预检旧 Markdown 工作区；确认后去掉 `--dry-run` 执行迁移。
- 运行 `validate` 验证 YAML；运行 `render-views` 重建只读 Markdown；运行 `build-index` 重建 SQLite；运行 `assemble-context --chapter N --max-chars 9000` 组装有限上下文。

## 定稿与恢复

1. 仅在正文 `accepted` 或安全的 `continue_with_warning` 后更新 YAML。
2. 验证 YAML，再重建 Markdown 视图和 SQLite 索引；最后更新恢复记录和状态。
3. SQLite 缺失、锁定或修订过期时，直接从 YAML 组装上下文并标记索引 stale；不得阻塞正文恢复或篡改 YAML。
4. 每十章或卷末创建一次 YAML checkpoint。迁移首个检查点以最后验收章节作为恢复锚点。

旧版工作区可继续使用 Markdown 台账；不要在未迁移工作区凭空创建部分 YAML 文件。
