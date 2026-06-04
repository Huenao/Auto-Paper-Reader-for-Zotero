#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


class PathSafetyError(RuntimeError):
    pass


def _resolved(path: Path) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def require_within_root(target: Path, root: Path) -> Path:
    root_resolved = _resolved(root)
    target_resolved = _resolved(target)
    try:
        target_resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise PathSafetyError(f"Refusing to write outside notes_root: {target_resolved}") from exc
    return target_resolved


def relative_to_root(path: Path, root: Path) -> Path:
    try:
        return _resolved(path).relative_to(_resolved(root))
    except ValueError as exc:
        raise PathSafetyError(f"Path is outside root: {path}") from exc


def sanitize_filename_stem(stem: str) -> str:
    value = stem.replace(":", " -")
    value = re.sub(r'[<>"/\\|?*\x00-\x1f]+', "-", value)
    value = re.sub(r"\s+", " ", value).strip(" .-_")
    value = re.sub(r"-{2,}", "-", value)
    return value or "untitled"


def note_rel_path_for_pdf(pdf_path: Path, pdf_root: Path) -> Path:
    rel = relative_to_root(pdf_path, pdf_root)
    parts = list(rel.parts)
    parts[-1] = sanitize_filename_stem(Path(parts[-1]).stem) + ".html"
    return Path(*parts)


def path_to_file_href(path: Path) -> str:
    return _resolved(path).as_uri()


def safe_id_filename(paper_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", paper_id)
