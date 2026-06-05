# Note Writing Guide

Write notes in Chinese technical prose unless the user asks otherwise. Keep raw titles, author names, venues, and mathematical notation in their original language when that is clearer.

## Required Sections

Every rendered note payload should cover:

- one-sentence summary
- problem the paper solves
- method overview
- method pipeline
- key innovations
- experimental setup
- main findings
- limitations
- value for the user's research direction
- follow-up questions

## Style

- Prefer concrete mechanisms over generic praise.
- Explain inputs, outputs, modules, data flow, training or inference steps, and failure handling when the paper describes a method.
- Do not claim full-text understanding when `extraction_status` is not `ok` or when Codex only saw partial text.
- Mention uncertainty explicitly when evidence is missing.
- Avoid boilerplate headings copied blindly across papers when the paper needs more specific phrasing.

## Payload Rules

- Keep `summary` short enough for the index.
- Use arrays for `authors`, `innovations`, `follow_up_questions`, and `tags`.
- Set `status` to `read` when a substantive note has been generated.
- Preserve `paper_id` from the reading pack or `paper_index.json`.
- Add optional `research_area`, `primary_subtopic`, `priority`, `reading_status`, `evidence_basis`, and `next_action` when the source evidence supports them.
- Keep optional dashboard fields concise; they are for scanning and filtering the local HTML index, not for replacing the full note sections.
- Leave optional fields absent when uncertain. The renderer provides defaults and old payloads remain valid.
