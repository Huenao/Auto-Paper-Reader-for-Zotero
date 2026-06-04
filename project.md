# Auto-Paper-Reader-for-Zotero MVP 规格文档

## 1. 项目定位

项目名称：Auto-Paper-Reader-for-Zotero
仓库名称：Auto-Paper-Reader-for-Zotero
Skill ID：auto-paper-reader-for-zotero
简称：AutoPaper Reader
中文名称：Zotero 自动论文阅读器

Auto-Paper-Reader-for-Zotero 是一个面向 Zotero 用户的 Codex Skill。它把 Zotero 管理的本地 PDF 附件目录视为只读论文源目录，在独立的 AI 笔记目录中生成结构化 HTML 论文阅读笔记，并维护一个可以直接用浏览器打开的本地 `index.html` 总索引。

核心原则：

- Zotero 管理论文条目、附件和元数据。
- Auto-Paper-Reader-for-Zotero 只管理 AI 阅读笔记和索引。
- PDF 附件目录默认只读，不移动、不重命名、不删除、不写回 Zotero。
- HTML 笔记保存到独立 `notes_root`，并镜像 PDF 在附件目录中的相对路径。

示例：

```text
PDF:
<zotero_attachment_root>/1.LLM/RAG/Self-RAG.pdf

HTML note:
<notes_root>/1.LLM/RAG/Self-RAG.html
```

## 2. 背景和参考项目

Zotero 用户可能通过 Zotero 默认 storage、linked attachment、Attanger、ZotMoov、OneDrive、iCloud、Dropbox、本地磁盘或 NAS 管理论文 PDF。无论实际存储方式如何，第一版只关心一个已经映射为本地路径的 PDF 附件根目录。

参考项目：

- `hwang847/codex-paper-reader`：参考 Codex 论文阅读工作流、本地 PDF 索引、标题匹配、HTML 笔记生成。
- `Zachary709/AutoPaperSkill`：参考自动化论文处理、本地论文归档、HTML 总索引和结构化论文报告思路。

本项目不复制参考项目，而是面向 Zotero 工作流重新定义边界：Zotero 仍是论文管理系统，本 Skill 只增加 AI 阅读笔记层。

## 3. MVP 范围

### 3.1 必须实现

- `SKILL.md`：定义触发条件、工作流、安全边界和输出规范。
- `agents/openai.yaml`：提供 Skill UI 元数据。
- 初始化配置：支持用户指定 `zotero_attachment_root` 和 `notes_root`。
- 扫描 PDF 附件目录，生成 `paper_index.json`。
- 根据绝对路径、相对路径、文件名、标题猜测匹配论文。
- 生成 reading pack，供 Codex 阅读和总结论文。
- 计算镜像 HTML 笔记路径。
- 渲染单篇 HTML 论文阅读笔记。
- 生成 `note_index.json`。
- 生成纯静态 `index.html` 总索引。
- 总索引支持搜索、路径分类、状态筛选、打开笔记、打开原 PDF。
- 所有写入操作只发生在 `notes_root` 内。

### 3.2 第一版不实现

- 不替代 Zotero。
- 不修改 Zotero SQLite。
- 不写回 Zotero note。
- 不移动、重命名或删除 Zotero PDF。
- 不默认下载论文。
- 不默认批量深度阅读所有论文。
- 不实现 PDF 标注同步。
- 不实现本地服务器。
- 不实现高级全文搜索引擎。
- 不强制绑定 Attanger、ZotMoov、OneDrive 或任何云同步工具。

### 3.3 实现优先级

- P0：Skill 可触发、配置读取、PDF 扫描、路径镜像、安全写入。
- P1：论文匹配、reading pack、HTML note 渲染、总索引刷新。
- P2：Better BibTeX、CSL JSON、Zotero collection、Zotero tags 等元数据增强。

## 4. 推荐项目结构

```text
Auto-Paper-Reader-for-Zotero/
  project.md
  SKILL.md
  agents/
    openai.yaml
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
      note.html
      index.html
    note.css
    index.css
    index.js
  tests/
    test_config.py
    test_path_mapping.py
    test_scan.py
    test_match.py
    test_render_note.py
    test_render_index.py
```

