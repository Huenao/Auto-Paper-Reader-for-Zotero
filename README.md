# Auto-Paper-Reader-for-Zotero

[中文说明](README.zh-CN.md)

Auto-Paper-Reader-for-Zotero is a Codex Skill for building a local AI reading-note layer on top of Zotero-managed PDF attachments.

Zotero stays the source of truth for papers, attachments, and metadata. This skill treats your Zotero PDF attachment root as read-only, writes AI-generated HTML notes under a separate `notes_root`, and keeps a static browser-openable `index.html` for search and review.

## What It Does

- Prefers the Codex Zotero plugin or Zotero local API to resolve collections, items, PDF attachments, local PDF paths, and indexed full text.
- Uses local Python PDF extraction automatically for Zotero-returned PDF paths, while keeping whole-library attachment-root scanning as a confirmation-gated discovery fallback.
- Builds `paper_index.json` with PDF paths, mirrored note paths, source status, and read status.
- Matches papers by absolute path, relative path, filename, file stem, or title fragment.
- Builds reading packs for Codex-assisted paper reading.
- Extracts PDF text with tools already available in the environment.
- Renders selected PDF pages with Poppler and crops inspected architecture figures with Pillow for HTML note evidence.
- Renders Chinese technical HTML notes with a readable paper header, metadata chips, evidence basis, table of contents, note links, and PDF links.
- Refreshes a static HTML paper-library dashboard with search, status filters, research categories, processing queue, expandable paper cards, note links, and PDF links.
- Writes only inside the configured `notes_root`.

## How It Works

The skill separates deterministic file work from AI reading work.

```text
Zotero attachment root (read-only)
        |
        | Zotero plugin/local API first
        | automatic local PDF read/crop when a path is known
        | confirmed root scan only when discovery needs it
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

The scripts handle repeatable operations: config loading, PDF discovery, path mirroring, text extraction, page rendering, figure cropping, safe note rendering, backups, and index refreshes. Codex handles the paper understanding: summarizing the problem, method, pipeline, experiments, limitations, and value for your research.

There are three access routes, and their priority matters:

- **Recommended Zotero-first path**: If the current Codex session has Zotero plugin or local API access, Codex should check Zotero readiness, search collections/items, inspect child attachments, retrieve local PDF paths, and use Zotero-indexed full text when available.
- **Local PDF fallback**: If Zotero returns a usable local PDF path but indexed full text is unavailable, Codex should automatically use bundled Python scripts to index, read, and crop evidence from that PDF.
- **Confirmed path-scan fallback**: If Zotero cannot resolve a specific item/PDF path, Codex must ask before scanning or broadly searching the configured `zotero_attachment_root`.

Codex should not scan the attachment directory if Zotero already provides a usable PDF path or indexed full text. The Python scripts are still responsible for this project's deterministic note workflow: config, path matching, PDF extraction fallback, page rendering and figure cropping, mirrored output paths, HTML rendering, backups, and index refresh.

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

The core workflow uses Python standard library modules only. For specific PDFs inside `zotero_attachment_root`, it can index PDFs, match papers, compute mirrored note paths, render HTML notes, and refresh the local index without installing third-party Python packages.

A Codex Zotero plugin or Zotero local API access is the preferred access route. When available, use it before scanning the attachment root. The skill automatically uses configured-root local PDF extraction when Zotero returns a usable PDF path; it asks only before broad attachment-root scanning/search when no specific PDF path is known.

Full-text PDF extraction is optional but recommended. For `readpack` to extract paper text, provide at least one of:

- `pypdf`
- `pdfplumber`
- `pdftotext`

If none of these extractors is available, `readpack` still returns paper metadata, paths, and note targets, but sets `extraction_status: "no_extractor_available"`. Codex must not claim to have read the full PDF in that state.

Architecture figure cropping is a normal HTML note step when visual tools are available. It uses Poppler `pdfinfo`/`pdftoppm` plus Pillow. Codex should first render and inspect the target page, then pass an explicit `--bbox x1,y1,x2,y2` to crop the final PNG; if no useful figure is found, the note should state that limitation.

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

`SKILL.md` is the runtime entry point for Codex. The runtime skill surface is `SKILL.md`, `agents/`, `scripts/`, `references/`, and `assets/`. The README and test files are repository-development materials for GitHub users and maintainers; a future packaged distribution may exclude them without changing the skill runtime.

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
Use $auto-paper-reader-for-zotero to locate/read my Zotero paper with the Zotero plugin first, then automatically use local PDF extraction and visual cropping when needed, and generate a local HTML paper note.
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

By default, `init` is lightweight: it saves config, creates the notes directory layout, writes an empty `paper_index.json`, and creates an initial `index.html` without scanning the whole attachment root. To index all existing PDFs during setup, opt in explicitly:

```bash
python3 scripts/aprz.py init \
  --scope global \
  --zotero-attachment-root "/path/to/zotero/attachments" \
  --notes-root "/path/to/ai/paper-notes" \
  --scan
