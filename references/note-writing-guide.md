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
- Use Markdown-like structure inside body strings when it improves scanning: bullets for parallel points, ordered lists for pipelines, `>` callouts for key intuitions, and simple pipe tables for compact experiment comparisons.

## Payload Rules

- Keep `summary` short enough for the index.
- Use arrays for `authors`, `innovations`, `follow_up_questions`, and `tags`.
- Set `status` to `read` when a substantive note has been generated.
- Preserve `paper_id` from the reading pack or `paper_index.json`.
- Add optional `research_area`, `primary_subtopic`, `priority`, `reading_status`, `evidence_basis`, and `next_action` when the source evidence supports them.
- Keep optional dashboard fields concise; they are for scanning and filtering the local HTML index, not for replacing the full note sections.
- Leave optional fields absent when uncertain. The renderer provides defaults and old payloads remain valid.

## Reproducibility Resources

Add optional `resources` only for code, project, dataset, benchmark, or model links that are explicitly visible in the paper text/readpack or supplied by the user. Do not search the web or guess links from paper titles.

- Use `type` values: `code`, `project`, `dataset`, `benchmark`, `model`, or `other`.
- Use `source` to cite where the link came from, such as `abstract footnote`, `method section`, `experiments section`, `appendix`, or `user provided`.
- Use `note` to explain what the resource is for, such as `官方代码实现`, `训练数据下载页`, or `评测 benchmark 页面`.
- If a dataset is named but no URL is provided, mention the dataset in `experiments`; do not add a `resources` entry.
- Omit `resources` entirely when no explicit links are available.

## Visual Evidence

For new HTML paper notes, attempt method or architecture visual evidence when Poppler and Pillow are available. Use `visuals` only when local visual extraction produced useful figure assets and the image was inspected; otherwise state the limitation in `evidence_basis` when it matters for the note.

- Keep `visuals[].asset_path` inside `notes_root`; outside paths are skipped by the renderer.
- Prefer one to three high-value visuals over dumping every extracted figure.
- Write `evidence_summary` as the insight the reader should take from the image and how it supports the nearby section text, not just `图 1 展示了方法流程`.
- Use `linked_section` to control where the visual is embedded: `method`, `pipeline`, `experiments`, `findings`, or `limitations`. Unknown or missing values are rendered in a final "其他图表证据" section.
- For method architecture figures, prefer `linked_section: "method"` when the image explains components or design rationale, and `linked_section: "pipeline"` when it explains execution flow.
- For method architecture figures, render and inspect the likely page first, then crop with an explicit bbox. Do not include the crop unless it was visually inspected.
- If Poppler or Pillow is unavailable, or no useful architecture figure is found after inspection, omit `visuals` and state the limitation in `evidence_basis` only when relevant.

Example:

```json
{
  "method_overview": "> 关键直觉：模型先判断是否需要检索，再用反思信号评价生成结果。\n\n- 检索触发由特殊 token 控制\n- 生成后再评估事实性与支持度",
  "pipeline": "1. 判断是否需要检索\n2. 检索相关证据\n3. 生成答案\n4. 用 critique token 评估答案",
  "visuals": [
    {
      "label": "图 1",
      "caption": "Overview of Self-RAG.",
      "page": 3,
      "bbox": [120, 180, 960, 620],
      "asset_path": "/path/inside/notes_root/assets/papers/sha256.../images/figure-001-p003.png",
      "visual_type": "figure",
      "linked_section": "method",
      "evidence_summary": "这张图把检索、生成和自我评价连接成一个推理闭环，解释了方法为什么能减少不必要检索。"
    }
  ]
}
```