说明：

- `SKILL.md` 保持精简，只写核心工作流和资源导航。
- 详细 schema、笔记写作规则和 Zotero 安全策略放在 `references/`。
- HTML/CSS/JS 模板放在 `assets/`，供渲染脚本复制或嵌入。
- 脚本只负责确定性工作；论文理解、解释和高质量总结由 Codex 完成。

## 5. 配置设计

### 5.1 配置文件

项目级配置：

```text
.auto-paper-reader/config.json
```

全局配置：

```text
~/.config/auto-paper-reader-for-zotero/config.json
```

示例：

```json
{
  "zotero_attachment_root": "/path/to/zotero/attachments",
  "notes_root": "/path/to/ai/paper-notes",
  "language": "zh-CN",
  "note_format": "html",
  "mirror_attachment_tree": true,
  "index_filename": "index.html",
  "default_note_style": "technical-readable",
  "include_pdf_link_in_note": true,
  "include_backlink_to_index": true,
  "metadata_mode": "path-first",
  "optional_bibtex_path": "",
  "optional_csl_json_path": "",
  "optional_zotero_sqlite_path": ""
}
```

### 5.2 配置优先级

当脚本或 Codex 需要确定路径时，按以下顺序查找：

1. 本次命令或用户指令中明确给出的路径。
2. `APRZ_CONFIG_PATH` 指向的配置文件。
3. 当前目录下 `.auto-paper-reader/config.json`。
4. `~/.config/auto-paper-reader-for-zotero/config.json`。
5. 环境变量 `APRZ_ZOTERO_ATTACHMENT_ROOT` 和 `APRZ_NOTES_ROOT`。
6. 如果仍无法确定，停止并要求用户提供配置。

## 6. 路径和写入规则

### 6.1 镜像路径

如果 PDF 位于：

```text
<zotero_attachment_root>/A/B/C/Paper.pdf
```

则默认 HTML note 保存为：

```text
<notes_root>/A/B/C/Paper.html
```

### 6.2 文件名安全处理

如果 PDF 文件名包含不适合 HTML 文件名的字符，脚本可以做保守转换。例如：

```text
Self-RAG: Learning to Retrieve.pdf
Self-RAG - Learning to Retrieve.html
```

必须在索引中记录原始 PDF 文件名、PDF 相对路径和实际 note 相对路径，避免后续无法定位已有笔记。

### 6.3 安全写入

- 写入前必须确认目标路径位于 `notes_root` 内。
- 不允许通过 `..`、绝对路径拼接或 symlink 逃逸写出 `notes_root`。
- 生成或更新 HTML note 前，如果目标文件已存在，应先在 `notes_root` 内创建备份。
- PDF 被移动或删除后，不删除旧 note，只在索引中标记 `source_missing`。

## 7. 数据文件设计

所有数据文件默认位于：

```text
<notes_root>/data/
```

### 7.1 paper_index.json

用途：记录扫描到的 PDF 文件、路径映射和基础状态。

```json
{
  "schema_version": 1,
  "generated_at": "2026-06-04T12:00:00+08:00",
  "zotero_attachment_root": "/path/to/zotero/attachments",
  "notes_root": "/path/to/ai/paper-notes",
  "items": [
    {
      "paper_id": "sha256:...",
      "pdf_abs_path": "/path/to/zotero/attachments/1.LLM/RAG/Self-RAG.pdf",
      "pdf_rel_path": "1.LLM/RAG/Self-RAG.pdf",
      "category_path": ["1.LLM", "RAG"],
      "filename": "Self-RAG.pdf",
      "file_stem": "Self-RAG",
      "title_guess": "Self-RAG",
      "authors_guess": [],
      "year_guess": null,
      "file_size": 1234567,
      "modified_at": "2026-06-01T10:00:00+08:00",
      "content_fingerprint": "sha256:...",
      "note_rel_path": "1.LLM/RAG/Self-RAG.html",
      "note_exists": true,
      "note_updated_at": "2026-06-03T18:00:00+08:00",
      "status": "read",
      "tags": [],
      "source_status": "available"
    }
  ]
}
```

