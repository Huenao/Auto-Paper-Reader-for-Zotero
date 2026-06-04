# Auto-Paper-Reader-for-Zotero 中文说明

[English README](README.md)

Auto-Paper-Reader-for-Zotero 是一个 Codex Skill，用来在 Zotero 管理的本地 PDF 附件目录之上，增加一层独立的 AI 论文阅读笔记系统。

Zotero 仍然是论文、附件和元数据的来源。这个 Skill 把 Zotero PDF 附件目录视为只读，把 AI 生成的 HTML 论文笔记写入单独的 `notes_root`，并维护一个可以直接用浏览器打开的本地 `index.html` 总索引。

这个项目参考了 [hwang847/codex-paper-reader](https://github.com/hwang847/codex-paper-reader) 的论文阅读工作流组织方式，但本项目的核心目标是适配 Zotero 用户已有的附件目录结构，而不是接管论文存储。

## 它能做什么

- 扫描本地 Zotero PDF 附件根目录。
- 生成 `paper_index.json`，记录 PDF 路径、镜像笔记路径、来源状态和阅读状态。
- 根据绝对路径、相对路径、文件名、文件名主体或标题片段匹配论文。
- 为 Codex 构建 reading pack，辅助论文阅读和总结。
- 使用当前环境中已经存在的 PDF 文本提取工具。
- 根据结构化 note payload 渲染中文技术 HTML 论文笔记。
- 刷新静态 HTML 总索引，支持搜索、状态筛选、分类查看、打开笔记和打开原 PDF。
- 只写入配置好的 `notes_root`。

## 工作方式

这个 Skill 把确定性的文件操作和 AI 阅读理解分开处理。

```text
Zotero 附件根目录（只读）
        |
        | scan / match / extract
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

脚本负责可重复、可验证的工作：读取配置、扫描 PDF、计算镜像路径、提取文本、安全渲染笔记、备份旧笔记、刷新索引。Codex 负责论文理解：总结论文解决的问题、方法、流程、实验、局限性，以及这篇论文对你当前研究方向的价值。

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

`SKILL.md` 是 Codex 真正运行 Skill 时读取的入口。README 文件面向 GitHub 读者，用来说明项目定位、安装方式和使用流程。

## 安装

可以通过 GitHub 安装，也可以在本地开发时使用 symlink。

### 方式一：从 GitHub 安装

适合从已发布仓库安装：

```bash
python3 /Users/huwt/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo Huenao/Auto-Paper-Reader-for-Zotero \
  --path . \
  --name auto-paper-reader-for-zotero
```

安装后重启 Codex，让新的 Skill 被发现。

### 方式二：本地 symlink

适合开发这个 Skill 时使用。这样 Codex 可以直接使用当前 checkout 中的修改。

```bash
mkdir -p "$HOME/.codex/skills"

ln -s "/Users/huwt/Library/CloudStorage/OneDrive-个人/Codex/Skills/Auto-Paper-Reader-for-Zotero" \
  "$HOME/.codex/skills/auto-paper-reader-for-zotero"
```

创建 symlink 后重启 Codex。

重启后可以显式调用：

```text
Use $auto-paper-reader-for-zotero to scan my Zotero PDF folder and generate a local HTML paper note.
```

## 快速开始

初始化本地论文笔记工作区：

```bash
python3 scripts/aprz.py init \
  --zotero-attachment-root "/path/to/zotero/attachments" \
  --notes-root "/path/to/ai/paper-notes"
```

检查配置和可用 PDF 文本提取工具：

```bash
python3 scripts/aprz.py doctor
```

扫描 PDF 并刷新索引：

```bash
python3 scripts/aprz.py scan
python3 scripts/aprz.py refresh-index
```

查找论文：

```bash
python3 scripts/aprz.py find "Self-RAG"
```

构建给 Codex 使用的 reading pack：

```bash
python3 scripts/aprz.py readpack "Self-RAG" --json
```

查看镜像笔记路径：

```bash
python3 scripts/aprz.py note-path "Self-RAG" --json
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

## 日常使用示例

可以用自然语言让 Codex 操作这个 Skill：

```text
Use $auto-paper-reader-for-zotero to initialize my paper note system.
My Zotero PDF attachment root is /Users/me/ZoteroPapers.
My AI notes root is /Users/me/PaperNotes.
```

```text
Use $auto-paper-reader-for-zotero to read the Self-RAG paper from my Zotero folder.
Focus on the method pipeline, training objective, experiments, and limitations.
```

```text
Use $auto-paper-reader-for-zotero to generate a Chinese HTML note for APEX-SQL.
Emphasize task definition, agent flow, tool use, state maintenance, and reproducibility details.
```

```text
Use $auto-paper-reader-for-zotero to refresh my paper index and show me which papers still have no notes.
```

如果同一个查询匹配到多篇论文，Skill 应该列出候选项并让你选择，而不是自行猜测。

## 工作区与输出结构

Zotero 附件根目录是只读来源：

```text
<zotero_attachment_root>/
  1.LLM/
    RAG/
      Self-RAG.pdf
  2.Text-to-SQL/
    APEX-SQL.pdf
```

AI 笔记根目录保存所有生成文件：

```text
<notes_root>/
  index.html
  1.LLM/
    RAG/
      Self-RAG.html
  2.Text-to-SQL/
    APEX-SQL.html
  data/
    paper_index.json
    note_index.json
    scan_log.jsonl
    extracted_text/
    note_payloads/
    backups/
  assets/
```

例如 PDF 位于：

```text
<zotero_attachment_root>/1.LLM/RAG/Self-RAG.pdf
```

默认生成的 HTML 笔记路径是：

```text
<notes_root>/1.LLM/RAG/Self-RAG.html
```

这种镜像路径设计让你长期维护笔记时更容易判断：哪篇 PDF 对应哪篇 AI 笔记、哪些论文还没有笔记、某个分类目录下有哪些已读论文。

## 配置

配置按以下顺序解析：

1. 当前命令或用户请求中显式给出的路径。
2. `APRZ_CONFIG_PATH`。
3. `.auto-paper-reader/config.json`。
4. `~/.config/auto-paper-reader-for-zotero/config.json`。
5. `APRZ_ZOTERO_ATTACHMENT_ROOT` 和 `APRZ_NOTES_ROOT`。

示例：

```json
{
  "zotero_attachment_root": "/path/to/zotero/attachments",
  "notes_root": "/path/to/ai/paper-notes",
  "language": "zh-CN",
  "note_format": "html"
}
```

生成的索引和 note payload 结构见 [references/metadata-schema.md](references/metadata-schema.md)。

## PDF 文本提取

这个 Skill 默认不安装 PDF 提取依赖。`readpack` 会按顺序尝试当前环境已经可用的工具：

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

写作规则见 [references/note-writing-guide.md](references/note-writing-guide.md)。

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

## License

尚未选择 License。
