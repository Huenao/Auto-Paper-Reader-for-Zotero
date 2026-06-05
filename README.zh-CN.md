# Auto-Paper-Reader-for-Zotero 中文说明

[English README](README.md)

Auto-Paper-Reader-for-Zotero 是一个 Codex Skill，用来在 Zotero 管理的本地 PDF 附件目录之上，增加一层独立的 AI 论文阅读笔记系统。

Zotero 仍然是论文、附件和元数据的来源。这个 Skill 把 Zotero PDF 附件目录视为只读，把 AI 生成的 HTML 论文笔记写入单独的 `notes_root`，并维护一个可以直接用浏览器打开的本地 `index.html` 总索引。

## 它能做什么

- 优先使用 Codex Zotero 插件或 Zotero local API 来定位 collection、条目、PDF 附件、本地 PDF 路径和 Zotero 已索引全文。
- 当 Zotero 返回本地 PDF 路径时，自动使用本地 Python PDF 读取和视觉裁剪；只有整库附件目录扫描仍然需要作为需确认的论文发现兜底。
- 生成 `paper_index.json`，记录 PDF 路径、镜像笔记路径、来源状态和阅读状态。
- 根据绝对路径、相对路径、文件名、文件名主体或标题片段匹配论文。
- 为 Codex 构建 reading pack，辅助论文阅读和总结。
- 使用当前环境中已经存在的 PDF 文本提取工具。
- 使用 Poppler 渲染指定 PDF 页面，并用 Pillow 裁剪已经检查过的方法架构图，作为 HTML 笔记中的图证据。
- 根据结构化 note payload 渲染中文技术 HTML 论文笔记，包含论文摘要区、元数据 chips、证据来源、目录、打开笔记和打开原 PDF。
- 刷新静态 HTML 论文库 dashboard，支持搜索、状态筛选、研究分类、处理队列、可展开论文卡片、打开笔记和打开原 PDF。
- 只写入配置好的 `notes_root`。

## 工作方式

这个 Skill 把确定性的文件操作和 AI 阅读理解分开处理。

```text
Zotero 附件根目录（只读）
        |
        | 优先 Zotero 插件/local API
        | 已知 PDF 路径时自动本地读取/裁剪
        | 只有发现阶段需要时才确认 root scan
        v
paper_index.json + reading pack
        |
        | Codex 阅读、理解并生成 note payload
        v
单篇 HTML 论文笔记
        |
        | refresh
        v
本地 index.html 总索引
```

脚本负责可重复、可验证的工作：读取配置、PDF 发现、计算镜像路径、提取文本、页面渲染、图像裁剪、安全渲染笔记、备份旧笔记、刷新索引。Codex 负责论文理解：总结论文解决的问题、方法、流程、实验、局限性，以及这篇论文对你当前研究方向的价值。

论文定位和读取可以走三类访问路径，并且优先级很重要：

- **推荐的 Zotero-first 路径**：如果当前 Codex 会话可以使用 Zotero 插件或 Zotero local API，Codex 应该先检查 Zotero 状态，查询 collection、搜索 Zotero 条目、查看子附件、获取本地 PDF 路径，并在可用时读取 Zotero 已索引全文。
- **本地 PDF 兜底路径**：如果 Zotero 返回了可用的本地 PDF 路径，但 Zotero 已索引全文不可用，Codex 应该自动使用内置 Python 脚本索引、读取并从这篇 PDF 裁剪证据图。
- **需确认的附件目录扫描兜底路径**：如果 Zotero 无法解析出具体条目或 PDF 路径，Codex 必须先询问用户，才可以扫描或广泛搜索配置好的 `zotero_attachment_root`。

如果 Zotero 已经提供可用的 PDF 路径或已索引全文，Codex 不应该再扫描附件目录。Python 脚本仍然负责这个项目自己的确定性笔记流程：配置读取、路径匹配、PDF 文本提取兜底、页面渲染和图像裁剪、镜像输出路径、HTML 渲染、旧笔记备份和索引刷新。

## 工作边界

当你的论文已经由 Zotero 或 Zotero 相关附件工作流管理时，可以使用这个 Skill。例如 Zotero 默认 storage、linked attachment、Attanger、ZotMoov、OneDrive、iCloud、Dropbox、本地磁盘目录或挂载为本地路径的 NAS。

