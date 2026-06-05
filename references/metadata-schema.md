# Metadata Schema

Use these schemas as the stable contract between scripts and Codex-authored content.

## Config

Project config lives at `.auto-paper-reader/config.json`; global config may live at `~/.config/auto-paper-reader-for-zotero/config.json`.

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

## paper_index.json

Stored at `<notes_root>/data/paper_index.json`.

Required top-level fields:

- `schema_version`: integer, currently `1`
- `generated_at`: ISO 8601 timestamp
- `zotero_attachment_root`: absolute path string
- `notes_root`: absolute path string
- `summary`: scan counts
- `items`: paper entries

Required item fields:

- `paper_id`: `sha256:<hex>`
- `pdf_abs_path`
- `pdf_rel_path`
- `category_path`
- `filename`
- `file_stem`
- `title_guess`
- `authors_guess`
- `year_guess`
- `file_size`
- `modified_at`
- `content_fingerprint`
- `note_rel_path`
- `note_exists`
- `note_updated_at`
- `status`: `read` or `unread`
- `tags`
- `source_status`: `available` or `source_missing`

## note_index.json

Stored at `<notes_root>/data/note_index.json` and embedded into `<notes_root>/index.html`.

Each item should include:

- `paper_id`
- `title`
- `authors`
- `year`
- `venue`
- `pdf_rel_path`
- `pdf_href`
- `note_rel_path`
- `note_href`
- `category_path`
- `tags`
- `status`
- `source_status`
- `summary`
- `updated_at`

Optional dashboard fields may also be present. They are display-only enhancements and must not be required for old notes:

- `research_area`
- `primary_subtopic`
- `priority`
- `reading_status`
- `evidence_basis`
- `problem_preview`
- `method_preview`
- `findings_preview`
- `value_preview`
- `next_action`

## Reading Pack

`readpack` returns a machine-readable structure for Codex:

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
  "sections": [],
  "full_text_path": "<notes_root>/data/extracted_text/sha256....txt",
  "extraction_status": "ok",
  "source_resolution": "query_match",
  "recommended_reading_order": [
    "abstract",
    "introduction",
    "method",
    "experiments",
    "limitations"
  ]
}
```

Allowed `extraction_status`: `ok`, `partial`, `no_extractor_available`, `pdf_unreadable`, `failed`.

Allowed `source_resolution` values:

- `query_match`: matched from `paper_index.json` using a title, filename, relative path, or fragment query.
- `direct_pdf_path`: built directly from a local PDF path under `zotero_attachment_root`, usually after Zotero indexed full text failed but Zotero returned a local attachment path.

## Visual Extraction

`extract-visuals` returns optional local figure/table evidence. It must not be required for old notes.

```json
{
  "visual_extraction_status": "ok",
  "paper_id": "sha256:...",
  "pdf_abs_path": "...",
  "visuals_json_path": "<notes_root>/data/visuals/sha256....json",
  "visuals": [
    {
      "label": "图 1",
      "label_original": "Figure 1",
      "caption": "Overall architecture.",
      "caption_zh": "",
      "page": 3,
      "asset_path": "<notes_root>/assets/papers/sha256.../images/figure-001.png",
      "image_scale": 3.0,
      "visual_type": "figure",
      "crop_status": "exported_with_docling",
      "evidence_summary": "展示方法的两阶段处理流程。",
      "linked_section": "method"
    }
  ]
}
```

Allowed `visual_extraction_status`: `ok`, `no_visuals_found`, `no_visual_extractor_available`, `outside_attachment_root`, `pdf_not_found`, `not_pdf`, `failed`, `paper_not_found`.

Only `asset_path` values inside `notes_root` should be rendered in notes. Outside paths must be skipped by the renderer.

## Note Payload

Codex writes this JSON payload before `render-note`:

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
  "visuals": [],
  "follow_up_questions": ["..."],
  "tags": [],
  "status": "read"
}
```

Optional Paper Vault-style display fields are supported:

```json
{
  "research_area": "RAG",
  "primary_subtopic": "Self-Reflection",
  "priority": "High",
  "reading_status": "fulltext-read",
  "evidence_basis": "Zotero indexed full text",
  "next_action": "Compare retrieval triggers against ReAct-style agents."
}
```

These optional fields improve the standalone note header and the local index dashboard. Do not make them mandatory; older payloads should continue to render with safe defaults.

Optional `visuals` entries may be copied from `extract-visuals` output and edited by Codex after inspecting the images:

```json
{
  "visuals": [
    {
      "label": "图 1",
      "caption": "Overall architecture.",
      "page": 3,
      "asset_path": "/absolute/path/inside/notes_root/assets/papers/sha256.../images/figure-001.png",
      "visual_type": "figure",
      "evidence_summary": "图中把检索、生成和 critique 串成闭环，说明该方法不是单次 RAG 调用。",
      "linked_section": "method"
    }
  ]
}
```

Body text fields such as `problem`, `method_overview`, `pipeline`, `experiments`, `findings`, `limitations`, and `value_for_user` may use lightweight Markdown-like formatting inside strings: paragraphs, `-` bullets, `1.` ordered lists, `>` callouts, and simple pipe tables. The renderer escapes text before producing HTML.
