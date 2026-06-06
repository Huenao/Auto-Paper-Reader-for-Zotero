#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable
from urllib.parse import urlparse

from config import APRZConfig, data_dir, ensure_notes_layout
from path_utils import PathSafetyError, path_to_file_href, require_within_root, safe_id_filename
from render_index import refresh_index, skill_root
from scan_pdfs import load_paper_index


REQUIRED_PAYLOAD_FIELDS = [
    "paper_id",
    "title",
    "summary",
    "problem",
    "method_overview",
    "pipeline",
    "experiments",
    "findings",
    "limitations",
    "value_for_user",
]


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _find_item(cfg: APRZConfig, paper_id: str) -> Dict[str, object]:
    index = load_paper_index(cfg)
    for item in index.get("items", []):
        if item.get("paper_id") == paper_id:
            return item
    raise ValueError(f"paper_id not found in paper_index.json: {paper_id}")


def _render_list(values: Iterable[object]) -> str:
    items = [f"<li>{html.escape(str(value))}</li>" for value in values if str(value).strip()]
    return '<ul class="note-list">' + "".join(items) + "</ul>" if items else "<p></p>"


def _render_text(value: object) -> str:
    if isinstance(value, list):
        return _render_list(value)
    return _render_markdown_like(str(value or ""))


def _render_markdown_like(text: str) -> str:
    blocks = _split_blocks(text)
    rendered = [_render_markdown_block(block) for block in blocks]
    return "".join(block for block in rendered if block) or "<p></p>"