### 7.2 note_index.json

用途：记录 HTML notes 摘要，供 `index.html` 使用。

```json
{
  "schema_version": 1,
  "generated_at": "2026-06-04T12:00:00+08:00",
  "items": [
    {
      "paper_id": "sha256:...",
      "title": "Self-RAG",
      "authors": [],
      "year": null,
      "venue": "",
      "pdf_rel_path": "1.LLM/RAG/Self-RAG.pdf",
      "note_rel_path": "1.LLM/RAG/Self-RAG.html",
      "category_path": ["1.LLM", "RAG"],
      "tags": ["RAG", "LLM"],
      "status": "read",
      "source_status": "available",
      "summary": "这篇论文提出让模型自我判断何时检索、如何生成和如何自我批评的 RAG 框架。",
      "updated_at": "2026-06-03T18:00:00+08:00"
    }
  ]
}
```

### 7.3 scan_log.jsonl

用途：记录扫描异常和修复建议。

每行一个 JSON 对象：

```json
{"time":"2026-06-04T12:00:00+08:00","level":"warning","code":"pdf_unreadable","pdf_rel_path":"1.LLM/RAG/Broken.pdf","message":"PDF cannot be opened.","suggestion":"Check whether the file is downloaded locally."}
```

常见 code：

- `pdf_unreadable`
- `cloud_placeholder`
- `metadata_extract_failed`
- `note_path_conflict`
- `duplicate_match_candidate`
- `source_missing`
- `json_corrupted`

## 8. 论文匹配逻辑

用户请求阅读某篇论文时，按以下顺序匹配：

1. 如果用户给出绝对 PDF 路径，确认该路径位于 `zotero_attachment_root` 内。
2. 如果用户给出相对路径，在 `zotero_attachment_root` 下查找。
3. 如果用户给出完整文件名，做精确文件名匹配。
4. 如果用户给出文件名片段，做大小写不敏感的模糊匹配。
5. 如果用户给出论文标题，使用 `title_guess`、PDF 元数据、第一页标题、文件名进行匹配。
6. 如果存在 BibTeX 或 CSL JSON，结合 title、author、year、citation key 匹配。
7. 如果匹配到多个候选，列出候选并让用户选择。
8. 如果没有匹配到，建议用户刷新索引或提供更完整路径。

匹配结果结构：

```json
{
  "match_status": "single_match",
  "confidence": 0.93,
  "reason": "filename fuzzy match + title metadata match",
  "paper_id": "sha256:...",
  "pdf_abs_path": "...",
  "pdf_rel_path": "...",
  "note_abs_path": "...",
  "note_rel_path": "..."
}
```

允许的 `match_status`：

- `single_match`
- `multiple_candidates`
- `not_found`
- `invalid_source_path`

## 9. Reading Pack 设计

Reading pack 是供 Codex 阅读论文时使用的中间结构。脚本负责提取路径、基础元数据、可用文本和章节线索；Codex 负责阅读、解释和生成高质量笔记。

```json
{
  "schema_version": 1,
  "paper_id": "sha256:...",
  "pdf_abs_path": "...",
  "pdf_rel_path": "...",
  "note_abs_path": "...",
  "note_rel_path": "...",
  "title": "Self-RAG",
  "authors": [],
  "year": null,
  "abstract": "",
  "sections": [
    {
      "title": "Introduction",
      "page_start": 1,
      "text_preview": "..."
    }
  ],
  "full_text_path": "<notes_root>/data/extracted_text/sha256....txt",
  "extraction_status": "ok",
  "recommended_reading_order": [
    "abstract",
    "introduction",
    "method",
    "experiments",
    "limitations"
  ]
}
```

`extraction_status` 可取值：

- `ok`
- `partial`
- `no_extractor_available`
- `pdf_unreadable`
- `failed`

