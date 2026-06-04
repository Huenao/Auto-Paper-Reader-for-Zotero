#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, Optional


DEFAULT_EXTRACTORS = ["pypdf", "pdfplumber", "pdftotext"]


def _write_text(output_path: Path, text: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8", errors="replace")


def _extract_with_pypdf(pdf_path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_with_pdfplumber(pdf_path: Path) -> str:
    import pdfplumber

    with pdfplumber.open(str(pdf_path)) as pdf:
        return "\n\n".join(page.extract_text() or "" for page in pdf.pages)


def _extract_with_pdftotext(pdf_path: Path) -> str:
    result = subprocess.run(
        ["pdftotext", str(pdf_path), "-"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout


def extract_pdf_text(
    pdf_path: Path,
    output_path: Path,
    extractors: Optional[Iterable[str]] = None,
) -> dict:
    requested = list(DEFAULT_EXTRACTORS if extractors is None else extractors)
    available = []
    for extractor in requested:
        if extractor in {"pypdf", "pdfplumber"} and importlib.util.find_spec(extractor):
            available.append(extractor)
        elif extractor == "pdftotext" and shutil.which("pdftotext"):
            available.append(extractor)

    if not available:
        return {
            "status": "no_extractor_available",
            "full_text_path": str(output_path),
            "sections": [],
            "message": "No PDF text extractor is available.",
        }

    last_error = None
    for extractor in available:
        try:
            if extractor == "pypdf":
                text = _extract_with_pypdf(pdf_path)
            elif extractor == "pdfplumber":
                text = _extract_with_pdfplumber(pdf_path)
            else:
                text = _extract_with_pdftotext(pdf_path)
        except Exception as exc:
            last_error = exc
            continue
        if text.strip():
            _write_text(output_path, text)
            return {
                "status": "ok",
                "full_text_path": str(output_path),
                "sections": [],
                "message": f"Extracted with {extractor}.",
            }
        last_error = RuntimeError(f"{extractor} produced no text")

    return {
        "status": "failed",
        "full_text_path": str(output_path),
        "sections": [],
        "message": str(last_error or "PDF extraction failed."),
    }
