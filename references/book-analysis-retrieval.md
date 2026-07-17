# BookGraph 与轻量混合检索

## 目录

- 目标与边界
- 权威资产与派生缓存
- Notes 检索元数据
- BookGraph 合同
- 建立本地索引
- 查询顺序
- 可选向量合同
- 上下文包规则
- 失效与恢复

## 目标与边界

长篇拆书使用 `BookGraph + 元数据过滤 + SQLite 全文检索 + 可选向量`。默认路径不得依赖 embedding 模型、FAISS、外部向量数据库或第三方 Python 包。

BookGraph 负责回答明确关系问题，例如人物怎样参与事件、事件怎样引出承诺、伏笔怎样走到兑现、规则怎样限制行动。全文检索负责专名、事件、原句证据和明确字段。向量只在运行环境已经能生成兼容 embedding 时补充语义相似召回。

首次完整分析仍需分段读取一次来源。检索层主要减少专项小节、追问、重跑、续写引用和增量更新时的重复输入。

## 权威资产与派生缓存

权威资产：

- `analysis-state.yaml`、来源范围与指纹；
- `notes/*.md` 与分析小节；
- `evidence-ledger.md`、`uncertainty-ledger.md`、`pattern-cards.md`；
- `graph/nodes.jsonl` 与 `graph/edges.jsonl`；
- 用户编辑且受保护的 Markdown/YAML。

派生缓存：

- `retrieval/analysis-index.sqlite3`；
- `retrieval/embeddings.jsonl`；
- 临时查询向量。

派生缓存可随时删除和重建，不得成为唯一事实源。索引构建不修改权威产物。

## Notes 检索元数据

在需要过滤的 Markdown 顶部加入一条可选机器注释：

```html
<!-- retrieval-meta: {"chapter_start":1,"chapter_end":10,"dimensions":["progression","cliffhanger"],"characters":["林越"]} -->
```

支持字段：

- `chapter_start`、`chapter_end`：1-based 章节范围；
- `dimensions`：分析维度，例如 `plot`、`progression`、`character`、`worldbuilding`、`style`、`market`、`cliffhanger`；
- `characters`：该 note 直接涉及的角色稳定名称。

注释只用于检索过滤，不代替正文中的来源范围、证据和不确定性记录。没有注释时，脚本会尝试从路径、标题和章节写法推断范围。

## BookGraph 合同

建议节点类型：

- `chapter`、`scene`、`character`、`event`、`location`；
- `faction`、`item`、`resource`、`world_rule`；
- `promise`、`payoff`、`conflict`、`state_snapshot`、`pattern`。

建议关系：

- `appears_in`、`participates_in`、`causes`、`blocks`、`enables`；
- `knows`、`owns`、`belongs_to`、`located_in`、`before`；
- `changes_state`、`opens`、`foreshadows`、`pays_off`、`contradicts`。

`graph/nodes.jsonl` 每行一个节点：

```json
{"id":"CHAR-001","type":"character","label":"林越","aliases":["阿越"],"attributes":{"role":"protagonist"},"confidence":"high","source_refs":["segment-001"]}
```

`graph/edges.jsonl` 每行一条有向关系：

```json
{"id":"EDGE-001","source":"EVENT-001","relation":"opens","target":"PROMISE-001","confidence":"medium","evidence":["CLAIM-012"],"attributes":{"scope":"第8章"}}
```

节点和边必须使用稳定 ID。关系端点必须存在。推断边降低置信度并绑定证据；开放假设不要写成确定边，可先保留在 `uncertainty-ledger.md`。

## 建立本地索引

脚本只依赖 Python 3.10+ 标准库：

```powershell
python scripts/analysis_retrieval.py build analyses/<名称>
python scripts/analysis_retrieval.py status analyses/<名称>
```

默认索引以下内容：

- `notes/**/*.md`、`sections/**/*.md`；
- 来源与覆盖清单；
- 证据、不确定性和机制卡；
- BookGraph 节点与边。

Markdown 按标题和长度切为稳定 chunk。脚本为中文建立二元/三元检索词，保存章节、维度和人物元数据，并验证图关系端点。

## 查询顺序

不要对每个问题都直接做向量搜索。按问题选择最窄路径：

1. 先带上 `source-manifest.md`、`coverage-map.md` 和总览中的必要全局锚点。
2. 明确人物、章节、事件或技法名称时，先做元数据过滤和全文检索。
3. 询问因果、关系、伏笔、知情边界或状态传播时，先查询 BookGraph。
4. 只有用户使用抽象描述、近义表达或明确要找相似模式时，才补向量召回。
5. 命中一个局部 chunk 后，按需要补充相邻 chunk 或前后章节。
6. 回到权威 Markdown 和证据锚点核实，不把检索排名当作事实。

全文与元数据查询：

```powershell
python scripts/analysis_retrieval.py search analyses/<名称> "升级循环" --dimension progression --limit 8
python scripts/analysis_retrieval.py search analyses/<名称> "身份揭示" --character 林越 --chapter 36 --format json
```

图邻域与路径：

```powershell
python scripts/analysis_retrieval.py nodes analyses/<名称> "林越"
python scripts/analysis_retrieval.py neighbors analyses/<名称> CHAR-001 --depth 2
python scripts/analysis_retrieval.py trace analyses/<名称> EVENT-001 PAYOFF-003 --max-depth 6
```

## 可选向量合同

Skill 不负责下载模型或调用固定 embedding 厂商。运行环境如能生成 embedding，可将 chunk 向量写入 `retrieval/embeddings.jsonl`：

```json
{"chunk_id":"CHUNK-...","model":"<embedding-model-id>","vector":[0.1,0.2]}
```

查询向量文件使用：

```json
{"model":"<embedding-model-id>","vector":[0.1,0.2]}
```

调用：

```powershell
python scripts/analysis_retrieval.py search analyses/<名称> "相似的压迫式升级" --query-vector query-vector.json --vector-weight 0.35
```

脚本校验数值、维度和模型标识，使用余弦相似度与全文结果做排名融合。没有查询向量时自动退回全文与元数据检索。embedding 模型变化后只重建向量 sidecar，不重新生成 notes。

## 上下文包规则

一次专项分析的上下文包只包含：

- 来源、范围和覆盖限制；
- 总览中与任务相关的定位锚点；
- 图路径或关系邻域；
- Top-K notes 和必要相邻片段；
- 对应证据、反例与开放假设；
- 明确省略的材料和可能风险。

不要把全部搜索结果或整本 notes 塞回模型。检索结果只是候选，最终结论仍按 [book-analysis.md](book-analysis.md) 的事实、推断、假设和证据合同生成。

## 失效与恢复

以下情况重建 SQLite 索引：

- notes、分析小节、账本或 graph JSONL 改变；
- chunk 切分参数改变；
- 来源范围或来源指纹改变。

来源变化时先将依赖产物标为 `stale`，重新生成受影响 notes 和图关系，再重建索引。不要用旧索引掩盖来源版本变化。