## 10. HTML 单篇笔记

每篇论文对应一个独立 HTML 文件，可以直接用浏览器打开。

必须包含：

- 论文标题
- 作者、年份、venue
- Zotero PDF 相对路径
- 原 PDF 文件链接
- 返回总索引链接
- 生成时间和最近更新时间
- 一句话总结
- 论文解决的问题
- 方法概览
- 方法 pipeline
- 关键创新点
- 实验设置
- 主要结论
- 局限性
- 对用户研究方向的价值
- 后续可追问问题

默认风格：

- 使用中文技术笔记风格。
- 避免空泛总结。
- 强调问题、方法、实验、局限和可复现细节。
- 适合后续复习、写 survey、开题和实验设计。

笔记 payload 最小结构：

```json
{
  "paper_id": "sha256:...",
  "title": "Self-RAG",
  "authors": [],
  "year": null,
  "venue": "",
  "summary": "...",
  "problem": "...",
  "method_overview": "...",
  "pipeline": "...",
  "innovations": ["..."],
  "experiments": "...",
  "findings": "...",
  "limitations": "...",
  "value_for_user": "...",
  "follow_up_questions": ["..."]
}
```

## 11. 总索引 index.html

位置：

```text
<notes_root>/index.html
```

第一版实现为纯静态 HTML + CSS + JavaScript，不需要启动本地服务器。

必须支持：

- 查看全部 PDF。
- 查看已有笔记的论文。
- 查看未生成笔记的论文。
- 按路径分类查看。
- 按年份、标签、阅读状态筛选。
- 搜索标题、作者、标签、路径、摘要。
- 打开 HTML 笔记。
- 打开原 PDF。
- 查看最近更新。
- 查看统计信息。

页面信息结构：

```text
Auto-Paper-Reader-for-Zotero

PDF 总数
已有笔记数
未读论文数
分类数量
最近刷新时间

搜索框
分类树
论文列表
```

## 12. CLI 设计

第一版统一使用：

```bash
python3 scripts/aprz.py <command>
```

不要求安装全局命令，不要求新增依赖。

### 12.1 init

```bash
python3 scripts/aprz.py init \
  --zotero-attachment-root "/path/to/zotero/attachments" \
  --notes-root "/path/to/ai/paper-notes"
```

行为：

- 检查 PDF 附件目录是否存在且可读。
- 检查或创建 `notes_root`。
- 创建 `data/`、`assets/` 等必要输出目录。
- 写入项目级配置。
- 执行一次扫描。
- 生成初始 `index.html`。

### 12.2 doctor

```bash
python3 scripts/aprz.py doctor
```

检查：

- 配置文件是否存在。
- PDF 附件根目录是否可读。
- `notes_root` 是否可写。
- PDF 提取工具是否可用。
- HTML 模板是否存在。
- 是否存在路径冲突。
- 是否存在不可读 PDF。

### 12.3 scan

```bash
python3 scripts/aprz.py scan
```

输出：

- PDF 总数。
- 新增 PDF 数。
- source missing 数。
- 已有笔记数。
- 缺失笔记数。
- 错误和警告。

### 12.4 find

```bash
python3 scripts/aprz.py find "Self-RAG"
```

输出匹配结果或候选列表。

### 12.5 readpack

```bash
python3 scripts/aprz.py readpack "Self-RAG" --json
```

输出供 Codex 使用的 reading pack。

### 12.6 note-path

```bash
python3 scripts/aprz.py note-path "Self-RAG" --json
```

输出：

```json
{
  "pdf_rel_path": "1.LLM/RAG/Self-RAG.pdf",
  "note_rel_path": "1.LLM/RAG/Self-RAG.html",
  "note_abs_path": "/path/to/notes/1.LLM/RAG/Self-RAG.html"
}
```

### 12.7 render-note

```bash
python3 scripts/aprz.py render-note \
  --paper-id "sha256:..." \
  --payload "/tmp/note_payload.json"
```

行为：

