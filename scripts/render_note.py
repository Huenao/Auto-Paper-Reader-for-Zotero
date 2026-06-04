#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable

from config import APRZConfig, data_dir, ensure_notes_layout
from path_utils import path_to_file_href, require_within_root, safe_id_filename
from render_index import refresh_index, skill_root
from scan_pdfs import load_paper_index, scan_pdfs


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
    return "<ul>" + "".join(items) + "</ul>" if items else "<p></p>"


def _render_text(value: object) -> str:
    if isinstance(value, list):
        return _render_list(value)
    paragraphs = [part.strip() for part in str(value or "").split("\n") if part.strip()]
    return "".join(f"<p>{html.escape(part)}</p>" for part in paragraphs) or "<p></p>"


def _format_authors(authors: object) -> str:
    if isinstance(authors, list):
        return html.escape(", ".join(str(author) for author in authors))
    return html.escape(str(authors or ""))


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
    stored_payload["updated_at"] = timestamp
    payload_path = require_within_root(data_dir(cfg) / "note_payloads" / (safe_id_filename(paper_id) + ".json"), cfg.notes_root)
    payload_path.write_text(json.dumps(stored_payload, ensure_ascii=False, indent=2) + "\n")

    template = (skill_root() / "assets" / "templates" / "note.html").read_text()
    context = {
        "title": html.escape(str(stored_payload.get("title") or item.get("title_guess") or item.get("file_stem"))),
        "css_href": _rel_href(note_path, cfg.notes_root / "assets" / "note.css"),
        "index_href": _rel_href(note_path, cfg.notes_root / cfg.index_filename),
        "pdf_href": path_to_file_href(Path(str(item["pdf_abs_path"]))) if item.get("source_status") == "available" else "",
        "pdf_rel_path": html.escape(str(item.get("pdf_rel_path", ""))),
        "authors": _format_authors(stored_payload.get("authors", [])),
        "year": html.escape(str(stored_payload.get("year") or "")),
        "venue": html.escape(str(stored_payload.get("venue") or "")),
        "summary": html.escape(str(stored_payload.get("summary") or "")),
        "problem": _render_text(stored_payload.get("problem")),
        "method_overview": _render_text(stored_payload.get("method_overview")),
        "pipeline": _render_text(stored_payload.get("pipeline")),
        "innovations": _render_text(stored_payload.get("innovations", [])),
        "experiments": _render_text(stored_payload.get("experiments")),
        "findings": _render_text(stored_payload.get("findings")),
        "limitations": _render_text(stored_payload.get("limitations")),
        "value_for_user": _render_text(stored_payload.get("value_for_user")),
        "follow_up_questions": _render_text(stored_payload.get("follow_up_questions", [])),
        "generated_at": timestamp,
        "updated_at": timestamp,
    }
    html_text = template
    for key, value in context.items():
        html_text = html_text.replace("{{ " + key + " }}", str(value))
    note_path.write_text(html_text)

    scan_pdfs(cfg)
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
