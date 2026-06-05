---
name: auto-paper-reader-for-zotero
description: Use for Zotero-managed papers when Codex needs to locate or read Zotero PDFs, prefer the Codex Zotero plugin/local API for collections, items, attachments, local PDF paths, or indexed full text, and generate standalone Chinese HTML paper notes with a local static index. Use bundled Python scripts automatically for Zotero-returned local PDFs, configured-root PDF extraction, visual crops, readpacks, and deterministic note rendering without modifying Zotero files.
---

# Auto-Paper-Reader-for-Zotero

Use this skill to add an AI note layer on top of Zotero-managed papers. Prefer Codex's Zotero plugin or Zotero local API for paper discovery and PDF/full-text access. Treat the Zotero attachment root as read-only. Write only under the configured `notes_root`.

## Script

Resolve paths from this skill directory. Use the unified CLI:

```text
python3 scripts/aprz.py init --scope global --zotero-attachment-root "/path/to/zotero/attachments" --notes-root "/path/to/ai/paper-notes"
python3 scripts/aprz.py init --scope project --zotero-attachment-root "/path/to/zotero/attachments" --notes-root "/path/to/ai/paper-notes"
python3 scripts/aprz.py doctor
python3 scripts/aprz.py scan
python3 scripts/aprz.py scan --force-hash
python3 scripts/aprz.py index-pdf --pdf-path "/path/to/zotero/attachments/1.LLM/RAG/Self-RAG.pdf" --json
python3 scripts/aprz.py find "Self-RAG"
python3 scripts/aprz.py readpack "Self-RAG" --json
python3 scripts/aprz.py readpack --pdf-path "/path/to/zotero/attachments/1.LLM/RAG/Self-RAG.pdf" --json
python3 scripts/aprz.py note-path "Self-RAG" --json
python3 scripts/aprz.py extract-visuals --paper-id "sha256:..." --page 2 --render-page --json
python3 scripts/aprz.py extract-visuals --paper-id "sha256:..." --page 2 --bbox "120,180,960,620" --label "图 1" --caption "Overall architecture." --linked-section method --json
python3 scripts/aprz.py extract-visuals --pdf-path "/path/to/zotero/attachments/1.LLM/RAG/Self-RAG.pdf" --page 2 --bbox "120,180,960,620" --json
python3 scripts/aprz.py render-note --paper-id "sha256:..." --payload "/tmp/note_payload.json"
python3 scripts/aprz.py refresh-index
```

Use `python3` for standard-library commands. In Codex Desktop, when workspace dependencies are available, prefer the bundled workspace Python for `readpack` or other PDF extraction commands because it may include optional extractors such as `pypdf`.

Core commands for scanning, matching, mirrored note paths, note rendering, and index refresh use Python standard library only. Full-library `scan` is incremental by default: it reuses an existing content fingerprint when a PDF's relative path, size, and modified time are unchanged. Use `scan --force-hash` only when a full integrity rebuild is needed.

For a single Zotero-resolved attachment, prefer `index-pdf --pdf-path` instead of `scan`. It validates that the PDF is under `zotero_attachment_root`, updates only that paper in `paper_index.json`, and avoids traversing the entire attachment library.

Full-text PDF extraction is optional: `readpack` tries tools already available in the environment in this order: `pypdf`, `pdfplumber`, then `pdftotext`.

Visual extraction depends on optional tools but is a normal HTML note step when those tools are available: `extract-visuals` uses Poppler `pdfinfo`/`pdftoppm` to render a selected page and Pillow to crop an explicit `--bbox x1,y1,x2,y2` after the page has been inspected. It writes final cropped figure assets under `<notes_root>/assets/papers/<paper_id>/images/` and visual metadata under `<notes_root>/data/visuals/<paper_id>/visuals.json`. Use `--render-page` first when a page preview is needed before choosing the crop box.

