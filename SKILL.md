---
name: auto-paper-reader-for-zotero
description: Use for Zotero-managed local PDF attachment roots when Codex needs to scan papers, match a requested paper, build reading packs, generate standalone Chinese HTML paper notes, and refresh a local static note index without modifying Zotero files.
---

# Auto-Paper-Reader-for-Zotero

Use this skill to add an AI note layer on top of a Zotero PDF attachment folder. Treat the Zotero attachment root as read-only. Write only under the configured `notes_root`.

## Script

Resolve paths from this skill directory. Use the unified CLI:

```text
python3 scripts/aprz.py init --zotero-attachment-root "/path/to/zotero/attachments" --notes-root "/path/to/ai/paper-notes"
python3 scripts/aprz.py doctor
python3 scripts/aprz.py scan
python3 scripts/aprz.py find "Self-RAG"
python3 scripts/aprz.py readpack "Self-RAG" --json
python3 scripts/aprz.py note-path "Self-RAG" --json
python3 scripts/aprz.py render-note --paper-id "sha256:..." --payload "/tmp/note_payload.json"
python3 scripts/aprz.py refresh-index
```

PDF text extraction tries only tools already available in the environment: `pypdf`, `pdfplumber`, then `pdftotext`. If none are available, `readpack` returns `extraction_status: "no_extractor_available"` and Codex must not claim to have read the full PDF.

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

Use `init` to create a project config, create the notes data directories, run a first scan, and write an initial `index.html`.

## Workflow

When the user asks to read a Zotero paper or generate a local paper note:

1. Load config; run `doctor` if paths or tools are uncertain.
2. Run `scan` if `paper_index.json` is missing or stale.
3. Use `find` or `readpack` to resolve the requested paper.
4. If multiple candidates match, show candidates and ask the user to choose. Do not guess.
5. Read the reading pack and available extracted text.
6. Write a structured note payload following `references/note-writing-guide.md`.
7. Run `render-note` to write the standalone HTML note.
8. Let `render-note` refresh `note_index.json` and `index.html`.
9. Report the note path, index path, validation performed, and any extraction limitations.

## Safety Rules

- Do not write to, move, rename, delete, or reorganize files under `zotero_attachment_root`.
- Do not read or modify Zotero SQLite.
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