这个 Skill 不会：

- 替代 Zotero；
- 修改 Zotero SQLite；
- 向 Zotero PDF 附件目录写入文件；
- 移动、重命名或删除 PDF；
- 因为源 PDF 消失而删除旧笔记；
- 在没有明确授权的情况下上传 PDF 内容；
- 默认安装新依赖；
- 启动本地服务器。

如果已有 HTML 笔记需要被更新，旧笔记会先备份到 `notes_root/data/backups/`。

## 环境要求

必需环境：

- 支持 Skills 的 Codex 环境。
- Python 3.9 或更高版本。

核心工作流只使用 Python 标准库。对于 `zotero_attachment_root` 内的具体 PDF，即使不安装第三方 Python 包，也可以索引 PDF、匹配论文、计算镜像笔记路径、渲染 HTML 笔记，并刷新本地总索引。

Codex 的 Zotero 插件或 Zotero local API 是首选访问路径。如果可用，应先通过它查找论文和附件，而不是扫描附件根目录。这个 Skill 在 Zotero 返回可用本地 PDF 路径时，会自动使用配置根目录内的本地 PDF 提取；只有在没有具体 PDF 路径、需要广泛扫描或搜索附件根目录时，才应该先询问用户。

全文 PDF 提取是可选但推荐的能力。如果希望 `readpack` 提取论文正文，请至少提供下面一种工具：

- `pypdf`
- `pdfplumber`
- `pdftotext`

如果这些提取器都不可用，`readpack` 仍会返回论文元数据、路径和目标笔记位置，但会设置 `extraction_status: "no_extractor_available"`。在这种状态下，Codex 不应该声称已经阅读全文。

方法架构图裁剪是 HTML 笔记生成中的常规尝试步骤，只在视觉工具可用时执行。它使用当前环境中已经存在的 Poppler `pdfinfo`/`pdftoppm` 和 Pillow。Codex 应先渲染并检查目标页面，再传入明确的 `--bbox x1,y1,x2,y2` 裁剪最终 PNG；如果没有找到有用图证据，应在 `evidence_basis` 中说明限制。

## Skill 目录结构

```text
SKILL.md
agents/openai.yaml
scripts/
  aprz.py
  config.py
  scan_pdfs.py
  match_paper.py
  extract_pdf.py
  build_readpack.py
  render_note.py
  render_index.py
  path_utils.py
references/
  metadata-schema.md
  note-writing-guide.md
  zotero-attachment-policy.md
assets/
  templates/
  index.css
  index.js
  note.css
tests/
```

`SKILL.md` 是 Codex 真正运行 Skill 时读取的入口。运行时 Skill 表面是 `SKILL.md`、`agents/`、`scripts/`、`references/` 和 `assets/`。README 和测试文件是面向 GitHub 用户及维护者的仓库开发材料；未来如果做打包分发，可以排除它们而不改变 Skill 运行时。

## 安装

从 GitHub 安装：

```bash
python3 /Users/huwt/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo Huenao/Auto-Paper-Reader-for-Zotero \
  --path . \
  --name auto-paper-reader-for-zotero
```

安装后重启 Codex，让新的 Skill 被发现。

重启后可以显式调用：

```text
Use $auto-paper-reader-for-zotero to locate/read my Zotero paper with the Zotero plugin first, then automatically use local PDF extraction and visual cropping when needed, and generate a local HTML paper note.
```

## 首次设置

第一次使用时，需要配置两个会长期复用的路径：

- `zotero_attachment_root`：只读的 Zotero PDF 附件根目录。
- `notes_root`：用于保存 HTML 笔记和索引的可写目录。

推荐写入全局配置 `~/.config/auto-paper-reader-for-zotero/config.json`，这样后续不同 Codex 会话和不同工作目录都可以复用同一套路径：

```bash
python3 scripts/aprz.py init \
  --scope global \
  --zotero-attachment-root "/path/to/zotero/attachments" \
  --notes-root "/path/to/ai/paper-notes"
```

如果没有找到配置，Codex 应该先询问你这两个路径，然后运行同样的全局初始化命令。