Do not install optional tooling such as `pytest`, PyYAML, Poppler, Pillow, `pypdf`, `pdfplumber`, or `pdftotext` without explicit user approval. Missing optional tools should degrade the workflow or be reported as an environment limitation.

If no extractor is available, `readpack` returns `extraction_status: "no_extractor_available"`. Use metadata/path-only mode in that state and do not claim to have read the full PDF.

If Zotero indexed full text returns 404 or is unavailable but Zotero returns a local PDF attachment path, prefer direct PDF readpack fallback:

```text
python3 scripts/aprz.py index-pdf --pdf-path "/absolute/path/under/zotero_attachment_root/Paper.pdf" --json
python3 scripts/aprz.py readpack --pdf-path "/absolute/path/under/zotero_attachment_root/Paper.pdf" --json
```

This path must be inside the configured `zotero_attachment_root`. If it is outside, stop and report the rejection instead of reading arbitrary PDFs.

For Zotero discovery/access, use Python commands automatically when they operate on a specific Zotero-returned local PDF path or a user-provided PDF path inside `zotero_attachment_root`. Keep `scan` and broad `find` as fallback discovery commands only when Zotero-first discovery fails or the user asks to search the configured attachment root. `render-note` and `refresh-index` are normal deterministic note-output commands after the paper/content has already been resolved.

## References

Load only what the task needs:

- `references/metadata-schema.md`: config, index, readpack, and note payload schemas.
- `references/note-writing-guide.md`: Chinese HTML note content contract and writing style.
- `references/zotero-attachment-policy.md`: Zotero safety boundary and stop conditions.

## Configuration

Resolve `zotero_attachment_root` and `notes_root` in this order:

1. Explicit paths or config path from the current request or command.
2. `APRZ_CONFIG_PATH`.
3. Current directory `.auto-paper-reader/config.json`.
4. `~/.config/auto-paper-reader-for-zotero/config.json`.
5. `APRZ_ZOTERO_ATTACHMENT_ROOT` and `APRZ_NOTES_ROOT`.
6. If still missing, stop and ask the user for both paths.

On first use, if config is missing, ask the user for both paths and run `init --scope global` so later Codex sessions and working directories can reuse `~/.config/auto-paper-reader-for-zotero/config.json`. Use `init --scope project` only when the user wants a workspace-specific override in `.auto-paper-reader/config.json`.

Use `init` to save config, create the notes data directories, run a first scan, and write an initial `index.html`. If the user provides both roots and asks to initialize the note system, treat that as approval for this initial scan. A future CLI may add `--no-scan`, but this version does not implement it.

## Zotero-First Resolution

When the user refers to a Zotero collection, category, saved item, paper title, attachment, PDF, or Zotero-indexed full text, start with the Codex Zotero plugin, Zotero local API, or equivalent Codex-side Zotero capability.

Use the Zotero route first:

- Check Zotero readiness/status before scanning attachment folders.
- Use Zotero collections and item search to locate candidates.
- Inspect child attachments for the selected item.
- Retrieve the local PDF file URL/path from Zotero when available.
- Read Zotero-indexed full text when the user asks for paper contents and Zotero can provide it.
- If indexed full text fails with 404 but Zotero returns a usable local PDF path, run `index-pdf --pdf-path` and `readpack --pdf-path` directly.
- Do not run attachment-root scanning if Zotero already returns a usable PDF path or indexed full text.

Keep Zotero as read-only for this skill. Enabling or restarting Zotero's local API, importing records, or writing to Zotero requires explicit user confirmation.

Automatic local PDF fallback is allowed when Zotero returns a local PDF path, the user provides a PDF path inside `zotero_attachment_root`, Zotero indexed full text is unavailable, or visual evidence is needed from that resolved PDF. Whole-library `scan` or broad attachment-root `find` remains a discovery fallback only when Zotero plugin/local API access is unavailable, Zotero Desktop is not running and the user does not want to enable/restart it, Zotero search cannot find the requested paper, Zotero finds the item but cannot return a local PDF attachment path, or Zotero returns ambiguous candidates and the user chooses attachment-root search instead.

