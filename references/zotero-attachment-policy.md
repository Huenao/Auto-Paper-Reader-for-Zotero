# Zotero Attachment Policy

Zotero remains the source of truth for paper items, attachments, and metadata. This skill only creates AI-generated notes and indexes.

Prefer Codex's Zotero plugin or Zotero local API for collection, item, attachment, local PDF path, and indexed full-text access. Python attachment-root scanning is slower and must be treated as a fallback, not the default route.

## Allowed

- Read PDF files under the configured `zotero_attachment_root`.
- Scan relative PDF paths and file metadata.
- Generate notes and indexes under `notes_root`.
- Link from notes back to local PDF files.
- Mark missing PDFs as `source_missing`.

## Forbidden Without Explicit User Authorization

- Silently switch from Zotero plugin/local API access to Python attachment-root scanning.
- Use `doctor`, `scan`, `find`, `readpack`, `note-path`, `index-pdf`, or `extract-visuals` as fallback access commands after Zotero-first failure.
- Modify Zotero SQLite.
- Write files into the Zotero attachment root.
- Move, rename, delete, or reorganize Zotero PDFs.
- Delete generated notes because a PDF disappeared.
- Upload PDF contents to external services.
- Create destructive migrations or cleanup jobs.

## Stop Conditions

Stop and ask the user when:

- config is missing and cannot be inferred from command arguments;
- a computed note path escapes `notes_root`;
- Zotero-first access fails and fallback scanning, matching, single-PDF indexing, reading-pack creation, visual extraction, or note-path lookup is needed;
- a user requests destructive changes to Zotero files;
- multiple paper candidates match and no exact choice was supplied;
- PDF extraction failed but the user asks for a confident full-text conclusion.