- 验证 `paper_id` 存在。
- 验证 note 目标路径位于 `notes_root` 内。
- 如果旧 note 存在，先在 `notes_root` 内创建备份。
- 渲染 HTML note。
- 刷新 `note_index.json` 和 `index.html`。

### 12.8 refresh-index

```bash
python3 scripts/aprz.py refresh-index
```

更新：

- `<notes_root>/data/note_index.json`
- `<notes_root>/index.html`

## 13. PDF 提取依赖策略

第一版不强制安装新依赖。

文本提取按以下顺序尝试已经可用的工具：

1. Python 包 `pypdf`
2. Python 包 `pdfplumber`
3. 命令行工具 `pdftotext`

如果都不可用：

- `doctor` 应提示缺少 PDF 提取工具。
- `readpack` 仍返回路径、索引元数据和 `extraction_status: "no_extractor_available"`。
- Codex 不应声称已经读取全文。

## 14. Codex Skill 行为

### 14.1 应触发本 Skill 的请求

- “帮我阅读 Zotero 中的某篇论文”
- “给 Zotero 里的论文生成笔记”
- “把这篇 PDF 论文整理成 HTML 笔记”
- “刷新我的 Zotero 论文笔记索引”
- “打开我的论文笔记首页”
- “按 Zotero PDF 文件夹分类查看笔记”
- “在 Zotero 附件目录中查找某篇论文”
- “把刚才的论文讨论写进本地 HTML 笔记”
- “生成一个可以本地浏览的论文笔记库”

### 14.2 不应默认触发本 Skill 的请求

- 用户只是问通用学术概念。
- 用户只是想在线搜索论文。
- 用户没有提到 Zotero、本地 PDF、论文附件目录或本地 HTML 笔记。
- 用户要求修改 Zotero 数据库。
- 用户要求批量移动、删除或重命名 PDF，但没有明确授权。
- 用户只是想临时总结一段粘贴文本。

### 14.3 Codex 使用流程

当用户要求阅读并生成笔记时：

1. 读取配置，必要时运行 `doctor`。
2. 如果索引不存在或过期，运行 `scan`。
3. 使用 `find` 或 `readpack` 匹配目标 PDF。
4. 如果只有一个匹配，读取 reading pack 和可用 PDF 文本。
5. 如果有多个候选，向用户列出候选，不猜测。
6. 由 Codex 生成结构化 note payload。
7. 运行 `render-note` 写入 HTML note。
8. 自动刷新总索引。
9. 总结生成路径、验证结果和剩余风险。

## 15. 安全与数据保护

必须遵守：

- Zotero PDF 附件目录默认只读。
- 不修改 Zotero SQLite。
- 不移动 Zotero PDF。
- 不删除 Zotero PDF。
- 不重命名 Zotero PDF。
- 不在未确认情况下上传论文内容。
- 不在未确认情况下覆盖已有笔记；覆盖前必须创建备份。
- 所有路径操作必须防止写出 `notes_root`。
- 所有生成文件都应适合长期本地保存。

遇到以下情况时必须停止并说明原因：

- 配置缺失且无法从用户指令中推断。
- 目标写入路径不在 `notes_root` 内。
- 用户要求修改 Zotero source root。
- 用户要求删除或批量移动 PDF。
- 匹配结果存在多个候选且用户未选择。
- PDF 无法读取但用户要求“已阅读全文”的结论。

## 16. 错误处理

需要处理：

- 配置文件不存在。
- PDF root 不存在或不可读。
- `notes_root` 不存在或不可写。
- PDF 文件不可读。
- PDF 是云端占位文件。
- PDF 解析失败。
- 多个 PDF 匹配同一标题。
- 笔记路径冲突。
- 旧笔记存在但无法备份或写入。
- 总索引生成失败。
- 数据 JSON 损坏。
- 用户请求的论文不存在。

处理原则：

- 不静默失败。
- 给出清楚错误原因。
- 给出可执行修复建议。
- 不破坏已有数据。
- 在不确定时停止写入。

## 17. 验收标准

项目完成后必须满足：