def _split_blocks(text: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.strip():
            current.append(line.rstrip())
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def _render_markdown_block(lines: list[str]) -> str:
    stripped = [line.strip() for line in lines if line.strip()]
    if not stripped:
        return ""
    if _is_table_block(stripped):
        return _render_table(stripped)
    if all(re.match(r"^[-*]\s+\S", line) for line in stripped):
        items = [re.sub(r"^[-*]\s+", "", line) for line in stripped]
        return _render_list(items)
    if all(re.match(r"^\d+[.)]\s+\S", line) for line in stripped):
        items = [re.sub(r"^\d+[.)]\s+", "", line) for line in stripped]
        return '<ol class="note-list ordered">' + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ol>"
    if all(line.startswith(">") for line in stripped):
        body = " ".join(line.lstrip(">").strip() for line in stripped)
        return f'<blockquote class="note-callout"><p>{html.escape(body)}</p></blockquote>'
    return "".join(f"<p>{html.escape(line)}</p>" for line in stripped)


def _is_table_block(lines: list[str]) -> bool:
    return (
        len(lines) >= 2
        and all(line.startswith("|") and line.endswith("|") for line in lines)
        and all(set(cell.strip()) <= {"-", ":"} for cell in lines[1].strip("|").split("|"))
    )


def _render_table(lines: list[str]) -> str:
    header = [cell.strip() for cell in lines[0].strip("|").split("|")]
    rows = [[cell.strip() for cell in line.strip("|").split("|")] for line in lines[2:]]
    head_html = "".join(f"<th>{html.escape(cell)}</th>" for cell in header)
    row_html = []
    for row in rows:
        cells = row + [""] * max(0, len(header) - len(row))
        row_html.append("<tr>" + "".join(f"<td>{html.escape(cell)}</td>" for cell in cells[: len(header)]) + "</tr>")
    return '<table class="note-table"><thead><tr>' + head_html + "</tr></thead><tbody>" + "".join(row_html) + "</tbody></table>"


def _plain_text(value: object) -> str:
    if isinstance(value, list):
        return " / ".join(str(item).strip() for item in value if str(item).strip())
    return " ".join(str(value or "").split())


def _format_authors(authors: object) -> str:
    if isinstance(authors, list):
        return html.escape(", ".join(str(author) for author in authors))
    return html.escape(str(authors or ""))


def _render_chip(label: str, value: object) -> str:
    text = _plain_text(value)
    if not text:
        return ""
    return (
        '<span class="meta-chip">'
        f"<span>{html.escape(label)}</span>"
        f"<strong>{html.escape(text)}</strong>"
        "</span>"
    )


def _render_meta_chips(values: Iterable[tuple[str, object]]) -> str:
    chips = [_render_chip(label, value) for label, value in values]
    return "".join(chip for chip in chips if chip)


def _render_tag_chips(values: object) -> str:
    if not isinstance(values, list):
        return ""
    chips = [
        f'<span class="tag-chip">{html.escape(str(value))}</span>'
        for value in values
        if str(value).strip()
    ]
    return "".join(chips)


def _first_nonempty(*values: object) -> str:
    for value in values:
        text = _plain_text(value)
        if text:
            return text
    return ""


VISUAL_SECTION_KEYS = {"method", "pipeline", "experiments", "findings", "limitations"}


def _render_visual_groups(cfg: APRZConfig, note_path: Path, visuals: object) -> Dict[str, str]:
    groups = {key: "" for key in VISUAL_SECTION_KEYS}
    groups["other"] = ""
    if not isinstance(visuals, list):
        return groups
    for item in visuals:
        if not isinstance(item, dict):
            continue
        linked_section = str(item.get("linked_section") or "").strip().casefold()
        target = linked_section if linked_section in VISUAL_SECTION_KEYS else "other"
        groups[target] += _render_visual_item(cfg, note_path, item)
    return groups


def _render_other_visuals(body: str) -> str:
    if not body:
        return ""
    return '<section id="visuals" class="note-section visual-section"><h2>其他图表证据</h2>' + body + "</section>"


def _render_visual_toc_link(other_visuals_section: str) -> str:
    if not other_visuals_section:
        return ""
    return '<a href="#visuals">其他图表证据</a>'


RESOURCE_TYPE_LABELS = {
    "code": "代码",
    "project": "项目页",
    "dataset": "数据集",
    "benchmark": "Benchmark",
    "model": "模型",
    "other": "其他",
}


def _render_resources(resources: object) -> str:
    if not isinstance(resources, list):
        return ""
    items = []
    for item in resources:
        if not isinstance(item, dict):
            continue
        rendered = _render_resource_item(item)
        if rendered:
            items.append(rendered)
    if not items:
        return ""
    return '<section id="resources" class="note-section resource-section"><h2>开源与数据资源</h2><div class="resource-list">' + "".join(items) + "</div></section>"


def _render_resources_toc_link(resources_section: str) -> str:
    if not resources_section:
        return ""
    return '<a href="#resources">开源与数据资源</a>'


def _render_resource_item(item: Dict[str, object]) -> str:
    href = _safe_resource_href(item.get("url"))
    if not href:
        return ""
    label = _first_nonempty(item.get("label"), item.get("url"), "资源链接")
    resource_type = str(item.get("type") or "other").strip().casefold()
    type_label = RESOURCE_TYPE_LABELS.get(resource_type, RESOURCE_TYPE_LABELS["other"])
    note = _first_nonempty(item.get("note"))
    source = _first_nonempty(item.get("source"))
    note_html = f'<p class="resource-note">{html.escape(note)}</p>' if note else ""
    source_html = f'<p class="resource-source"><span>来源</span>{html.escape(source)}</p>' if source else ""
    return (
        '<article class="paper-resource">'
        '<div class="resource-heading">'
        f'<span class="resource-type">{html.escape(type_label)}</span>'
        f'<a href="{href}" target="_blank" rel="noopener noreferrer">{html.escape(label)}</a>'
        "</div>"
        f"{note_html}{source_html}"
        "</article>"
    )


def _safe_resource_href(url: object) -> str:
    raw = str(url or "").strip()
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return html.escape(raw, quote=True)


def _render_visual_item(cfg: APRZConfig, note_path: Path, item: Dict[str, object]) -> str:
    label = _first_nonempty(item.get("label"), item.get("label_original"), "图表")
    caption = _first_nonempty(item.get("caption_zh"), item.get("caption"))
    page = _first_nonempty(item.get("page"))
    evidence = _first_nonempty(item.get("evidence_summary_zh"), item.get("evidence_summary"))
    heading = html.escape(label)
    if page:
        heading += f'<span class="visual-page">p. {html.escape(page)}</span>'
    asset_path = _safe_visual_href(cfg, note_path, item.get("asset_path"))
    caption_text = caption or evidence or label
    alt = html.escape(" ".join(part for part in [label, caption_text] if part))
    if asset_path:
        media = f'<img src="{asset_path}" alt="{alt}" loading="lazy">'
    else:
        media = '<div class="visual-missing">图片路径被安全策略跳过</div>'
    details = ""
    if caption:
        details += f"<figcaption>{html.escape(caption)}</figcaption>"
    if evidence:
        details += f'<p class="visual-summary">{html.escape(evidence)}</p>'
    return f'<figure class="paper-visual"><div class="visual-heading">{heading}</div>{media}{details}</figure>'


def _safe_visual_href(cfg: APRZConfig, note_path: Path, asset_path: object) -> str:
    if not asset_path:
        return ""
    try:
        path = require_within_root(Path(str(asset_path)), cfg.notes_root)
    except (PathSafetyError, RuntimeError):
        return ""
    if not path.exists() or not path.is_file():
        return ""
    return html.escape(_rel_href(note_path, path))


def _validate_payload(payload: Dict[str, object]) -> None:
    missing = [field for field in REQUIRED_PAYLOAD_FIELDS if field not in payload]
    if missing:
        raise ValueError(f"Missing note payload fields: {', '.join(missing)}")


def _backup_existing(cfg: APRZConfig, note_path: Path, paper_id: str) -> Path | None:
    if not note_path.exists():
        return None
    backup_name = f"{safe_id_filename(paper_id)}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{note_path.name}"
    backup_path = require_within_root(data_dir(cfg) / "backups" / backup_name, cfg.notes_root)
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(note_path, backup_path)
    return backup_path


def render_note(cfg: APRZConfig, payload: Dict[str, object]) -> Dict[str, object]:
    ensure_notes_layout(cfg)
    _validate_payload(payload)
    paper_id = str(payload["paper_id"])
    item = _find_item(cfg, paper_id)
    note_path = require_within_root(cfg.notes_root / str(item["note_rel_path"]), cfg.notes_root)
    note_path.parent.mkdir(parents=True, exist_ok=True)
    backup = _backup_existing(cfg, note_path, paper_id)

    shutil.copyfile(skill_root() / "assets" / "note.css", require_within_root(cfg.notes_root / "assets" / "note.css", cfg.notes_root))

    timestamp = now_iso()
    stored_payload = dict(payload)
    stored_payload.setdefault("tags", [])
    stored_payload["status"] = stored_payload.get("status") or "read"
    stored_payload.setdefault("reading_status", stored_payload["status"])
    stored_payload["updated_at"] = timestamp
    payload_path = require_within_root(data_dir(cfg) / "note_payloads" / (safe_id_filename(paper_id) + ".json"), cfg.notes_root)
    payload_path.write_text(json.dumps(stored_payload, ensure_ascii=False, indent=2) + "\n")

    template = (skill_root() / "assets" / "templates" / "note.html").read_text()
    research_area = _first_nonempty(stored_payload.get("research_area"), item.get("category_path"), "未分类")
    primary_subtopic = _first_nonempty(stored_payload.get("primary_subtopic"), (item.get("category_path") or [])[-1:] if item.get("category_path") else [], "未标注")
    priority = _first_nonempty(stored_payload.get("priority"), "Saved")
    reading_status = _first_nonempty(stored_payload.get("reading_status"), stored_payload.get("status"), "read")
    evidence_basis = _first_nonempty(stored_payload.get("evidence_basis"), "Zotero metadata, local PDF path, or approved extraction evidence")
    next_action = _first_nonempty(stored_payload.get("next_action"))
    visual_groups = _render_visual_groups(cfg, note_path, stored_payload.get("visuals", []))
    other_visuals_section = _render_other_visuals(visual_groups["other"])
    resources_section = _render_resources(stored_payload.get("resources", []))
    context = {
        "title": html.escape(str(stored_payload.get("title") or item.get("title_guess") or item.get("file_stem"))),
        "css_href": _rel_href(note_path, cfg.notes_root / "assets" / "note.css"),
        "index_href": _rel_href(note_path, cfg.notes_root / cfg.index_filename),
        "pdf_action": (
            f'<a class="action-link primary" href="{path_to_file_href(Path(str(item["pdf_abs_path"])))}">打开原 PDF</a>'
            if item.get("source_status") == "available"
            else '<span class="action-link disabled">源 PDF 缺失</span>'
        ),
        "pdf_rel_path": html.escape(str(item.get("pdf_rel_path", ""))),
        "authors": _format_authors(stored_payload.get("authors", [])),
        "year": html.escape(str(stored_payload.get("year") or "")),
        "venue": html.escape(str(stored_payload.get("venue") or "")),
        "summary": html.escape(str(stored_payload.get("summary") or "")),
        "meta_chips": _render_meta_chips(
            [
                ("研究方向", research_area),
                ("主子主题", primary_subtopic),
                ("优先级", priority),
                ("阅读状态", reading_status),
                ("年份", stored_payload.get("year")),
                ("来源", stored_payload.get("venue")),
            ]
        ),
        "tag_chips": _render_tag_chips(stored_payload.get("tags", [])),
        "reading_status": html.escape(reading_status),
        "evidence_basis": html.escape(evidence_basis),
        "research_area": html.escape(research_area),
        "primary_subtopic": html.escape(primary_subtopic),
        "priority": html.escape(priority),
        "problem": _render_text(stored_payload.get("problem")),
        "method_overview": _render_text(stored_payload.get("method_overview")),
        "method_visuals": visual_groups["method"],
        "pipeline": _render_text(stored_payload.get("pipeline")),
        "pipeline_visuals": visual_groups["pipeline"],
        "resources_toc_link": _render_resources_toc_link(resources_section),
        "resources_section": resources_section,
        "innovations": _render_text(stored_payload.get("innovations", [])),
        "experiments": _render_text(stored_payload.get("experiments")),
        "experiments_visuals": visual_groups["experiments"],
        "findings": _render_text(stored_payload.get("findings")),
        "findings_visuals": visual_groups["findings"],
        "limitations": _render_text(stored_payload.get("limitations")),
        "limitations_visuals": visual_groups["limitations"],
        "value_for_user": _render_text(stored_payload.get("value_for_user")),
        "visuals_toc_link": _render_visual_toc_link(other_visuals_section),
        "visuals_section": other_visuals_section,
        "next_action": _render_text(next_action),
        "follow_up_questions": _render_text(stored_payload.get("follow_up_questions", [])),
        "generated_at": timestamp,
        "updated_at": timestamp,
    }
    html_text = template
    for key, value in context.items():
        html_text = html_text.replace("{{ " + key + " }}", str(value))
    note_path.write_text(html_text)

    index_result = refresh_index(cfg)
    return {
        "note_abs_path": str(note_path),
        "backup_abs_path": str(backup) if backup else "",
        "payload_abs_path": str(payload_path),
        "index_abs_path": index_result["index_abs_path"],
    }


def _rel_href(from_file: Path, target: Path) -> str:
    return Path(
        Path(target).resolve().relative_to(Path(from_file).resolve().parent)
    ).as_posix() if _is_parent(Path(target).resolve(), Path(from_file).resolve().parent) else _relative_posix(from_file, target)


def _relative_posix(from_file: Path, target: Path) -> str:
    import os

    return os.path.relpath(str(target.resolve()), str(from_file.resolve().parent)).replace("\\", "/")


def _is_parent(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