默认情况下，`init` 是轻量初始化：保存配置、创建笔记目录结构、写入空的 `paper_index.json`，并创建初始 `index.html`，不会扫描整个附件根目录。如果你确实希望在设置时索引所有现有 PDF，需要显式开启：

```bash
python3 scripts/aprz.py init \
  --scope global \
  --zotero-attachment-root "/path/to/zotero/attachments" \
  --notes-root "/path/to/ai/paper-notes" \
  --scan
```

如果某个工作区需要单独覆盖全局配置，可以写入项目配置：

```bash
python3 scripts/aprz.py init \
  --scope project \
  --zotero-attachment-root "/path/to/zotero/attachments" \
  --notes-root "/path/to/ai/paper-notes"
```

项目配置保存到 `.auto-paper-reader/config.json`，并且优先级高于全局配置。

也可以手动创建全局配置：

```json
{
  "zotero_attachment_root": "/path/to/zotero/attachments",
  "notes_root": "/path/to/ai/paper-notes",
  "language": "zh-CN",
  "note_format": "html"
}
```

保存路径为：

```text
~/.config/auto-paper-reader-for-zotero/config.json
```

## 快速开始

检查配置和可用 PDF/视觉提取工具：

```bash
python3 scripts/aprz.py doctor
```

扫描 PDF 并刷新索引。扫描是较慢的整库论文发现兜底路径，Codex 应该先询问你，除非你已经明确要求索引附件根目录。如果你明确希望首次设置时就建立完整库索引，也可以使用 `init --scan`：

```bash
python3 scripts/aprz.py scan
python3 scripts/aprz.py refresh-index
```

通过附件根目录索引查找论文。应先使用 Zotero 搜索；只有 Zotero-first 发现失败，或你明确要求搜索附件根目录时，才使用这个广泛兜底：

```bash
python3 scripts/aprz.py find "Attention Is All You Need"
```

从索引查询构建给 Codex 使用的 reading pack。如果 Zotero 已返回本地 PDF 路径，应优先使用下面的直接 `--pdf-path` 形式：

```bash
python3 scripts/aprz.py readpack "Attention Is All You Need" --json
```

如果 Zotero indexed full text 返回 404，但 Zotero 已经给 Codex 返回了本地 PDF 附件路径，可以使用直接 PDF 兜底，而不是重新扫描或模糊匹配：

```bash
python3 scripts/aprz.py readpack \
  --pdf-path "/path/to/zotero/attachments/1.Foundations/Transformers/Attention Is All You Need.pdf" \
  --json
```

这个 PDF 路径必须位于配置好的 `zotero_attachment_root` 内。命令会拒绝 root 外路径，以保持 Zotero 附件边界清晰。

查看镜像笔记路径。如果 Zotero 已经提供了可用 PDF 路径，Codex 应该避免额外兜底查找，除非生成笔记确实需要：

```bash
python3 scripts/aprz.py note-path "Attention Is All You Need" --json
```

根据 Codex 生成的 note payload 渲染 HTML 笔记：

```bash
python3 scripts/aprz.py render-note \
  --paper-id "sha256:..." \
  --payload "/tmp/note_payload.json"
```

刷新可以直接用浏览器打开的总索引：

```bash
python3 scripts/aprz.py refresh-index
```

## 查看 HTML 笔记

生成的笔记和总索引都是静态 HTML 文件。正常使用时不需要启动 Python Web 服务。

推荐的本地文件模式：

```text
<notes_root>/index.html
<notes_root>/1.Foundations/Transformers/Attention Is All You Need.html
```

你可以直接双击 `index.html` 或任意单篇笔记，也可以在浏览器中用 `file://` URL 打开。这个模式最简单，也最适合当前项目，因为“打开原 PDF”的链接同样是本地 `file://` 链接。

优点：

- 不需要启动服务；
- 离线可用；
- 笔记系统保持为普通文件；
- 本地 PDF 链接通常更容易直接从浏览器打开。

缺点：

- 不同系统和浏览器对本地文件的行为可能略有差异；
- 有些浏览器调试功能在 HTTP URL 下更方便；
- 如果后续加入动态加载额外文件的前端能力，`file://` 的安全限制可能比 HTTP 更严格。

