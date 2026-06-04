# Auto-Paper-Reader-for-Zotero

[中文说明](README.zh-CN.md)

Auto-Paper-Reader-for-Zotero is a Codex Skill for building a local AI reading-note layer on top of Zotero-managed PDF attachments.

Zotero stays the source of truth for papers, attachments, and metadata. This skill treats your Zotero PDF attachment root as read-only, writes AI-generated HTML notes under a separate `notes_root`, and keeps a static browser-openable `index.html` for search and review.

## What It Does

- Scans a local Zotero PDF attachment root.
- Builds `paper_index.json` with PDF paths, mirrored note paths, source status, and read status.
- Matches papers by absolute path, relative path, filename, file stem, or title fragment.
- Builds reading packs for Codex-assisted paper reading.
- Extracts PDF text with tools already available in the environment.
- Renders Chinese technical HTML notes from structured note payloads.
- Refreshes a static HTML index with search, status filters, category views, note links, and PDF links.
- Writes only inside the configured `notes_root`.

## How It Works

The skill separates deterministic file work from AI reading work.

```text
Zotero attachment root (read-only)
        |
        | scan / match / extract
        v
paper_index.json + reading pack
        |
        | Codex reads, reasons, and writes a note payload
        v
standalone HTML note
        |
        | refresh
        v
local index.html
```

The scripts handle repeatable operations: config loading, PDF discovery, path mirroring, text extraction, safe note rendering, backups, and index refreshes. Codex handles the paper understanding: summarizing the problem, method, pipeline, experiments, limitations, and value for your research.

## Workflow Boundary

Use the skill when you want Codex to work with papers already managed by Zotero or a Zotero-linked attachment workflow such as Zotero storage, linked attachments, Attanger, ZotMoov, OneDrive, iCloud, Dropbox, a local folder, or a mounted NAS path.

This skill does not:

- replace Zotero;
- modify Zotero SQLite;
- write into the Zotero PDF attachment directory;
- move, rename, or delete PDFs;
- delete old notes when source PDFs disappear;
- upload PDF contents without explicit approval;
- install new dependencies by default;
- start a local server.

Existing notes are backed up inside `notes_root/data/backups/` before replacement.

## Requirements

Required:

- Codex with Skills support.
- Python 3.9 or newer.

The core workflow uses Python standard library modules only. You can scan PDFs, match papers, compute mirrored note paths, render HTML notes, and refresh the local index without installing third-party Python packages.

Full-text PDF extraction is optional but recommended. For `readpack` to extract paper text, provide at least one of:

- `pypdf`
- `pdfplumber`
- `pdftotext`

If none of these extractors is available, `readpack` still returns paper metadata, paths, and note targets, but sets `extraction_status: "no_extractor_available"`. Codex must not claim to have read the full PDF in that state.

## Skill Layout

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

`SKILL.md` is the runtime entry point for Codex. The README files are human-facing GitHub documentation.

## Installation

Install the skill from GitHub:

```bash
python3 /Users/huwt/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo Huenao/Auto-Paper-Reader-for-Zotero \
  --path . \
  --name auto-paper-reader-for-zotero
```

Restart Codex after installation so the new skill is discovered.

After restart, invoke it explicitly:

```text
Use $auto-paper-reader-for-zotero to scan my Zotero PDF folder and generate a local HTML paper note.
```

## First-Time Setup

On first use, configure the two persistent paths:

- `zotero_attachment_root`: your read-only Zotero PDF attachment root.
- `notes_root`: the writable folder for generated HTML notes and indexes.

The recommended setup writes a global config to `~/.config/auto-paper-reader-for-zotero/config.json`, so later Codex sessions and working directories can reuse the same paths:

```bash
python3 scripts/aprz.py init \
  --scope global \
  --zotero-attachment-root "/path/to/zotero/attachments" \
  --notes-root "/path/to/ai/paper-notes"
```

Codex should ask you for these two paths if no config exists, then run the same global init command.

For a workspace-specific override, write project config instead:

```bash
python3 scripts/aprz.py init \
  --scope project \
  --zotero-attachment-root "/path/to/zotero/attachments" \
  --notes-root "/path/to/ai/paper-notes"
```

Project config is stored at `.auto-paper-reader/config.json` and takes priority over the global config.

You can also create the global config manually:

```json
{
  "zotero_attachment_root": "/path/to/zotero/attachments",
  "notes_root": "/path/to/ai/paper-notes",
  "language": "zh-CN",
  "note_format": "html"
}
```

Save it as:

```text
~/.config/auto-paper-reader-for-zotero/config.json
```

## Quickstart

