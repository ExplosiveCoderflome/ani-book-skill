# Ani Book Skill

[![Validate](https://github.com/ExplosiveCoderflome/ani-book-skill/actions/workflows/validate.yml/badge.svg)](https://github.com/ExplosiveCoderflome/ani-book-skill/actions/workflows/validate.yml)
[English](README.en.md) · [更新记录](docs/releases/release-notes.md) · [贡献指南](CONTRIBUTING.md) · [安全政策](SECURITY.md)

> 把“我想写一部长篇”变成一条能持续跑下去的创作生产线。

**Ani Book Skill** 是面向 Codex 的长篇中文小说工作流。它不只替你补一段正文，而是把选题判断、故事发动机、章节推进、审校修复和长期连续性连接成一套可恢复、可追溯、始终由作者掌控的本地流程。

从一个模糊灵感开始，到几十章以后仍知道人物此刻知道什么、伏笔该在哪里兑现、这一章为什么值得读——这正是它要解决的问题。

![Ani Book Skill 工作流：灵感与选题、故事架构、正文审查、连续性存储构成一个可持续循环](assets/workflow-hero.png)

*从创意火花到下一章：每次回灌都让小说更完整，而不是让上下文更失控。*

## 你会得到什么

| 你正在面对的问题 | Ani Book Skill 的做法 | 最终留下什么 |
| --- | --- | --- |
| “这个题材现在还有没有机会？” | 分析公开榜单的标题、标签与简介，只给基于元数据的方向判断 | 榜单快照、趋势报告、机会卡 |
| “我有设定，但不知道第一卷怎么拉住人。” | 用渐进确认锁定读者回报，再建立故事发动机、卷级承诺和章节职责 | 可编辑的简介、世界观、角色、卷纲与节奏板 |
| “章节能写，但越写越散。” | 每章固定经过计划 → 上下文 → 完整正文 → 人性化二稿 → 审查 → 回灌 | 正文、审查、差分与唯一下一步 |
| “写到五十章后，上下文会不会爆？” | YAML 保存权威事实，SQLite 只做可重建检索；按当前章筛选有限上下文 | 可恢复的连续性状态、检查点与只读台账视图 |

## 它和普通提示词有什么不同？

- **先锁定读者期待，再扩写世界。** 模糊需求不会被一次性问卷淹没；每轮只处理 2–3 个真正影响后续的选择。
- **一章一章地稳定推进。** 不拼接多个片段，也不让未验收的后续候选污染故事事实。
- **把长期记忆当成工程问题处理。** 事实、资源、伏笔、角色动态和关系约束都有稳定 ID、来源章节与恢复路径。
- **内容留在你的本地工作区。** 小说、拆书来源和趋势快照默认不提交到公开仓库；你可以审阅、修改、迁移和备份所有工件。

## 三种开始方式

### 从一个灵感开始

```text
使用 $produce-long-form-novel 帮我从一个灵感开始规划长篇小说。
```

它会先帮你确定读者频道、连载形态和主要阅读回报，而不是立刻抛出一份不可控的万字大纲。

### 把已有小说继续写下去

```text
使用 $produce-long-form-novel 继续 novels/<小说名>/，先判断上一章稳定后下一步该做什么。
```

它会读取必要的恢复记录、上章承接、参与角色和活跃伏笔，只装配当前章真正需要的上下文。

### 找方向或拆解已授权作品

```text
使用 $produce-long-form-novel 分析近期男频玄幻榜单的题材构成，并生成机会卡。
```

```text
使用 $produce-long-form-novel 拆解这份有权使用的小说文本，先建立覆盖范围、分段笔记和快速总览。
```

## 一部小说如何在这里持续生长

```text
选题/灵感
  → 阅读承诺与故事发动机
  → 世界、角色与卷级回报
  → 当前章节合同与最小上下文
  → 完整正文与人性化修订
  → 审查、连续性回灌、恢复检查点
  → 下一章
```

每个箭头都留下可编辑工件。作者修改正文时，依赖产物会被标记为 stale，而不是悄悄用旧设定覆盖新创作。

## 为长篇而设计的连续性

当小说进入长期续写阶段，可将连续性迁移为：

```text
YAML 权威事实
   ├── 事实 / 伏笔 / 资源 / 角色动态 / 关系约束
   ├── 每 10 章或卷末检查点
   └── Markdown 可读台账视图

SQLite 可重建索引
   └── 只负责检索和上下文候选；丢失或过期时直接回退 YAML
```

这意味着章节越多，并不需要把整本书塞进模型上下文；索引也永远不能反向修改你的故事事实。

## 安装与本地工具

将本仓库安装为个人 Codex Skill 后，直接在 Codex 中使用 `$produce-long-form-novel`。完整行为契约见 [SKILL.md](SKILL.md)。

需要 Python 3.10+；使用 YAML 连续性存储前安装依赖：

```powershell
python -m pip install -r requirements.txt
```

```powershell
# 导出已完成章节
python scripts/export_novel_txt.py novels/<小说名>

# 校验连续性来源与状态
python scripts/check_continuity_workspace.py novels/<小说名>

# 将旧 Markdown 台账安全迁移为 YAML 权威数据
python scripts/continuity_store.py migrate novels/<小说名> --dry-run
python scripts/continuity_store.py migrate novels/<小说名>

# 为已授权参考作品建立本地检索
python scripts/analysis_retrieval.py build analyses/<名称>

# 校验和比较榜单元数据快照
python scripts/trend_snapshot.py validate trends/<范围>/snapshots/<日期>/<platform>-<chart>.jsonl
```

`novels/`、`analyses/` 和 `trends/` 默认被忽略，避免把真实小说、来源文本或研究快照误推送到公开仓库。

## 清晰的边界

- 榜单路线只处理公开元数据，不读取小说正文，也不伪造“趋势必然上涨”的结论。
- 拆书只处理你有权使用的文本，输出可迁移的机制，不提供贴近原作的仿写。
- 这不是小说托管平台，也不会替代作者对作品、隐私和发布的最终判断。

## 来源与许可

本项目由 [AI-Novel-Writing-Assistant](https://github.com/ExplosiveCoderflome/AI-Novel-Writing-Assistant) 的维护者，基于其中的长篇生产经验蒸馏而成；它是独立、文档优先的 Codex Skill，不包含原项目的前后端、数据库或运行时服务，也不存在运行时依赖。

本仓库文件采用 [Apache License 2.0](LICENSE)。欢迎提交经过授权、脱敏的示例、测试和工作流改进；提交前请阅读 [贡献指南](CONTRIBUTING.md) 与 [行为准则](CODE_OF_CONDUCT.md)。

最新变化请见 [更新记录](docs/releases/release-notes.md)。

## 最新更新

### 2026-07-18

- 新增工作流宣传图，以可视化方式呈现选题、故事架构、章节审查和长期连续性之间的闭环。

完整历史见 [更新记录](docs/releases/release-notes.md)。
