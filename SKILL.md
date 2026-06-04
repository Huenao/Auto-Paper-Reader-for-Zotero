---
name: auto-paper-reader-for-zotero
description: Use for Zotero-managed local PDF attachment roots when Codex needs to scan papers, match a requested paper, build reading packs, generate standalone Chinese HTML paper notes, and refresh a local static note index without modifying Zotero files.
---

# Auto-Paper-Reader-for-Zotero

Use this skill to add an AI note layer on top of a Zotero PDF attachment folder. Treat the Zotero attachment root as read-only. Write only under the configured `notes_root`.

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

When the user refers to a Zotero collection, category, saved item, paper title, attachment, or Zotero-indexed full text, first check whether a Zotero plugin, Zotero local API, or equivalent Codex-side Zotero capability is available in the current session.

If available, use that Zotero capability first for discovery: list collections, search Zotero items, inspect child attachments, retrieve a local attachment file URL/path, or read Zotero-indexed full text when the user asked for paper contents. Keep Zotero as read-only for this skill. Enabling or restarting Zotero's local API, importing records, or writing to Zotero requires explicit user confirmation.

If Zotero capability is unavailable, Zotero Desktop is not running, local API access is disabled, no matching attachment exists, or no local PDF path/full text can be retrieved, fall back to the bundled scripts. The scripts remain the deterministic layer for config, path scanning, matching, reading packs, mirrored note paths, note rendering, backups, and index refresh.

## Workflow

When the user asks to read a Zotero paper or generate a local paper note:

1. Try Zotero-first resolution when the request names a collection, Zotero item, attachment, or title that may be resolved through Zotero. Use the resulting local PDF path or indexed full text only if it is actually available.
2. Load config; run `doctor` if paths or tools are uncertain.
3. Run `scan` if `paper_index.json` is missing or stale, or when Zotero-first resolution did not provide a usable local PDF path.
4. Use `find` or `readpack` to resolve the requested paper from the configured attachment root. If Zotero-first produced an absolute PDF path under `zotero_attachment_root`, pass that path to the script.
5. If multiple candidates match, show candidates and ask the user to choose. Do not guess.
6. Read the reading pack and available extracted text or Zotero-indexed full text. If extraction/full text is unavailable or failed, continue only with metadata/path-level evidence and state the limitation.
7. Write a structured note payload following `references/note-writing-guide.md`.
8. Run `render-note` to write the standalone HTML note.
9. Let `render-note` refresh `note_index.json` and `index.html`.
10. Report the note path, index path, validation performed, and any extraction limitations.

## Safety Rules

- Do not write to, move, rename, delete, or reorganize files under `zotero_attachment_root`.
- Do not read or modify Zotero SQLite.
- Do not modify the Zotero library through plugin/API actions unless the user explicitly asks and confirms the exact write.
- Do not upload PDF contents unless the user explicitly asks and approves.
- Write only inside `notes_root`; reject paths that escape through absolute paths, `..`, or symlinks.
- Back up an existing HTML note inside `notes_root/data/backups/` before replacing it.
- If a PDF disappears, mark it `source_missing`; do not delete the note.
- Stop when config is missing, the target path is outside `notes_root`, a destructive Zotero operation is requested, or PDF extraction failed but the user asks for a full-text conclusion.

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
