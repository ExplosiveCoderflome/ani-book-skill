# Ani Book Skill

[English](README.en.md) · [更新记录](docs/releases/release-notes.md) · [贡献指南](CONTRIBUTING.md) · [安全政策](SECURITY.md)

`Ani Book Skill` 是一个面向 Codex 的长篇中文网文生产工作流。它将灵感、设定、卷纲、章节、审校和连续性管理拆成可编辑、可恢复的 Markdown 工件，帮助作者以小步、可追溯的方式完成长篇创作。

> 这是一个创作工作流 Skill，不是小说托管平台，也不会替代作者的创作判断。

## 能做什么

- 从创意逐步推进到小说简介、故事圣经、世界观、人物与分卷规划。
- 以章节契约、上下文包和连续性台账管理长篇一致性。
- 对完整章节执行人性化修订、审校与定向修复，同时保护已确认事实。
- 通过内置脚本导出已生成章节为 TXT，或检查工作区连续性资产。
- 用本地 Markdown 和 YAML 保存内容，便于版本控制、审阅与迁移。

## 安装

将本仓库作为个人 Codex Skill 安装，或将其内容复制到你的 Skill 目录。安装后，在 Codex 中直接调用：

```text
使用 $produce-long-form-novel 帮我从一个灵感开始规划长篇小说。
```

也可以从已有工作区继续：

```text
使用 $produce-long-form-novel 继续 novels/<小说名>/，先判断下一步该做什么。
```

Skill 的入口和完整行为约定见 [SKILL.md](SKILL.md)。

## 工作流

```text
灵感 → 小说简介 → 故事圣经 → 世界与人物 → 分卷策略 → 卷纲
  → 章节计划 → 上下文包 → 初稿 → 人性化修订 → 审校/修复 → 连续性更新
```

每一步都会生成可编辑工件，并尽量只读取完成当前步骤所需的上下文。已确认的作者决定与正文默认受到保护，不会被悄然重写。

## 仓库结构

```text
SKILL.md       # Skill 入口与行为约定
agents/        # Codex 展示与调用配置
references/    # 规划、写作、审校和连续性参考规范
scripts/       # TXT 导出与连续性检查工具
novels/        # 本地小说工作区（默认不提交到公开仓库）
```

`novels/` 设计为你的私有创作区，已被 `.gitignore` 排除。若要公开范例，请在 `examples/` 中添加经过授权、已脱敏的最小示例，而不是提交真实稿件。

## 命令行工具

需要 Python 3.10 或更高版本；当前脚本不依赖第三方包。

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

## 开发与验证

```powershell
python -m compileall scripts
python scripts/export_novel_txt.py --help
python scripts/check_continuity_workspace.py --help
```

提交前请确认 Markdown 说明与实际工作流一致，并避免提交未授权的小说正文、个人信息或 API 密钥。

## 最新更新

### 2026-07-16

- 首次开源发布：提供可恢复的长篇小说生产工作流、TXT 导出和连续性检查工具。

完整历史见 [更新记录](docs/releases/release-notes.md)。

## 参与贡献

欢迎改进工作流、补充测试、修正文档或提交经过授权的脱敏示例。提交前请阅读 [贡献指南](CONTRIBUTING.md) 与 [行为准则](CODE_OF_CONDUCT.md)。

## 许可

本项目采用 [Apache License 2.0](LICENSE)。贡献即表示你同意按相同许可发布贡献内容。
