#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from config import APRZConfig
from path_utils import require_within_root
from scan_pdfs import paper_index_path


def _load_items(cfg: APRZConfig) -> List[Dict[str, object]]:
    path = paper_index_path(cfg)
    if not path.exists():
        return []
    return json.loads(path.read_text()).get("items", [])


def _norm(value: object) -> str:
    return str(value or "").casefold().strip()


def _with_note_paths(cfg: APRZConfig, item: Dict[str, object], confidence: float, reason: str) -> Dict[str, object]:
    note_abs = require_within_root(cfg.notes_root / str(item["note_rel_path"]), cfg.notes_root)
    out = dict(item)
    out.update(
        {
            "match_status": "single_match",
            "confidence": confidence,
            "reason": reason,
            "note_abs_path": str(note_abs),
        }
    )
    return out


def _candidate(item: Dict[str, object]) -> Dict[str, object]:
    return {
        "paper_id": item.get("paper_id"),
        "pdf_rel_path": item.get("pdf_rel_path"),
        "title_guess": item.get("title_guess"),
        "note_rel_path": item.get("note_rel_path"),
        "source_status": item.get("source_status"),
    }


def find_paper(cfg: APRZConfig, query: str) -> Dict[str, object]:
    items = _load_items(cfg)
    if not items:
        return {"match_status": "not_found", "query": query, "candidates": []}

    q = query.strip()
    q_norm = _norm(q)
    q_path = Path(q).expanduser()

    if q_path.is_absolute():
        try:
            rel = q_path.resolve(strict=False).relative_to(cfg.zotero_attachment_root.resolve(strict=False)).as_posix()
        except ValueError:
            return {"match_status": "invalid_source_path", "query": query, "reason": "Path is outside zotero_attachment_root."}
        for item in items:
            if item.get("pdf_rel_path") == rel:
                return _with_note_paths(cfg, item, 1.0, "absolute path match")
        return {"match_status": "not_found", "query": query, "candidates": []}

    for item in items:
        if _norm(item.get("pdf_rel_path")) == q_norm:
            return _with_note_paths(cfg, item, 1.0, "relative path match")

    filename_matches = [item for item in items if _norm(item.get("filename")) == q_norm]
    if len(filename_matches) == 1:
        return _with_note_paths(cfg, filename_matches[0], 0.98, "exact filename match")
    if len(filename_matches) > 1:
        return {
            "match_status": "multiple_candidates",
            "query": query,
            "confidence": 0.75,
            "reason": "multiple exact filename matches",
            "candidates": [_candidate(item) for item in filename_matches],
        }

    scored = []
    for item in items:
        haystacks = [
            _norm(item.get("pdf_rel_path")),
            _norm(item.get("filename")),
            _norm(item.get("file_stem")),
            _norm(item.get("title_guess")),
        ]
        if any(q_norm and q_norm in haystack for haystack in haystacks):
            score = 0.72
            if q_norm in (_norm(item.get("file_stem")), _norm(item.get("title_guess"))):
                score = 0.9
            scored.append((score, item))

    scored.sort(key=lambda pair: (-pair[0], str(pair[1].get("pdf_rel_path", ""))))
    if len(scored) == 1:
        return _with_note_paths(cfg, scored[0][1], scored[0][0], "fuzzy filename/title match")
    if scored:
        return {
            "match_status": "multiple_candidates",
            "query": query,
            "confidence": scored[0][0],
            "reason": "multiple fuzzy candidates",
            "candidates": [_candidate(item) for _, item in scored],
        }
    return {"match_status": "not_found", "query": query, "candidates": []}