Check configuration and available PDF extraction tools:

```bash
python3 scripts/aprz.py doctor
```

Scan PDFs and refresh the index:

```bash
python3 scripts/aprz.py scan
python3 scripts/aprz.py refresh-index
```

Find a paper:

```bash
python3 scripts/aprz.py find "Attention Is All You Need"
```

Build a reading pack for Codex:

```bash
python3 scripts/aprz.py readpack "Attention Is All You Need" --json
```

Show the mirrored note path:

```bash
python3 scripts/aprz.py note-path "Attention Is All You Need" --json
```

Render a note from a Codex-authored payload:

```bash
python3 scripts/aprz.py render-note \
  --paper-id "sha256:..." \
  --payload "/tmp/note_payload.json"
```

Refresh the browser-openable index:

```bash
python3 scripts/aprz.py refresh-index
```

## Everyday Use

Ask Codex for paper work in natural language:

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

If multiple papers match a query, the skill should list candidates and ask you to choose instead of guessing.

## Workspace And Output

The attachment root is read-only:

```text
<zotero_attachment_root>/
  1.Foundations/
    Transformers/
      Attention Is All You Need.pdf
  2.Foundation-Models/
    LLaMA - Open and Efficient Foundation Language Models.pdf
```

The notes root is where generated files live:

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
    note_payloads/
    backups/
  assets/
```

For a PDF at:

```text
<zotero_attachment_root>/1.Foundations/Transformers/Attention Is All You Need.pdf
```

the default HTML note path is:

```text
<notes_root>/1.Foundations/Transformers/Attention Is All You Need.html
```

This mirrored path design makes it easy to see which note belongs to which Zotero-managed PDF.

## Configuration

Configuration is resolved in this order:

1. Explicit command/request paths.
2. `APRZ_CONFIG_PATH`.
3. `.auto-paper-reader/config.json`.
4. `~/.config/auto-paper-reader-for-zotero/config.json`.
5. `APRZ_ZOTERO_ATTACHMENT_ROOT` and `APRZ_NOTES_ROOT`.

Because project config is checked before global config, a specialized workspace can override your global defaults without changing the global file.

Global config example:

```json
{
  "zotero_attachment_root": "/path/to/zotero/attachments",
  "notes_root": "/path/to/ai/paper-notes",
  "language": "zh-CN",
  "note_format": "html"
}
```

See [references/metadata-schema.md](references/metadata-schema.md) for the generated index and note payload contracts.

## PDF Reading Modes

Auto-Paper-Reader-for-Zotero supports progressive PDF reading:

1. **Metadata-only mode**: Works without third-party packages. Supports scanning, matching, mirrored note paths, note rendering, and index refresh.
2. **Text-extraction mode**: Uses an available extractor to produce full text for `readpack`.
3. **Future advanced mode**: Structured parsers or OCR may be added later for figures, tables, equations, and scanned PDFs. These are not required or implemented in the current version.

`readpack` tries text extractors already available in this order:

1. `pypdf`
2. `pdfplumber`
3. `pdftotext`

If none are available, `readpack` returns `extraction_status: "no_extractor_available"`. In that case Codex should not claim to have read the full PDF.

## Note Style

Generated notes are intended to be useful long-term research notes, not generic abstracts. The default note payload covers:

- one-sentence summary;
- problem the paper solves;
- method overview;
- method pipeline;
- key innovations;
- experimental setup;
- main findings;
- limitations;
- value for your research direction;
- follow-up questions.

See [references/note-writing-guide.md](references/note-writing-guide.md) for the writing contract.

## Safety

The safety boundary is part of the skill contract:

- Treat `zotero_attachment_root` as read-only.
- Write only inside `notes_root`.
- Reject note paths that escape through absolute paths, `..`, or symlinks.
- Back up an existing HTML note before replacing it.
- Mark missing PDFs as `source_missing`; do not delete their notes.
- Stop when config is missing, a computed output path is unsafe, multiple matches need a user choice, or extraction failed but the user asks for a confident full-text conclusion.

See [references/zotero-attachment-policy.md](references/zotero-attachment-policy.md) for the full policy.

## For Maintainers

Run the test suite:

```bash
python3 -m unittest discover -s tests
```

Check the CLI:

```bash
python3 scripts/aprz.py --help
```

Validate the skill structure when PyYAML is available:

```bash
python3 /Users/huwt/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

If validation fails with `ModuleNotFoundError: No module named 'yaml'`, install or provide PyYAML only after explicit approval from the repository owner.

For local development, you may symlink this checkout into your Codex skills directory, but ordinary users should install from GitHub as shown above.