```

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

Check configuration and available PDF/visual extraction tools:

```bash
python3 scripts/aprz.py doctor
```

Scan PDFs and refresh the index. Scanning is the slower fallback route for root-level paper discovery, so Codex should ask before using it unless you explicitly request attachment-root indexing. You can also use `init --scan` during first-time setup when you knowingly want a full initial library index:

```bash
python3 scripts/aprz.py scan
python3 scripts/aprz.py refresh-index
```

Find a paper by attachment-root index. Prefer Zotero search first; use this broad fallback only after Zotero-first discovery fails or when you explicitly request root search:

```bash
python3 scripts/aprz.py find "Attention Is All You Need"
```

Build a reading pack for Codex from an indexed query. For a Zotero-returned local PDF path, prefer the direct `--pdf-path` form below:

```bash
python3 scripts/aprz.py readpack "Attention Is All You Need" --json
```

If Zotero indexed full text returns 404 but Zotero already gave Codex a local PDF attachment path, use the direct PDF fallback instead of rescanning or fuzzy matching:

```bash
python3 scripts/aprz.py readpack \
  --pdf-path "/path/to/zotero/attachments/1.Foundations/Transformers/Attention Is All You Need.pdf" \
  --json
```

The PDF path must be inside the configured `zotero_attachment_root`. The command refuses paths outside that root so the skill keeps the Zotero attachment boundary clear.

Show the mirrored note path. If Zotero already supplied a usable PDF path, Codex should avoid fallback lookup unless it is needed for note output:

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

## Viewing HTML Notes

The generated notes and index are static HTML files. You do not need to run a Python web service for normal use.

Recommended local-file mode:

```text
<notes_root>/index.html
<notes_root>/1.Foundations/Transformers/Attention Is All You Need.html
```

Open `index.html` or any single note by double-clicking the file, or by opening it in a browser with a `file://` URL. This is the simplest mode and is usually best for this project because local PDF links are also `file://` links.

Pros:

- no server setup;
- works offline;
- keeps the note system as plain files;
- local PDF links are more likely to open directly from the browser.

Cons:

- browser behavior for local files can vary by OS and browser;
- some browser developer features are easier when using an HTTP URL;
- if you later add features that fetch extra files dynamically, `file://` security rules may become stricter than HTTP.

Optional local HTTP mode:

```bash
cd "/path/to/ai/paper-notes"
python3 -m http.server 8766 --bind 127.0.0.1
```

Then open:

```text
http://127.0.0.1:8766/index.html
```

Pros:

- gives the static site a normal HTTP origin;
- useful for browser debugging or future frontend features;
- makes relative CSS/JS paths behave like a hosted static site.

Cons:

- requires keeping the terminal server running;
- the site is available on localhost while the server is running;
- some browsers may block or warn when an HTTP page opens local `file://` PDF links.

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

For paper lookup, Codex should try Zotero collections/items/attachments first. If Zotero returns a usable local PDF path, Codex should automatically run direct local PDF indexing, reading, and visual-cropping commands as needed. If it cannot get a usable local PDF path or indexed full text, it should explain the blocker and ask before broad attachment-root scanning/search. Once the paper/content is resolved, `render-note` and `refresh-index` remain normal note-output commands.

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
    visuals/
    note_payloads/
    backups/
  assets/
    papers/
      <safe_paper_id>/
        images/
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

1. **Zotero-first mode**: Uses the Zotero plugin/local API for collections, item search, child attachments, local PDF paths, and Zotero-indexed full text.
2. **Local metadata fallback**: Works without third-party packages for specific PDFs inside `zotero_attachment_root`. Supports indexing, matching, mirrored note paths, note rendering, and index refresh.
3. **Local text-extraction fallback**: Uses an available extractor to produce full text for `readpack`.
4. **Local visual-cropping fallback**: Uses Poppler to render selected PDF pages and Pillow to crop inspected architecture figures into local note assets.

If Zotero indexed full text fails with `404 Not Found`, that does not mean the HTML note workflow has failed. When Zotero can still provide a local PDF attachment path, `readpack --pdf-path` can extract text directly from that PDF without scanning the whole attachment root.

For local PDF extraction, `readpack` tries text extractors already available in this order:

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

The renderer also accepts optional display fields inspired by Paper Vault-style research dashboards:

- `research_area`
- `primary_subtopic`
- `priority`
- `reading_status`
- `evidence_basis`
- `next_action`

These fields improve the standalone note header and local index dashboard, but old payloads remain valid when they are absent.

See [references/note-writing-guide.md](references/note-writing-guide.md) for the writing contract.

## Feature Plan

These items are planned or exploratory; they are not implemented as core behavior yet:

- Import selected papers from a research-radar or daily literature digest workflow.
- Add High/Medium priority scoring for newly discovered papers.
- Keep a full-text queue for promising papers that still need a local PDF, Zotero full text, or user-authorized browser access.
- Limit dashboard research areas to at most five broad categories, with drill-down primary subtopics.
- Add optional bilingual note fields for English/Chinese scanning.
- Surface journal/source metadata when it is available from Zotero, DOI metadata, Better BibTeX, or user-provided payloads.
- Enrich notes with Zotero collections, tags, citation keys, and Better BibTeX metadata while keeping Zotero itself read-only.

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
