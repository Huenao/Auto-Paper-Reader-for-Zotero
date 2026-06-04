# Zotero Attachment Policy

Zotero remains the source of truth for paper items, attachments, and metadata. This skill only creates AI-generated notes and indexes.

## Allowed

- Read PDF files under the configured `zotero_attachment_root`.
- Scan relative PDF paths and file metadata.
- Generate notes and indexes under `notes_root`.
- Link from notes back to local PDF files.
- Mark missing PDFs as `source_missing`.

## Forbidden Without Explicit User Authorization

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
- a user requests destructive changes to Zotero files;
- multiple paper candidates match and no exact choice was supplied;
- PDF extraction failed but the user asks for a confident full-text conclusion.