- 用户可以配置 Zotero PDF 附件根目录和 AI 笔记根目录。
- 系统可以扫描 PDF 附件目录并建立索引。
- 对于 `<zotero_attachment_root>/1.LLM/RAG/Self-RAG.pdf`，系统生成 `<notes_root>/1.LLM/RAG/Self-RAG.html`。
- 用户可以通过论文标题、文件名和相对路径查找目标 PDF。
- 用户要求生成笔记时，系统能生成可直接浏览的 HTML 文件。
- HTML note 包含原 PDF 链接和返回总索引链接。
- `index.html` 可以显示所有论文。
- `index.html` 可以按路径分类查看。
- `index.html` 可以搜索标题、作者、标签和路径。
- 生成或更新 note 后，总索引会刷新。
- 重复生成同一篇论文 note 时，默认更新旧 note，不生成重复文件。
- 更新旧 note 前会在 `notes_root` 内创建备份。
- PDF 被移动或删除后，系统不会删除旧 note，而是标记 `source_missing`。
- 系统不会修改 Zotero PDF 附件目录中的任何文件。

## 18. 测试计划

使用 Python 标准库 `unittest`，不要求新增测试依赖。

必须覆盖：

- 配置优先级和缺失配置错误。
- 镜像路径计算。
- 文件名安全转换。
- 防止写出 `notes_root`。
- PDF 扫描和 `paper_index.json` 生成。
- `source_missing` 状态。
- 精确和模糊匹配。
- reading pack 在无 PDF 提取工具时的降级行为。
- HTML note 渲染。
- 旧 note 备份。
- `note_index.json` 和 `index.html` 刷新。

建议验证命令：

```bash
python3 -m unittest discover -s tests
python3 scripts/aprz.py --help
python3 /Users/huwt/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/huwt/Library/CloudStorage/OneDrive-个人/Codex/Skills/Auto-Paper-Reader-for-Zotero
```

## 19. 后续增强方向

后续版本可以增加：

- Better BibTeX 导出的 BibTeX 文件。
- CSL JSON。
- Zotero collection 分类。
- Zotero tags。
- 同一篇论文出现在多个分类视图。
- 阅读状态管理。
- 批量生成轻量笔记。
- 多篇论文对比阅读。
- survey 草稿生成。
- 论文关系图。
- 按研究问题聚类。
- note 转 Markdown。
- note 转 PDF。
- 从 HTML note 反向打开 Zotero 条目。
- 本地全文搜索。
- 保存关键图表截图。
- 与用户已有研究项目目录关联。

## 20. 给实现 agent 的最终指令

请根据本规格实现一个 Codex Skill：

- Skill ID：`auto-paper-reader-for-zotero`
- Skill 根目录：当前项目目录
- 第一版范围：MVP
- 语言：中文说明为主，代码和 schema 字段使用英文

必须创建或更新：

- `SKILL.md`
- `agents/openai.yaml`
- `scripts/aprz.py`
- `scripts/config.py`
- `scripts/scan_pdfs.py`
- `scripts/match_paper.py`
- `scripts/extract_pdf.py`
- `scripts/build_readpack.py`
- `scripts/render_note.py`
- `scripts/render_index.py`
- `scripts/path_utils.py`
- `references/metadata-schema.md`
- `references/note-writing-guide.md`
- `references/zotero-attachment-policy.md`
- `assets/templates/note.html`
- `assets/templates/index.html`
- `assets/note.css`
- `assets/index.css`
- `assets/index.js`
- `tests/`

禁止：

- 安装新依赖，除非用户明确确认。
- 写入 Zotero PDF 附件目录。
- 修改 Zotero SQLite。
- 移动、重命名或删除 PDF。
- 删除已有 note。
- 写出 `notes_root`。
- 在未验证的情况下声称已完成。

实现完成后必须总结：

- 修改了哪些文件。
- 为什么这样改。
- 运行了哪些测试、lint、typecheck 或 validation。
- 验证结果。
- 未验证内容和原因。
- 风险或后续建议。
- 提醒用户 review diff。
