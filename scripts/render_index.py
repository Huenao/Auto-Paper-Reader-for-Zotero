#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from config import APRZConfig, data_dir, ensure_notes_layout
from path_utils import path_to_file_href, require_within_root, safe_id_filename
from scan_pdfs import load_paper_index, paper_index_path


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def note_index_path(cfg: APRZConfig) -> Path:
    return data_dir(cfg) / "note_index.json"


def _copy_index_assets(cfg: APRZConfig) -> None:
    assets_out = cfg.notes_root / "assets"
    assets_out.mkdir(parents=True, exist_ok=True)
    for name in ["index.css", "index.js", "note.css"]:
        src = skill_root() / "assets" / name
        if src.exists():
            target = require_within_root(assets_out / name, cfg.notes_root)
            shutil.copyfile(src, target)


def _load_payload(cfg: APRZConfig, paper_id: str) -> Dict[str, object]:
    path = data_dir(cfg) / "note_payloads" / (safe_id_filename(paper_id) + ".json")
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _make_note_item(cfg: APRZConfig, paper: Dict[str, object]) -> Dict[str, object]:
    payload = _load_payload(cfg, str(paper["paper_id"]))
    note_rel = str(paper.get("note_rel_path", ""))
    note_abs = cfg.notes_root / note_rel
    note_exists = note_abs.exists()
    title = payload.get("title") or paper.get("title_guess") or paper.get("file_stem")
    status = payload.get("status") or ("read" if note_exists else "unread")
    return {
        "paper_id": paper.get("paper_id"),
        "title": title,
        "authors": payload.get("authors", paper.get("authors_guess", [])),
        "year": payload.get("year", paper.get("year_guess")),
        "venue": payload.get("venue", ""),
        "pdf_rel_path": paper.get("pdf_rel_path"),
        "pdf_href": path_to_file_href(Path(str(paper.get("pdf_abs_path")))) if paper.get("source_status") == "available" else "",
        "note_rel_path": note_rel,
        "note_href": note_rel if note_exists else "",
        "category_path": paper.get("category_path", []),
        "tags": payload.get("tags", paper.get("tags", [])),
        "status": status,
        "source_status": paper.get("source_status", "available"),
        "summary": payload.get("summary", ""),
        "updated_at": payload.get("updated_at") or paper.get("note_updated_at"),
    }


def build_note_index(cfg: APRZConfig) -> Dict[str, object]:
    paper_index = load_paper_index(cfg)
    items: List[Dict[str, object]] = [_make_note_item(cfg, item) for item in paper_index.get("items", [])]
    return {
        "schema_version": 1,
        "generated_at": now_iso(),
        "items": items,
    }


def refresh_index(cfg: APRZConfig) -> Dict[str, object]:
    ensure_notes_layout(cfg)
    if not paper_index_path(cfg).exists():
        from scan_pdfs import scan_pdfs

        scan_pdfs(cfg)
    _copy_index_assets(cfg)
    note_index = build_note_index(cfg)
    note_index_path(cfg).write_text(json.dumps(note_index, ensure_ascii=False, indent=2) + "\n")

    items = note_index["items"]
    categories = {"/".join(item.get("category_path") or []) for item in items}
    context = {
        "generated_at": note_index["generated_at"],
        "pdf_total": sum(1 for item in items if item.get("source_status") == "available"),
        "noted_total": sum(1 for item in items if item.get("status") == "read"),
        "unread_total": sum(1 for item in items if item.get("status") != "read"),
        "category_total": len(categories),
        "note_index_json": json.dumps(note_index, ensure_ascii=False),
    }
    template = (skill_root() / "assets" / "templates" / "index.html").read_text()
    html = template
    for key, value in context.items():
        html = html.replace("{{ " + key + " }}", str(value))
    output_path = require_within_root(cfg.notes_root / cfg.index_filename, cfg.notes_root)
    output_path.write_text(html)
    return {
        "index_abs_path": str(output_path),
        "note_index_abs_path": str(note_index_path(cfg)),
        "item_count": len(items),
    }
