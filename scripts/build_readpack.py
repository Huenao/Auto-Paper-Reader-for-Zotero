#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from config import APRZConfig, data_dir, ensure_notes_layout
from extract_pdf import extract_pdf_text
from match_paper import find_paper
from path_utils import PathSafetyError, note_rel_path_for_pdf, relative_to_root, require_within_root, safe_id_filename
from scan_pdfs import sha256_file, title_guess_from_stem


def build_readpack(
    cfg: APRZConfig,
    query: str,
    extractors: Optional[Iterable[str]] = None,
) -> dict:
    ensure_notes_layout(cfg)
    match = find_paper(cfg, query)
    if match.get("match_status") != "single_match":
        return match

    paper_id = str(match["paper_id"])
    text_path = require_within_root(
        data_dir(cfg) / "extracted_text" / (safe_id_filename(paper_id) + ".txt"),
        cfg.notes_root,
    )
    extraction = extract_pdf_text(Path(str(match["pdf_abs_path"])), text_path, extractors=extractors)
    note_abs = require_within_root(Path(str(match["note_abs_path"])), cfg.notes_root)

    return {
        "schema_version": 1,
        "paper_id": paper_id,
        "pdf_abs_path": match["pdf_abs_path"],
        "pdf_rel_path": match["pdf_rel_path"],
        "note_abs_path": str(note_abs),
        "note_rel_path": match["note_rel_path"],
        "title": match.get("title_guess") or match.get("file_stem"),
        "authors": match.get("authors_guess", []),
        "year": match.get("year_guess"),
        "abstract": "",
        "sections": extraction.get("sections", []),
        "full_text_path": extraction.get("full_text_path"),
        "extraction_status": extraction.get("status"),
        "extraction_message": extraction.get("message", ""),
        "source_resolution": "query_match",
        "recommended_reading_order": [
            "abstract",
            "introduction",
            "method",
            "experiments",
            "limitations",
        ],
    }


def build_readpack_from_pdf_path(
    cfg: APRZConfig,
    pdf_path: Path,
    extractors: Optional[Iterable[str]] = None,
) -> dict:
    ensure_notes_layout(cfg)
    pdf_path = Path(pdf_path).expanduser().resolve()
    try:
        pdf_rel = relative_to_root(pdf_path, cfg.zotero_attachment_root)
    except PathSafetyError:
        return {
            "match_status": "outside_attachment_root",
            "pdf_abs_path": str(pdf_path),
            "zotero_attachment_root": str(cfg.zotero_attachment_root.resolve()),
            "message": "Refusing direct PDF readpack because the PDF path is outside zotero_attachment_root.",
        }
    if not pdf_path.exists() or not pdf_path.is_file():
        return {
            "match_status": "pdf_not_found",
            "pdf_abs_path": str(pdf_path),
            "message": "PDF path does not exist or is not a file.",
        }
    if pdf_path.suffix.lower() != ".pdf":
        return {
            "match_status": "not_pdf",
            "pdf_abs_path": str(pdf_path),
            "message": "Direct readpack requires a .pdf file.",
        }

    paper_id = sha256_file(pdf_path)
    note_rel = note_rel_path_for_pdf(pdf_path, cfg.zotero_attachment_root)
    note_abs = require_within_root(cfg.notes_root / note_rel, cfg.notes_root)
    text_path = require_within_root(
        data_dir(cfg) / "extracted_text" / (safe_id_filename(paper_id) + ".txt"),
        cfg.notes_root,
    )
    extraction = extract_pdf_text(pdf_path, text_path, extractors=extractors)

    return {
        "schema_version": 1,
        "paper_id": paper_id,
        "pdf_abs_path": str(pdf_path),
        "pdf_rel_path": pdf_rel.as_posix(),
        "note_abs_path": str(note_abs),
        "note_rel_path": note_rel.as_posix(),
        "title": title_guess_from_stem(pdf_path.stem),
        "authors": [],
        "year": None,
        "abstract": "",
        "sections": extraction.get("sections", []),
        "full_text_path": extraction.get("full_text_path"),
        "extraction_status": extraction.get("status"),
        "extraction_message": extraction.get("message", ""),
        "recommended_reading_order": [
            "abstract",
            "introduction",
            "method",
            "experiments",
            "limitations",
        ],
        "source_resolution": "direct_pdf_path",
    }
