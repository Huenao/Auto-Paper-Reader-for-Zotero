#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List

from config import APRZConfig, data_dir, ensure_notes_layout
from path_utils import note_rel_path_for_pdf


SCHEMA_VERSION = 1


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def paper_index_path(cfg: APRZConfig) -> Path:
    return data_dir(cfg) / "paper_index.json"


def scan_log_path(cfg: APRZConfig) -> Path:
    return data_dir(cfg) / "scan_log.jsonl"


def load_paper_index(cfg: APRZConfig) -> Dict[str, object]:
    path = paper_index_path(cfg)
    if not path.exists():
        return {
            "schema_version": SCHEMA_VERSION,
            "items": [],
        }
    return json.loads(path.read_text())


def iter_pdf_paths(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() == ".pdf")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def title_guess_from_stem(stem: str) -> str:
    value = stem.replace("_", " ").replace("-", " ")
    return " ".join(value.split()) or stem


def _mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds")


def _existing_note_info(cfg: APRZConfig, note_rel: Path):
    note_path = cfg.notes_root / note_rel
    if note_path.exists():
        return True, _mtime(note_path), "read"
    return False, None, "unread"


def _item_for_pdf(cfg: APRZConfig, pdf_path: Path) -> Dict[str, object]:
    rel = pdf_path.resolve().relative_to(cfg.zotero_attachment_root.resolve())
    note_rel = note_rel_path_for_pdf(pdf_path, cfg.zotero_attachment_root)
    note_exists, note_updated_at, status = _existing_note_info(cfg, note_rel)
    fingerprint = sha256_file(pdf_path)
    stat = pdf_path.stat()
    return {
        "paper_id": fingerprint,
        "pdf_abs_path": str(pdf_path.resolve()),
        "pdf_rel_path": rel.as_posix(),
        "category_path": list(rel.parts[:-1]),
        "filename": pdf_path.name,
        "file_stem": pdf_path.stem,
        "title_guess": title_guess_from_stem(pdf_path.stem),
        "authors_guess": [],
        "year_guess": None,
        "file_size": stat.st_size,
        "modified_at": _mtime(pdf_path),
        "content_fingerprint": fingerprint,
        "note_rel_path": note_rel.as_posix(),
        "note_exists": note_exists,
        "note_updated_at": note_updated_at,
        "status": status,
        "tags": [],
        "source_status": "available",
    }


def scan_pdfs(cfg: APRZConfig) -> Dict[str, object]:
    ensure_notes_layout(cfg)
    previous = load_paper_index(cfg)
    previous_by_rel = {item["pdf_rel_path"]: item for item in previous.get("items", [])}
    items: List[Dict[str, object]] = []
    seen = set()
    warnings = []

    for pdf_path in iter_pdf_paths(cfg.zotero_attachment_root):
        try:
            item = _item_for_pdf(cfg, pdf_path)
        except Exception as exc:
            rel = str(pdf_path)
            try:
                rel = pdf_path.resolve().relative_to(cfg.zotero_attachment_root.resolve()).as_posix()
            except Exception:
                pass
            warnings.append(
                {
                    "time": now_iso(),
                    "level": "warning",
                    "code": "pdf_unreadable",
                    "pdf_rel_path": rel,
                    "message": str(exc),
                    "suggestion": "Check whether the file is downloaded locally and readable.",
                }
            )
            continue
        old = previous_by_rel.get(item["pdf_rel_path"])
        if old:
            item["tags"] = old.get("tags", item["tags"])
            if item["note_exists"]:
                item["status"] = "read"
            else:
                item["status"] = old.get("status", item["status"])
        seen.add(item["pdf_rel_path"])
        items.append(item)

    for old in previous.get("items", []):
        if old.get("pdf_rel_path") in seen:
            continue
        missing = dict(old)
        missing["source_status"] = "source_missing"
        missing["note_exists"], missing["note_updated_at"], missing["status"] = _existing_note_info(
            cfg, Path(str(missing.get("note_rel_path", "")))
        )
        items.append(missing)
        warnings.append(
            {
                "time": now_iso(),
                "level": "warning",
                "code": "source_missing",
                "pdf_rel_path": missing.get("pdf_rel_path", ""),
                "message": "PDF was present in a previous scan but is missing now.",
                "suggestion": "Check whether the Zotero attachment is available locally.",
            }
        )

    items.sort(key=lambda item: item.get("pdf_rel_path", ""))
    summary = {
        "pdf_total": sum(1 for item in items if item.get("source_status") == "available"),
        "note_total": sum(1 for item in items if item.get("note_exists")),
        "missing_notes": sum(1 for item in items if not item.get("note_exists")),
        "source_missing": sum(1 for item in items if item.get("source_status") == "source_missing"),
        "warnings": len(warnings),
    }
    output = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "zotero_attachment_root": str(cfg.zotero_attachment_root),
        "notes_root": str(cfg.notes_root),
        "summary": summary,
        "items": items,
    }
    paper_index_path(cfg).write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    if warnings:
        with scan_log_path(cfg).open("a", encoding="utf-8") as handle:
            for warning in warnings:
                handle.write(json.dumps(warning, ensure_ascii=False) + "\n")
    return output
