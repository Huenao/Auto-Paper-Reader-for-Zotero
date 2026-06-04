---
name: auto-paper-reader-for-zotero
description: Use for Zotero-managed papers when Codex needs to locate or read Zotero PDFs, prefer the Codex Zotero plugin/local API for collections, items, attachments, local PDF paths, or indexed full text, and generate standalone Chinese HTML paper notes with a local static index. Use the bundled Python scripts only as an approved slow fallback for attachment-root scanning, matching, readpacks, and deterministic note rendering without modifying Zotero files.
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
python3 scripts/aprz.py find "Self-RAG"
python3 scripts/aprz.py readpack "Self-RAG" --json
python3 scripts/aprz.py note-path "Self-RAG" --json
python3 scripts/aprz.py render-note --paper-id "sha256:..." --payload "/tmp/note_payload.json"
python3 scripts/aprz.py refresh-index
```

Core commands for scanning, matching, mirrored note paths, note rendering, and index refresh use Python standard library only. Full-text PDF extraction is optional: `readpack` tries tools already available in the environment in this order: `pypdf`, `pdfplumber`, then `pdftotext`.

If no extractor is available, `readpack` returns `extraction_status: "no_extractor_available"`. Use metadata/path-only mode in that state and do not claim to have read the full PDF.

For Zotero discovery/access, treat `doctor`, `scan`, `find`, `readpack`, and `note-path` as slower Python fallback commands. Use them only after Zotero-first access fails and the user approves fallback for the current task. `render-note` and `refresh-index` are normal deterministic note-output commands after the paper/content has already been resolved.

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

Use `init` to save config, create the notes data directories, run a first scan, and write an initial `index.html`.

## Zotero-First Resolution

When the user refers to a Zotero collection, category, saved item, paper title, attachment, PDF, or Zotero-indexed full text, start with the Codex Zotero plugin, Zotero local API, or equivalent Codex-side Zotero capability.

Use the Zotero route first:

- Check Zotero readiness/status before scanning attachment folders.
- Use Zotero collections and item search to locate candidates.
- Inspect child attachments for the selected item.
- Retrieve the local PDF file URL/path from Zotero when available.
- Read Zotero-indexed full text when the user asks for paper contents and Zotero can provide it.
- Do not run attachment-root scanning if Zotero already returns a usable PDF path or indexed full text.

Keep Zotero as read-only for this skill. Enabling or restarting Zotero's local API, importing records, or writing to Zotero requires explicit user confirmation.

Python fallback is allowed only when Zotero plugin/local API access is unavailable, Zotero Desktop is not running and the user does not want to enable/restart it, Zotero search cannot find the requested paper, Zotero finds the item but cannot return a local PDF attachment path, Zotero full text is unavailable and PDF text extraction is still needed, or Zotero returns ambiguous candidates and the user chooses attachment-root search instead.

Before using `doctor`, `scan`, `find`, `readpack`, or `note-path` for fallback access, stop and ask the user whether to use the slower Python attachment-root fallback. Explain the Zotero-first failure and name the intended command category, such as "scan the configured attachment root" or "build a reading pack from the local PDF." Once approved for that paper/task, run only the minimum necessary fallback commands.

The scripts remain the deterministic layer for config, approved path scanning, matching, reading packs, mirrored note paths, note rendering, backups, and index refresh. `render-note` and `refresh-index` do not need a separate fallback-access approval after the paper/content has been resolved and the user asked to generate or update a note.

## Workflow

When the user asks to read a Zotero paper or generate a local paper note:

1. Check Zotero readiness/status and use Zotero collections/search for any collection, item, attachment, title, or PDF request.
2. Inspect the selected Zotero item's child attachments and retrieve a local PDF file URL/path when available.
3. Use Zotero-indexed full text for paper contents when available and requested.
4. If Zotero returns multiple plausible papers, show candidates and ask the user to choose. Do not guess.
5. If Zotero provides a usable local PDF path or indexed full text, do not scan the attachment root for discovery.
6. If Zotero-first access fails and fallback discovery or PDF extraction is needed, ask the user before running `doctor`, `scan`, `find`, `readpack`, or `note-path`. After approval, run only the minimum necessary fallback commands.
7. If extraction/full text is unavailable or failed, continue only with metadata/path-level evidence and state the limitation.
8. Write a structured note payload following `references/note-writing-guide.md`.
9. Run `render-note` to write the standalone HTML note and refresh `note_index.json` and `index.html`.
10. Report the note path, index path, validation performed, whether Zotero or approved Python fallback was used, and any extraction limitations.

## Safety Rules

- Do not write to, move, rename, delete, or reorganize files under `zotero_attachment_root`.
- Do not read or modify Zotero SQLite.
- Do not modify the Zotero library through plugin/API actions unless the user explicitly asks and confirms the exact write.
- Do not silently switch from Zotero plugin/local API access to Python attachment-root scanning.
- Ask before using `doctor`, `scan`, `find`, `readpack`, or `note-path` as slow fallback access commands.
- Do not upload PDF contents unless the user explicitly asks and approves.
- Write only inside `notes_root`; reject paths that escape through absolute paths, `..`, or symlinks.
- Back up an existing HTML note inside `notes_root/data/backups/` before replacing it.
- If a PDF disappears, mark it `source_missing`; do not delete the note.
- Stop when config is missing, the target path is outside `notes_root`, Zotero-first access failed and fallback access has not been approved, a destructive Zotero operation is requested, or PDF extraction failed but the user asks for a full-text conclusion.

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
