# Auto-Paper-Reader-for-Zotero

Auto-Paper-Reader-for-Zotero is a Codex Skill for building a local AI reading-note layer on top of Zotero-managed PDF attachments.

Zotero remains the source of truth for papers, attachments, and metadata. This skill treats the Zotero PDF attachment root as read-only, generates standalone HTML paper notes under a separate `notes_root`, and maintains a static browser-openable `index.html`.

## What It Does

- Scans a local Zotero PDF attachment root.
- Builds `paper_index.json` with PDF paths, note paths, and read status.
- Matches papers by absolute path, relative path, filename, or title fragment.
- Builds reading packs for Codex-assisted paper reading.
- Renders Chinese technical HTML notes from structured note payloads.
- Refreshes a static HTML index with search, status filters, category views, note links, and PDF links.
- Writes only inside the configured `notes_root`.

## Safety Boundary

This skill does not:

- modify Zotero SQLite;
- write into the Zotero PDF attachment directory;
- move, rename, or delete PDFs;
- delete old notes when source PDFs disappear;
- install new dependencies by default;
- start a local server.

Existing notes are backed up inside `notes_root/data/backups/` before being replaced.

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
assets/
tests/
```

## Installation

Install the skill into Codex with either a local symlink or the GitHub installer.

### Option 1: Local Symlink

Use this when you are developing the skill locally and want Codex to pick up future edits from this checkout.

```bash
mkdir -p "$HOME/.codex/skills"

ln -s "/Users/huwt/Library/CloudStorage/OneDrive-个人/Codex/Skills/Auto-Paper-Reader-for-Zotero" \
  "$HOME/.codex/skills/auto-paper-reader-for-zotero"
```

Restart Codex after creating the symlink.

### Option 2: Install from GitHub

Use this when installing from the published repository:

```bash
python3 /Users/huwt/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo Huenao/Auto-Paper-Reader-for-Zotero \
  --path . \
  --name auto-paper-reader-for-zotero
```

Restart Codex after installation so the new skill is discovered.

After restart, invoke it explicitly in Codex:

```text
Use $auto-paper-reader-for-zotero to scan my Zotero PDF folder and generate a local HTML paper note.
```

## Quick Start

Initialize the local note workspace:

```bash
python3 scripts/aprz.py init \
  --zotero-attachment-root "/path/to/zotero/attachments" \
  --notes-root "/path/to/ai/paper-notes"
```

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
python3 scripts/aprz.py find "Self-RAG"
```

Build a reading pack:

```bash
python3 scripts/aprz.py readpack "Self-RAG" --json
```

Render a note from a Codex-authored payload:

```bash
python3 scripts/aprz.py render-note \
  --paper-id "sha256:..." \
  --payload "/tmp/note_payload.json"
```

## Configuration

Configuration is resolved in this order:

1. Explicit command/request paths.
2. `APRZ_CONFIG_PATH`.
3. `.auto-paper-reader/config.json`.
4. `~/.config/auto-paper-reader-for-zotero/config.json`.
5. `APRZ_ZOTERO_ATTACHMENT_ROOT` and `APRZ_NOTES_ROOT`.

Example:

```json
{
  "zotero_attachment_root": "/path/to/zotero/attachments",
  "notes_root": "/path/to/ai/paper-notes",
  "language": "zh-CN",
  "note_format": "html"
}
```

## Output Files

Generated files live under `notes_root`:

```text
notes_root/
  index.html
  data/
    paper_index.json
    note_index.json
    scan_log.jsonl
    extracted_text/
    backups/
```

For a PDF at:

```text
<zotero_attachment_root>/1.LLM/RAG/Self-RAG.pdf
```

the default note path is:

```text
<notes_root>/1.LLM/RAG/Self-RAG.html
```

## Validation

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

## License

No license has been selected yet.