Before using whole-library `scan` or broad attachment-root `find`, stop and ask unless the user already requested root-level indexing/search. For a specific PDF path inside `zotero_attachment_root`, do not ask before running `doctor`, `index-pdf`, `readpack --pdf-path`, `note-path`, or `extract-visuals`; run only the minimum necessary commands and report which route was used.

The scripts remain the deterministic layer for config, path scanning, matching, reading packs, mirrored note paths, visual crops, note rendering, backups, and index refresh.

## Workflow

When the user asks to read a Zotero paper or generate a local paper note:

1. Check Zotero readiness/status and use Zotero collections/search for any collection, item, attachment, title, or PDF request.
2. Inspect the selected Zotero item's child attachments and retrieve a local PDF file URL/path when available.
3. Use Zotero-indexed full text for paper contents when available and requested.
4. If Zotero returns multiple plausible papers, show candidates and ask the user to choose. Do not guess.
5. If Zotero indexed full text is unavailable or returns 404 but a local PDF path is available, run `index-pdf --pdf-path` and `readpack --pdf-path`; do not scan the attachment root for discovery.
6. If Zotero-first discovery fails and root-level discovery is needed, ask before running whole-library `scan` or broad `find`. For a resolved local PDF path, continue automatically with the best available PDF/text route.
7. If extraction/full text is unavailable or failed, continue only with metadata/path-level evidence and state the limitation.
8. When Zotero or the user provides a local PDF path for a specific paper, run `index-pdf --pdf-path` before rendering so the paper exists in `paper_index.json` without a full scan.
9. Run `doctor` and attempt method architecture visual extraction when generating an HTML note. If visual tools are available, locate likely figure pages from user hints, captions, section text, or early method pages; run `extract-visuals --page N --render-page`, inspect the rendered page, then rerun with `--page N --bbox x1,y1,x2,y2`. Add useful crops to `visuals`; if no useful figure is found or tools are unavailable, state that limitation in `evidence_basis`.
10. Write a structured note payload following `references/note-writing-guide.md`. Use Markdown-like strings for better HTML note layout when helpful.
11. Run `render-note` to write the standalone HTML note and refresh `note_index.json` and `index.html`. `render-note` does not run a full attachment scan.
12. Report the note path, index path, validation performed, which Zotero/indexed-text/local-PDF route was used, and any extraction limitations.

## Safety Rules

- Do not write to, move, rename, delete, or reorganize files under `zotero_attachment_root`.
- Do not read or modify Zotero SQLite.
- Do not modify the Zotero library through plugin/API actions unless the user explicitly asks and confirms the exact write.
- Do not silently switch from Zotero plugin/local API access to Python attachment-root scanning.
- Ask before whole-library attachment-root scanning/search when no specific Zotero item or local PDF path is known.
- Do not upload PDF contents unless the user explicitly asks and approves.
- Write only inside `notes_root`; reject paths that escape through absolute paths, `..`, or symlinks.
- Render note images only from paths inside `notes_root`; skip outside paths instead of embedding them.
- Back up an existing HTML note inside `notes_root/data/backups/` before replacing it.
- If a PDF disappears, mark it `source_missing`; do not delete the note.
- Stop when config is missing, the target path is outside `notes_root`, a local PDF path is outside `zotero_attachment_root`, a destructive Zotero operation is requested, or PDF extraction failed but the user asks for a full-text conclusion.

## Output Contract

Single notes are standalone HTML files mirroring the PDF relative path:

```text
<zotero_attachment_root>/1.LLM/RAG/Self-RAG.pdf
<notes_root>/1.LLM/RAG/Self-RAG.html
```

The main index is:

```text
<notes_root>/index.html
```

The index is static HTML/CSS/JavaScript and supports local browser use without a server.
