# ANI 本地阅读台

可选的 React 阅读工具，承载 `analyses/` 拆书工作区和 `novels/` 小说工作区中的 Markdown。使用 React Router、Fumadocs UI/Core 和 `@fumadocs/local-md`；独立启动，不影响未安装阅读端的 Skill 使用。

## 启动

需要 Node.js 22.18+ 和 npm。Windows 可直接运行：

```powershell
cd apps/workspace-reader
./start-local.ps1
```

打开 <http://127.0.0.1:8790>。默认读取本仓库中的 `novels/` 与 `analyses/`。

要阅读其他位置的稿件，传入一个或多个绝对路径：

```powershell
./start-local.ps1 -Roots 'C:/writing', 'D:/research'
```

目录可以是包含 `novels/`、`analyses/` 的父目录，这两个目录本身，或者带 `novel-state.yaml` / `analysis-state.yaml` / `analysis-manifest.yaml` / `source-manifest.md` 的单个工作区。路径仅在本机使用，不需要移动稿件。

其他系统或手动启动：

```text
npm ci --include=dev
npm run build
npm start
```

通过环境变量 `ANI_READER_ROOTS` 指定绝对路径的 JSON 数组，`PORT` 指定生产端口。启动时须以本应用目录为工作目录。开发模式使用 `npm run dev`，Windows 助手也支持 `-Dev`。

## 已实现

- 书架按小说/拆书筛选，显示工作区及资料数量。
- 资料分类和完整原始目录树并存；没有 frontmatter 的 Markdown 同样可读。
- 重复的计划、正文与审校文件带章节名称；按数字顺序阅读，优先提供已有修订正文。
- Markdown 表格、列表、代码块、页内目录，以及工作区内部相对链接和本地图片。
- 当前工作区或全书架的中文全文搜索，文件变化后重新建立本地索引。
- 调整字号、明暗主题、查看来源文件及 SHA-256 指纹。
- 页面可见时每 8 秒检查更新，也支持手动刷新；新增、修改、删除文件都会反映在导航与阅读内容中。
- 根据状态文件显示产物状态；实际内容指纹与记录不一致时显示“文件已有修改”，不改动状态文件。
- 拆书工作台区分计划窗口与实际已读范围，展示专项分析缺口、分段笔记和可选机制；不会用计划范围推算完成百分比。
- 读取 `pattern-cards.yaml` 的机制卡，核对来源记录、证据指纹与状态。可选择机制、目标小说和章节，复制接入请求给 Codex。
- 小说总览展示各章参考选择、本书改造与审校目标，并提示来源是否匹配；不会沿清单读取未加入当前书架的目录。

## 拆书如何进入生成

只有分段笔记时，先用工作台的“复制整理请求”交给 Codex，将可复用原理、前提、失败方式和证据整理成机制卡。有机制卡后，选择适合本章的卡与目标小说，复制接入请求。Codex 依据本书定位、计划和连续性提出原创改造，再创建 `context-packages/chapter-XXX.references.yaml`，校验后装入生成上下文；审校检查机制实际效果。

底层脚本与 Skill 合同见 [拆书接入小说](../../references/analysis-to-novel.md)。阅读台负责选择和展示，创作仍在 Codex 中进行；复制请求不会直接修改任何稿件。

## 边界与限制

仅提供读取。浏览器通过独立的本地 Node 服务查看明确配置的工作区；生产服务只监听 `127.0.0.1`，只接受 GET/HEAD。不会调用模型、运行 `novelctl`、保存正文修改或修改权威 Markdown/YAML。符号链接、目录穿越及不支持的资源类型不会被提供。

稿件按纯 Markdown 解析，原始 HTML 不执行；MDX 不在读取范围内。正文和索引保留在本机，不调用云端搜索。远程图片显示为链接，避免阅读时自动向外部服务器请求资源。

首版每次刷新会扫描配置的工作区，首次搜索会建立索引；大型跨书资料库需要后续性能评估。文件编辑仍在原工作区进行；阅读端尚未提供批注、编辑或反馈提交。未被状态索引登记的 MD 仍能阅读，但不会推断其验收状态。

## 验证

```text
npm run typecheck
npm test
npm run build
```

测试覆盖小说/拆书发现、无 frontmatter 内容、中文搜索及更新、Markdown 表格和链接、原始 HTML、特殊文件名、目录越界与符号链接，以及状态源保持不变。仓库级 Python 验证仍按根目录开发说明执行。

Windows 运行仓库级 Python 测试时，设置 `PYTHONUTF8=1` 和 `PYTHONIOENCODING=utf-8`，使测试启动的子进程同样使用 UTF-8。
