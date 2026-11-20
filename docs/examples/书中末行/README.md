# 《书中末行》第 37 章工程快照

原始设定是“修书匠能听见每本书被删掉的最后一句话”。这份快照保存了第 1–37 章的验收稿，共 82,171 个正文汉字。第 38 章的计划和上下文已就绪，下一步是写初稿。第 37 章保留当时的原文，包括随后要修订的“第三个”。

[下载阶段工程 ZIP](书中末行-第37章工程快照.zip) · [只读正文 TXT](书中末行-第1至37章.txt) · [第一章开头的检测截图](AI检测截图.png)

| 想看什么 | 解压后的位置 |
| --- | --- |
| 一句话设定如何展开为三卷 | `novel-brief.md`、`story-bible.md`、`volumes/` |
| 书的规则和主要人物 | `world-bible.md`、`characters/` |
| 一章怎样从计划走到定稿 | `chapters/chapter-001/` 内的计划、上下文、初稿、修订稿和审校意见 |
| 较早的承诺如何跨章追踪 | `continuity/` 内的伏笔台账、逐章差分和检查点 |
| 中断位置、审读发现和已导出的正文 | `novel-state.yaml`、`production/`、`exports/` |

### 在本地恢复

从仓库根目录执行以下 PowerShell 命令。示例将快照解压到一个独立的本地目录。还原时用仓库里的 `scripts/novelctl.py` 检查状态；此快照对应的 Skill 版本为 [85db02f](https://github.com/ExplosiveCoderflome/ani-book-skill/commit/85db02f14414ac306a5fbfae09a894f2e4dc6d91)。

```powershell
$snapshot = 'docs/examples/书中末行/书中末行-第37章工程快照.zip'
$destination = Join-Path $env:TEMP ('novel-example-' + [guid]::NewGuid())
Expand-Archive -LiteralPath $snapshot -DestinationPath $destination
$book = Join-Path $destination '书中末行'
python -X utf8 scripts/novelctl.py validate $book
python -X utf8 scripts/novelctl.py status $book --measure-length
python -X utf8 scripts/novelctl.py next $book
```

发布前已逐文件核对解压出的 253 个文件。校验返回零错误、零告警，下一步为 `chapter_038_draft`。
