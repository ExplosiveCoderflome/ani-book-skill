# 热门题材趋势分析

## 目录

- [适用范围](#适用范围)
- [固定流程](#固定流程)
- [工作区合同](#工作区合同)
- [榜单快照合同](#榜单快照合同)
- [信号提取合同](#信号提取合同)
- [聚合与比较](#聚合与比较)
- [趋势报告](#趋势报告)
- [机会卡](#机会卡)
- [创作上下文隔离](#创作上下文隔离)
- [来源与访问边界](#来源与访问边界)
- [修正与失效传播](#修正与失效传播)

## 适用范围

本路线回答“某平台某频道的榜单当前由哪些题材信号构成”和“两个可比日期之间发生了哪些榜单级变化”。它只处理公开榜单元数据，不读取小说正文，也不启用 BookGraph、RAG、全文索引或向量检索。

以下请求进入本路线：热门拆书、榜单题材、最近热门玄幻、近期流行方向、赛道机会、榜单选题分析。用户要求分析某一本书的角色弧、节奏、伏笔、结构或正文技巧时，停止本路线，明确升级到 [book-analysis.md](book-analysis.md) 的书级拆解流程；不要自动获取正文。

## 固定流程

1. 确定平台、读者频道、榜单和时间范围。用户未指定平台或频道时，先询问目标频道，不自行混合男频、女频或不同受众。
2. 按需读取公开官方榜单。默认每榜前 20 名，单次最多处理 3 个榜单；扩大范围前先取得用户同意。
3. 将原始可见元数据保存为不可变快照，并记录来源 URL、访问日期和限制。
4. 仅从标题、标签和简介提取表层信号，保存证据字段与置信度。
5. 运行 `scripts/trend_snapshot.py validate`，再运行 `summarize` 或对可比日期运行 `compare`。
6. AI 根据结构化事实编写报告。单快照只能称为“当前榜单构成”。
7. 生成 3–5 张机会卡，明确证据窗口、拥挤风险与不可推断项。

网页不可访问时，改用用户提供的截图、表格或文本。先注明哪些字段可见、哪些缺失，再人工规范化为相同 JSONL 合同；不得绕过登录、付费墙、验证码、反爬或站点访问限制。

## 工作区合同

持久化趋势研究只写入独立目录：

```text
trends/<规范化范围>/
├── trend-state.yaml
├── source-manifest.md
├── snapshots/
│   └── YYYY-MM-DD/<platform>-<chart>.jsonl
├── reports/
│   └── YYYY-MM-DD.md
└── opportunity-cards/
    └── OPP-001.md
```

规范化范围应能区分平台、频道和研究主题，例如 `qidian-male-fantasy`。不要把趋势资产写进 `novels/` 或 `analyses/`。

`trend-state.yaml` 保持为小型状态索引：

```yaml
schema_version: 1
scope: qidian-male-fantasy
platforms: [示例平台]
channels: [男频玄幻]
default_chart_limit: 20
snapshot_limit: 3
snapshots:
  - path: snapshots/2026-07-17/example-weekly.jsonl
    status: stable
reports:
  - path: reports/2026-07-17.md
    status: ready
opportunity_cards:
  - path: opportunity-cards/OPP-001.md
    status: ready
next_action: 等待用户选择机会卡或补充下一期快照
```

`source-manifest.md` 至少记录平台、榜单、统计周期、来源 URL、抓取或接收日期、输入形式（网页、截图、表格、文本）、可见字段、缺失字段和访问限制。

## 榜单快照合同

每个 JSONL 文件代表同一平台、同一榜单、同一统计周期和同一快照日期。每行是一部作品，必填字段为：

| 字段 | 规则 |
| --- | --- |
| `platform` | 非空平台名 |
| `chart` | 非空榜单名 |
| `window` | 榜单统计周期，例如 `daily`、`weekly` 或平台原始说明 |
| `captured_at` | `YYYY-MM-DD` 快照日期 |
| `rank` | 从 1 开始的正整数，同一快照内不可重复 |
| `title` | 作品名 |
| `author` | 作者名；来源未展示时先补充缺失说明，不编造 |
| `source_url` | 公开 HTTP(S) 来源 URL；用户材料也记录其对应公开页面（若已知） |
| `access_level` | 固定为 `metadata_only` |

可选字段为 `category`、`tags`、`synopsis`、`status`、`word_count` 和 `updated_at`。同一作品和作者组合不得在同一快照重复。

示例：

```json
{"platform":"示例平台","chart":"男频畅销榜","window":"weekly","captured_at":"2026-07-17","rank":1,"title":"示例书名","author":"示例作者","source_url":"https://example.com/chart","access_level":"metadata_only","tags":["玄幻","升级"],"synopsis":"公开简介。","signals":[{"dimension":"genre","value":"玄幻","confidence":"high","evidence_fields":["tags"]}]}
```

## 信号提取合同

AI 只能从 `title`、`tags` 和 `synopsis` 提取以下维度：

- `genre`：大题材。
- `subgenre`：可被元数据直接支持的细分题材。
- `protagonist_identity`：简介或标题明示的主角身份。
- `core_mechanism`：简介明示的主要能力、规则或重复行动机制。
- `emotional_promise`：元数据承诺的主要情绪回报。
- `hook_pattern`：标题或简介可见的开篇吸引模式。
- `audience_signal`：频道、标签或文案直接表达的受众信号。

每条信号必须包含：

```json
{
  "dimension": "core_mechanism",
  "value": "规则面板升级",
  "confidence": "medium",
  "evidence_fields": ["synopsis"]
}
```

`confidence` 仅允许 `high`、`medium` 或 `low`。`evidence_fields` 只能引用当前记录中确实存在且非空的 `title`、`tags`、`synopsis`。不要硬编码题材词典；信号命名应忠实于当次可见元数据，并在同一研究范围内保持规范化。

元数据不能支持以下判断：全书节奏、人物弧完成度、伏笔兑现、文风质量、中后期表现、结局质量、留存率或实际读者口碑。报告与机会卡必须把这些列入不可推断项。

## 聚合与比较

使用标准库脚本：

```powershell
python scripts/trend_snapshot.py validate trends/<范围>/snapshots/2026-07-17/<platform>-<chart>.jsonl
python scripts/trend_snapshot.py summarize <snapshot.jsonl> --format markdown
python scripts/trend_snapshot.py compare <older.jsonl> <newer.jsonl> --format json
```

`summarize` 按信号统计作品数、平台覆盖、平均名次和排名权重。排名权重固定为：

```text
1 / log2(rank + 1)
```

单个快照只支持“当前榜单构成”描述，不得产生“上升”“下降”“持续热门”或“新晋题材”结论。

`compare` 只接受同平台、同榜单、同统计周期且日期先后明确的两个快照。它输出新增作品、退出作品、名次变化和信号权重变化。脚本的 `rank_change` 为 `旧名次 - 新名次`，正数表示名次向前。脚本只给事实和差值；“持续热门、上升机会、拥挤方向”等解释由 AI 在报告中结合样本限制生成。

跨榜单共性应先分别聚合各榜单，再由 AI 比较信号是否在多个榜单出现。不得直接比较不同平台或不同榜单的名次数值。

## 趋势报告

`reports/YYYY-MM-DD.md` 使用以下结构：

1. 来源与时间范围。
2. 榜单覆盖：平台、频道、榜单、每榜条目数和缺失项。
3. 当前热门信号：事实聚合、代表作品名和证据字段。
4. 跨榜单共性：仅在覆盖两个或以上榜单时填写。
5. 历史变化：仅在存在至少两个可比较日期时填写；否则写“数据不足”。
6. 饱和风险：明确这是基于榜单重复度和组合集中度的假设，不等同于市场供给全貌。
7. 数据限制与不可推断项。

所有趋势性形容词都要绑定比较窗口。低覆盖、字段缺失或仅有一个日期时降低置信度。

## 机会卡

每次报告生成 3–5 张 `opportunity-cards/OPP-NNN.md`，每张包含：

```markdown
# OPP-001：机会方向

- 状态：ready
- 读者承诺：
- 常见组合：
- 拥挤元素：
- 差异化假设：
- 证据窗口：平台 / 榜单 / 日期 / 样本量
- 置信度：high | medium | low
- 不可推断项：全书节奏、人物弧、伏笔兑现、文风和中后期表现
```

机会卡是选题假设，不是成功保证。差异化假设应改变人物身份、约束、目标、情绪回报或机制组合，不复制榜单作品标题、简介表达或具体设定。

## 创作上下文隔离

趋势研究与小说生产默认完全隔离：

- 只有用户明确选中的一张机会卡可以被提炼进 `novel-brief.md`。
- 只迁移用户选中的读者承诺、机会方向和已确认差异化假设。
- 不得把原始榜单、作品简介、全部信号表、其他机会卡或报告全文注入小说上下文。
- 迁移后在 `novel-brief.md` 标注来源机会卡 ID、用户确认日期和允许使用的字段。
- 用户未选择时，停在机会卡，不自动开始写书。

## 来源与访问边界

- 默认只使用公开官方榜单与用户提供资料。
- 来源访问级别始终是 `metadata_only`；即使页面同时展示正文入口，也不进入正文。
- 不抓取盗版来源，不绕过登录、付费墙、验证码、反爬或地区限制。
- 不内置平台爬虫，不依赖站点私有接口，不把页面结构写死在脚本中。
- 页面不可访问时，说明限制并请求截图、表格或文本；不要用非官方转载替代官方榜单而不声明来源差异。
- MVP 为按需查询，不创建定时任务、后台监控或自动历史采集。

## 修正与失效传播

快照一旦被报告引用即视为稳定来源。发现抄录、解析或信号错误时：

1. 不静默覆盖；在 `source-manifest.md` 记录修正原因、时间和受影响文件。
2. 修正对应 JSONL，并重新运行 `validate`。
3. 将引用该快照的报告标记为 `stale`。
4. 将依赖这些报告的机会卡标记为 `stale`。
5. 只重建受影响的报告与机会卡；不改动用户已选择并已进入创作的内容，除非先向用户说明影响并得到授权。