可选的本地 HTTP 模式：

```bash
cd "/path/to/ai/paper-notes"
python3 -m http.server 8766 --bind 127.0.0.1
```

然后打开：

```text
http://127.0.0.1:8766/index.html
```

优点：

- 给静态站点一个正常的 HTTP origin；
- 适合浏览器调试或未来更复杂的前端功能；
- 相对路径 CSS/JS 的行为更接近部署后的静态站点。

缺点：

- 需要保持终端里的 HTTP 服务运行；
- 服务运行期间页面会在本机 localhost 上可访问；
- 某些浏览器可能会阻止或提示 HTTP 页面打开本地 `file://` PDF 链接。

## 日常使用示例

可以用自然语言让 Codex 操作这个 Skill：

```text
Use $auto-paper-reader-for-zotero to initialize my paper note system.
My Zotero PDF attachment root is /Users/me/ZoteroPapers.
My AI notes root is /Users/me/PaperNotes.
```

```text
Use $auto-paper-reader-for-zotero to read the Attention Is All You Need paper from my Zotero folder.
Focus on the transformer architecture, attention mechanism, experiments, and limitations.
```

```text
Use $auto-paper-reader-for-zotero to generate a Chinese HTML note for LLaMA: Open and Efficient Foundation Language Models.
Emphasize model scale, training data, efficiency choices, evaluation setup, and reproducibility details.
```

```text
Use $auto-paper-reader-for-zotero to refresh my paper index and show me which papers still have no notes.
```

如果同一个查询匹配到多篇论文，Skill 应该列出候选项并让你选择，而不是自行猜测。

论文查找时，Codex 应该先通过 Zotero collection、条目和附件定位 PDF。如果 Zotero 返回可用本地 PDF 路径，Codex 应该按需自动运行直接本地 PDF 索引、读取和视觉裁剪命令。如果无法获得可用本地 PDF 路径或已索引全文，Codex 应该说明阻塞点，并在广泛扫描或搜索附件根目录前请求你的同意。论文或正文解析完成后，`render-note` 和 `refresh-index` 仍然是正常的笔记输出命令。

## 工作区与输出结构

Zotero 附件根目录是只读来源：

```text
<zotero_attachment_root>/
  1.Foundations/
    Transformers/
      Attention Is All You Need.pdf
  2.Foundation-Models/
    LLaMA - Open and Efficient Foundation Language Models.pdf
```

AI 笔记根目录保存所有生成文件：

```text
<notes_root>/
  index.html
  1.Foundations/
    Transformers/
      Attention Is All You Need.html
  2.Foundation-Models/
    LLaMA - Open and Efficient Foundation Language Models.html
  data/
    paper_index.json
    note_index.json
    scan_log.jsonl
    extracted_text/
    visuals/
    note_payloads/
    backups/
  assets/
    papers/
      <safe_paper_id>/
        images/
```

例如 PDF 位于：

```text
<zotero_attachment_root>/1.Foundations/Transformers/Attention Is All You Need.pdf
```

默认生成的 HTML 笔记路径是：

```text
<notes_root>/1.Foundations/Transformers/Attention Is All You Need.html
```

这种镜像路径设计让你长期维护笔记时更容易判断：哪篇 PDF 对应哪篇 AI 笔记、哪些论文还没有笔记、某个分类目录下有哪些已读论文。

## 配置

配置按以下顺序解析：

1. 当前命令或用户请求中显式给出的路径。
2. `APRZ_CONFIG_PATH`。
3. `.auto-paper-reader/config.json`。
4. `~/.config/auto-paper-reader-for-zotero/config.json`。
5. `APRZ_ZOTERO_ATTACHMENT_ROOT` 和 `APRZ_NOTES_ROOT`。

因为项目配置会先于全局配置读取，特殊工作区可以覆盖全局默认路径，而不需要改动全局配置文件。

全局配置示例：

```json
{
  "zotero_attachment_root": "/path/to/zotero/attachments",
  "notes_root": "/path/to/ai/paper-notes",
  "language": "zh-CN",
  "note_format": "html"
}
```

生成的索引和 note payload 结构见 [references/metadata-schema.md](references/metadata-schema.md)。

