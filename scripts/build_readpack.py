#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from config import APRZConfig, data_dir, ensure_notes_layout
from extract_pdf import extract_pdf_text
from match_paper import find_paper
from path_utils import require_within_root, safe_id_filename


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
        "recommended_reading_order": [
            "abstract",
            "introduction",
            "method",
            "experiments",
            "limitations",
        ],
    }
