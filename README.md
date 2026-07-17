# Ani Book Skill

[English](README.en.md) · [更新记录](docs/releases/release-notes.md) · [贡献指南](CONTRIBUTING.md) · [安全政策](SECURITY.md)

`Ani Book Skill` 是一个面向 Codex 的长篇中文网文生产、热门题材分析与拆书工作流。它将榜单研究、参考小说分析、灵感、设定、卷纲、章节、审校和连续性管理拆成可编辑、可恢复的工件，帮助作者以小步、可追溯的方式研究方向并完成长篇创作。

> 这是一个创作工作流 Skill，不是小说托管平台，也不会替代作者的创作判断。

## 来源与项目关系

本项目由原项目 [AI-Novel-Writing-Assistant](https://github.com/ExplosiveCoderflome/AI-Novel-Writing-Assistant) 的维护者，基于其长篇小说生产链路、创作方法论与实践经验蒸馏而成。它将其中可复用的创作流程收敛为可在 Codex 中运行的轻量、文档优先 Skill。

- 本仓库是独立的 Skill，不是原项目的镜像或运行时发行版；不包含原项目的前端、后端、数据库、Agent 服务或桌面端代码。
- 本仓库仅对自身包含的文件采用 [Apache License 2.0](LICENSE)；原项目的许可证与商业授权政策请以其仓库为准。
- 提到原项目仅用于说明来源与致谢，不代表本 Skill 与原项目的任何版本存在运行时依赖关系。

## 能做什么

- 从创意逐步推进到小说简介、故事圣经、世界观、人物与分卷规划。
- 用渐进式确认引导新手做设定选择：每轮只处理 2–3 个高影响问题，提供推荐及影响说明，并记住已确认、交给 AI 或明确跳过的决定。
- 按需分析公开官方榜单的标题、标签和简介，生成当前榜单构成、可比日期差值与 3–5 张选题机会卡，不读取小说正文。
- 对已授权的本地文本、可访问线上小说或自己的稿件进行分层拆书，输出证据化结论、覆盖地图和可迁移机制卡。
- 使用轻量 BookGraph、SQLite 中文全文检索和可选向量融合查询长篇 notes，无需捆绑本地 embedding 模型或向量数据库。
- 以章节契约、上下文包和连续性台账管理长篇一致性。
- 对完整章节执行人性化修订、审校与定向修复，同时保护已确认事实。
- 通过内置脚本导出已生成章节为 TXT，或检查工作区连续性资产。
- 用本地 Markdown 和 YAML 保存内容，便于版本控制、审阅与迁移。

## 安装

将本仓库作为个人 Codex Skill 安装，或将其内容复制到你的 Skill 目录。安装后，在 Codex 中直接调用：

```text
使用 $produce-long-form-novel 帮我从一个灵感开始规划长篇小说。
```

当需求还比较模糊时，Skill 不会一次要求填写完整设定表，而会先提供类似这样的少量选择：

```text
1. 读者频道：男频 / 女频 / 泛读者 / 由 AI 推荐
2. 平台形态：付费连载 / 免费连载 / 暂不限定
3. 主要回报：升级成长 / 关系情绪 / 悬疑揭秘 / 自定义
```

每项都会附带一个推荐方向和影响说明。你可以逐项选择，也可以说“全部接受”“这些由你决定”或“这项不重要”。这些决定会在当前小说项目中持续生效，除非你主动修改。

也可以从已有工作区继续：

```text
使用 $produce-long-form-novel 继续 novels/<小说名>/，先判断下一步该做什么。
```

或拆解有权使用的参考小说：

```text
使用 $produce-long-form-novel 拆解这份小说文本，先建立覆盖范围、分段笔记和快速总览。
```

或研究某个频道的热门题材：

```text
使用 $produce-long-form-novel 分析近期男频玄幻榜单的题材构成，并生成机会卡。
```

Skill 的入口和完整行为约定见 [SKILL.md](SKILL.md)。

## 工作流

```text
灵感 → 小说简介 → 故事圣经 → 世界与人物 → 分卷策略 → 卷纲
  → 章节计划 → 上下文包 → 初稿 → 人性化修订 → 审校/修复 → 连续性更新

授权来源 → 范围与指纹 → 分段笔记 → 总览 → 专项拆解
  → 证据/反例 → 机制卡 → 原创规划或稿件修复

平台/频道/时间范围 → 公开榜单 → 元数据快照 → 表层信号
  → 榜单构成/可比差值 → 趋势报告 → 3–5 张机会卡
```

每一步都会生成可编辑工件，并尽量只读取完成当前步骤所需的上下文。未确认的 AI 推荐只能用于局部预览；确认或授权 AI 决定后才会进入正式规划。已确认的作者决定与正文默认受到保护，不会被悄然重写。

## 仓库结构

```text
SKILL.md       # Skill 入口与行为约定
agents/        # Codex 展示与调用配置
references/    # 规划、写作、审校和连续性参考规范
scripts/       # 导出、连续性检查、拆书检索与榜单快照工具
novels/        # 本地小说工作区（默认不提交到公开仓库）
analyses/      # 私有拆书工作区（默认不提交到公开仓库）
trends/        # 私有榜单趋势工作区（默认不提交到公开仓库）
```

`novels/`、`analyses/` 与 `trends/` 设计为私有工作区，已被 `.gitignore` 排除。若要公开范例，请在 `examples/` 中添加经过授权、已脱敏的最小示例，而不是提交真实稿件、来源文本或榜单研究快照。

## 命令行工具

需要 Python 3.10 或更高版本。安装 YAML 连续性存储所需依赖：

```powershell
python -m pip install -r requirements.txt
```

导出已完成章节（默认优先使用 `draft-humanized.md`）：

```powershell
python scripts/export_novel_txt.py novels/<小说名>
```

在指定范围或来源导出前，可先预览：

```powershell
python scripts/export_novel_txt.py novels/<小说名> --start 1 --end 10 --source humanized --dry-run
```

检查连续性资产与来源指纹：

```powershell
python scripts/check_continuity_workspace.py novels/<小说名>
```

对于已经进入长篇续写阶段的工作区，可将连续性事实迁移为 YAML 权威数据，并从中重建本地 SQLite 索引：

```bash
python scripts/continuity_store.py migrate novels/<小说名> --dry-run
python scripts/continuity_store.py migrate novels/<小说名>
python scripts/continuity_store.py validate novels/<小说名>
```

迁移后，`continuity/data/*.yaml` 是唯一权威；`continuity/*.md` 是可读生成视图，`continuity/index.sqlite3` 可删除并重建。

为长篇拆书工作区建立 BookGraph 与本地检索索引：

```powershell
python scripts/analysis_retrieval.py build analyses/<名称>
python scripts/analysis_retrieval.py search analyses/<名称> "升级循环" --dimension progression
python scripts/analysis_retrieval.py nodes analyses/<名称> "林越"
python scripts/analysis_retrieval.py trace analyses/<名称> EVENT-001 PAYOFF-003
```

默认使用 SQLite 全文、元数据和图关系检索；只有提供兼容 embeddings 与查询向量时才启用向量融合。

校验、聚合或比较榜单元数据快照：

```powershell
python scripts/trend_snapshot.py validate trends/<范围>/snapshots/2026-07-17/<platform>-<chart>.jsonl
python scripts/trend_snapshot.py summarize <snapshot.jsonl> --format markdown
python scripts/trend_snapshot.py compare <older.jsonl> <newer.jsonl> --format json
```

趋势脚本只做事实统计与差值，不内置爬虫、题材词典、RAG 或趋势结论。单快照只能描述当前榜单构成。

## 开发与验证

```powershell
python -m compileall scripts
python scripts/export_novel_txt.py --help
python scripts/check_continuity_workspace.py --help
python scripts/continuity_store.py --help
python scripts/analysis_retrieval.py --help
python scripts/trend_snapshot.py --help
python -m unittest discover -s tests -v
```

提交前请确认 Markdown 说明与实际工作流一致，并避免提交未授权的小说正文、个人信息或 API 密钥。

## 最新更新

### 2026-07-17

- 新增证据可追溯的参考小说拆解与稿件诊断工作流，并提供轻量 BookGraph、SQLite 中文全文检索和可选向量融合，支持按关系路径和必要证据查询长篇分析资料。
- 新增独立的热门题材榜单分析路线：保存元数据快照、聚合表层信号、比较同榜可比日期并生成机会卡；趋势资产默认不提交，也不会混入小说创作上下文。
- 新增贯穿开书、故事发动机、世界角色、卷规划与首章前的渐进确认机制；每轮最多确认 3 项，并避免重复询问已明确、已授权 AI 决定或不适用的设置。
- 连续性存储升级为 YAML 权威数据、只读 Markdown 台账视图和可重建 SQLite 索引；支持有限上下文组装、恢复检查点和旧工作区安全迁移。
- 章节生产保持单章串行回灌，暂停多子代理预热，避免未验收候选污染长期事实。

完整历史见 [更新记录](docs/releases/release-notes.md)。

## 参与贡献

欢迎改进工作流、补充测试、修正文档或提交经过授权的脱敏示例。提交前请阅读 [贡献指南](CONTRIBUTING.md) 与 [行为准则](CODE_OF_CONDUCT.md)。

## 许可

本项目采用 [Apache License 2.0](LICENSE)。贡献即表示你同意按相同许可发布贡献内容。