## PDF 读取模式

Auto-Paper-Reader-for-Zotero 支持渐进式 PDF 读取：

1. **Zotero-first 模式**：使用 Zotero 插件/local API 处理 collection、条目搜索、子附件、本地 PDF 路径和 Zotero 已索引全文。
2. **本地元数据模式**：对 `zotero_attachment_root` 内的具体 PDF 不需要第三方包。支持索引、匹配、镜像笔记路径、笔记渲染和索引刷新。
3. **本地文本提取模式**：使用当前环境中可用的提取器，为 `readpack` 生成正文文本。
4. **本地视觉裁剪模式**：使用 Poppler 渲染指定 PDF 页面，并用 Pillow 把已检查过的方法架构图裁剪成本地笔记资源。

如果 Zotero indexed full text 返回 `404 Not Found`，这不代表 HTML 笔记流程失败。只要 Zotero 仍然能提供本地 PDF 附件路径，`readpack --pdf-path` 就可以直接从该 PDF 提取正文，不需要扫描整个附件根目录。

对于配置根目录内的具体 PDF，`readpack` 会按顺序尝试当前环境已经可用的文本提取工具：

1. `pypdf`
2. `pdfplumber`
3. `pdftotext`

如果都不可用，`readpack` 会返回 `extraction_status: "no_extractor_available"`。此时 Codex 不应该声称已经阅读全文。

## 笔记风格

生成的笔记目标是长期可复习、可用于研究整理的技术笔记，而不是泛泛的摘要。默认 note payload 覆盖：

- 一句话总结；
- 论文解决的问题；
- 方法概览；
- 方法 pipeline；
- 关键创新点；
- 实验设置；
- 主要结论；
- 局限性；
- 对你当前研究方向的价值；
- 后续可追问问题。

渲染器还支持受 Paper Vault 式研究 dashboard 启发的可选展示字段：

- `research_area`
- `primary_subtopic`
- `priority`
- `reading_status`
- `evidence_basis`
- `next_action`

这些字段会增强单篇笔记页头部和本地总索引 dashboard；如果旧 payload 没有这些字段，也仍然可以正常渲染。

写作规则见 [references/note-writing-guide.md](references/note-writing-guide.md)。

## Feature Plan

以下是计划或探索项，不代表当前核心功能已经实现：

- 从 research-radar 或每日文献日报工作流导入筛选后的论文。
- 为新发现论文增加 High/Medium 优先级评分。
- 为有潜力但还缺本地 PDF、Zotero 全文或用户授权浏览器访问的论文维护全文队列。
- 将 dashboard 研究大类控制在最多 5 个，并支持主子主题钻取。
- 增加可选中英文双语笔记字段，方便快速浏览。
- 在 Zotero、DOI 元数据、Better BibTeX 或用户 payload 可用时展示期刊和来源信息。
- 在保持 Zotero 只读的前提下，用 Zotero collections、tags、citation keys 和 Better BibTeX 元数据增强笔记。

## 安全规则

安全边界是这个 Skill 的核心契约：

- 把 `zotero_attachment_root` 当作只读目录。
- 只写入 `notes_root`。
- 拒绝通过绝对路径、`..` 或 symlink 逃逸出 `notes_root` 的笔记路径。
- 替换已有 HTML 笔记前先备份。
- PDF 消失时标记为 `source_missing`，不要删除已有笔记。
- 当配置缺失、输出路径不安全、匹配结果需要用户选择，或提取失败但用户要求确定的全文结论时，停止并说明原因。

完整策略见 [references/zotero-attachment-policy.md](references/zotero-attachment-policy.md)。

## 维护者检查

运行测试：

```bash
python3 -m unittest discover -s tests
```

检查 CLI：

```bash
python3 scripts/aprz.py --help
```

当 PyYAML 可用时，校验 Skill 结构：

```bash
python3 /Users/huwt/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

如果校验失败并提示 `ModuleNotFoundError: No module named 'yaml'`，说明当前 Python 环境缺少 PyYAML。不要在未经仓库所有者确认的情况下安装新依赖。

本地开发时，可以把当前 checkout symlink 到 Codex skills 目录；普通用户应优先使用上面的 GitHub 安装方式。
