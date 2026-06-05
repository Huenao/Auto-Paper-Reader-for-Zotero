#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from config import APRZConfig, data_dir, ensure_notes_layout
from path_utils import PathSafetyError, relative_to_root, require_within_root, safe_id_filename
from scan_pdfs import load_paper_index, sha256_file


DEFAULT_DPI = 200
CODEX_NATIVE_BIN = Path("~/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin").expanduser()


def extract_visuals_for_paper_id(
    cfg: APRZConfig,
    paper_id: str,
    page: int | None = None,
    bbox: str | list[int] | tuple[int, int, int, int] | None = None,
    label: str = "",
    caption: str = "",
    linked_section: str = "method",
    dpi: int = DEFAULT_DPI,
    render_page: bool = False,
) -> dict[str, Any]:
    ensure_notes_layout(cfg)
    for item in load_paper_index(cfg).get("items", []):
        if item.get("paper_id") == paper_id:
            return extract_visuals_for_pdf(
                cfg,
                Path(str(item["pdf_abs_path"])),
                paper_id=paper_id,
                page=page,
                bbox=bbox,
                label=label,
                caption=caption,
                linked_section=linked_section,
                dpi=dpi,
                render_page=render_page,
            )
    return {
        "visual_extraction_status": "paper_not_found",
        "paper_id": paper_id,
        "visuals": [],
        "message": f"paper_id not found in paper_index.json: {paper_id}",
    }


def extract_visuals_for_pdf(
    cfg: APRZConfig,
    pdf_path: Path,
    paper_id: str | None = None,
    page: int | None = None,
    bbox: str | list[int] | tuple[int, int, int, int] | None = None,
    label: str = "",
    caption: str = "",
    linked_section: str = "method",
    dpi: int = DEFAULT_DPI,
    render_page: bool = False,
) -> dict[str, Any]:
    ensure_notes_layout(cfg)
    pdf_path = Path(pdf_path).expanduser().resolve()
    base_error = _validate_pdf_path(cfg, pdf_path)
    if base_error:
        return base_error

    resolved_paper_id = paper_id or sha256_file(pdf_path)
    safe_paper_id = safe_id_filename(resolved_paper_id)
    visuals_dir = require_within_root(cfg.notes_root / "assets" / "papers" / safe_paper_id / "images", cfg.notes_root)
    visual_data_dir = require_within_root(data_dir(cfg) / "visuals" / safe_paper_id, cfg.notes_root)
    visuals_json_path = require_within_root(visual_data_dir / "visuals.json", cfg.notes_root)

    if page is None:
        result = {
            "visual_extraction_status": "needs_page_and_bbox",
            "paper_id": resolved_paper_id,
            "pdf_abs_path": str(pdf_path),
            "visuals": [],
            "visuals_json_path": str(visuals_json_path),
            "message": "Provide --page and --bbox after rendering/inspecting the target PDF page.",
        }
        _write_visuals_json(visuals_json_path, result)
        return result

    tools = _poppler_tools()
    if not tools:
        result = {
            "visual_extraction_status": "no_visual_extractor_available",
            "paper_id": resolved_paper_id,
            "pdf_abs_path": str(pdf_path),
            "visuals": [],
            "visuals_json_path": str(visuals_json_path),
            "message": "Poppler pdfinfo and pdftoppm are required for page rendering.",
        }
        _write_visuals_json(visuals_json_path, result)
        return result

    try:
        Image = _load_pillow_image()
    except ModuleNotFoundError:
        result = {
            "visual_extraction_status": "no_visual_extractor_available",
            "paper_id": resolved_paper_id,
            "pdf_abs_path": str(pdf_path),
            "visuals": [],
            "visuals_json_path": str(visuals_json_path),
            "message": "Pillow is required to crop rendered PDF pages.",
        }
        _write_visuals_json(visuals_json_path, result)
        return result

    page_count = _pdf_page_count(tools["pdfinfo"], pdf_path)
    if page < 1 or (page_count and page > page_count):
        result = {
            "visual_extraction_status": "invalid_page",
            "paper_id": resolved_paper_id,
            "pdf_abs_path": str(pdf_path),
            "page": page,
            "page_count": page_count,
            "visuals": [],
            "visuals_json_path": str(visuals_json_path),
            "message": "Page must be within the PDF page range.",
        }
        _write_visuals_json(visuals_json_path, result)
        return result

    if render_page and bbox is None:
        page_render_path = require_within_root(visual_data_dir / "page-renders" / f"page-{page:03d}.png", cfg.notes_root)
        _render_page(tools["pdftoppm"], pdf_path, page, dpi, page_render_path)
        result = {
            "visual_extraction_status": "page_rendered",
            "paper_id": resolved_paper_id,
            "pdf_abs_path": str(pdf_path),
            "page": page,
            "page_count": page_count,
            "dpi": dpi,
            "page_render_abs_path": str(page_render_path),
            "visuals": [],
            "visuals_json_path": str(visuals_json_path),
            "message": "Rendered the requested page. Inspect it, then rerun with --page and --bbox to crop the figure.",
        }
        _write_visuals_json(visuals_json_path, result)
        return result

    parsed_bbox = _parse_bbox(bbox)
    if not parsed_bbox:
        result = {
            "visual_extraction_status": "needs_page_and_bbox",
            "paper_id": resolved_paper_id,
            "pdf_abs_path": str(pdf_path),
            "page": page,
            "visuals": [],
            "visuals_json_path": str(visuals_json_path),
            "message": "Provide --page and --bbox x1,y1,x2,y2 after inspecting the rendered page.",
        }
        _write_visuals_json(visuals_json_path, result)
        return result
    if parsed_bbox[2] <= parsed_bbox[0] or parsed_bbox[3] <= parsed_bbox[1]:
        result = _invalid_bbox_result(resolved_paper_id, pdf_path, page, parsed_bbox, visuals_json_path, "bbox x2/y2 must be greater than x1/y1.")
        _write_visuals_json(visuals_json_path, result)
        return result

    with tempfile.TemporaryDirectory(prefix="aprz-page-render-") as tmp:
        page_render_path = Path(tmp) / f"page-{page:03d}.png"
        _render_page(tools["pdftoppm"], pdf_path, page, dpi, page_render_path)
        with Image.open(page_render_path) as image:
            width, height = image.size
            if parsed_bbox[0] < 0 or parsed_bbox[1] < 0 or parsed_bbox[2] > width or parsed_bbox[3] > height:
                result = _invalid_bbox_result(
                    resolved_paper_id,
                    pdf_path,
                    page,
                    parsed_bbox,
                    visuals_json_path,
                    f"bbox must fit inside rendered page bounds 0,0,{width},{height}.",
                )
                _write_visuals_json(visuals_json_path, result)
                return result
            crop = image.crop(tuple(parsed_bbox))
            asset_path = require_within_root(visuals_dir / _visual_filename(label, caption, linked_section, page), cfg.notes_root)
            asset_path.parent.mkdir(parents=True, exist_ok=True)
            crop.save(asset_path, format="PNG")

    visual = _visual_item(asset_path, page, parsed_bbox, label, caption, linked_section, dpi)
    result = {
        "visual_extraction_status": "ok",
        "paper_id": resolved_paper_id,
        "pdf_abs_path": str(pdf_path),
        "page_count": page_count,
        "visuals_json_path": str(visuals_json_path),
        "visuals": [visual],
        "message": "Cropped 1 visual item with Poppler page rendering and Pillow.",
    }
    _write_visuals_json(visuals_json_path, result)
    return result


def _validate_pdf_path(cfg: APRZConfig, pdf_path: Path) -> dict[str, Any] | None:
    try:
        relative_to_root(pdf_path, cfg.zotero_attachment_root)
    except PathSafetyError:
        return {
            "visual_extraction_status": "outside_attachment_root",
            "pdf_abs_path": str(pdf_path),
            "zotero_attachment_root": str(cfg.zotero_attachment_root.resolve()),
            "visuals": [],
            "message": "Refusing visual extraction because the PDF path is outside zotero_attachment_root.",
        }
    if not pdf_path.exists() or not pdf_path.is_file():
        return {
            "visual_extraction_status": "pdf_not_found",
            "pdf_abs_path": str(pdf_path),
            "visuals": [],
            "message": "PDF path does not exist or is not a file.",
        }
    if pdf_path.suffix.lower() != ".pdf":
        return {
            "visual_extraction_status": "not_pdf",
            "pdf_abs_path": str(pdf_path),
            "visuals": [],
            "message": "Visual extraction requires a .pdf file.",
        }
    return None


def _resolve_tool(name: str) -> str:
    env_dir = os.environ.get("APRZ_POPPLER_BIN_DIR")
    candidates = []
    if env_dir:
        candidates.append(Path(env_dir) / name)
    found = shutil.which(name)
    if found:
        candidates.append(Path(found))
    candidates.extend(
        [
            CODEX_NATIVE_BIN / name,
            Path("/opt/homebrew/bin") / name,
            Path("/usr/local/bin") / name,
        ]
    )
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    return ""


def _poppler_tools() -> dict[str, str]:
    pdfinfo = _resolve_tool("pdfinfo")
    pdftoppm = _resolve_tool("pdftoppm")
    if not pdfinfo or not pdftoppm:
        return {}
    return {"pdfinfo": pdfinfo, "pdftoppm": pdftoppm}


def _load_pillow_image():
    from PIL import Image

    return Image


def _pdf_page_count(pdfinfo: str, pdf_path: Path) -> int | None:
    result = subprocess.run(
        [pdfinfo, str(pdf_path)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    match = re.search(r"^Pages:\s+(\d+)", result.stdout, re.MULTILINE)
    return int(match.group(1)) if match else None


def _render_page(pdftoppm: str, pdf_path: Path, page: int, dpi: int, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_prefix = output_path.with_suffix("")
    subprocess.run(
        [
            pdftoppm,
            "-f",
            str(page),
            "-l",
            str(page),
            "-r",
            str(dpi),
            "-png",
            "-singlefile",
            str(pdf_path),
            str(output_prefix),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    rendered = output_prefix.with_suffix(".png")
    if rendered != output_path and rendered.exists():
        rendered.replace(output_path)
    return output_path


def _parse_bbox(bbox: str | list[int] | tuple[int, int, int, int] | None) -> list[int] | None:
    if bbox is None:
        return None
    if isinstance(bbox, str):
        parts = [part.strip() for part in bbox.split(",")]
    else:
        parts = list(bbox)
    if len(parts) != 4:
        return None
    try:
        return [int(float(part)) for part in parts]
    except (TypeError, ValueError):
        return None


def _invalid_bbox_result(
    paper_id: str,
    pdf_path: Path,
    page: int,
    bbox: list[int],
    visuals_json_path: Path,
    message: str,
) -> dict[str, Any]:
    return {
        "visual_extraction_status": "invalid_bbox",
        "paper_id": paper_id,
        "pdf_abs_path": str(pdf_path),
        "page": page,
        "bbox": bbox,
        "visuals": [],
        "visuals_json_path": str(visuals_json_path),
        "message": message,
    }


def _visual_filename(label: str, caption: str, linked_section: str, page: int) -> str:
    number = _figure_number(label, caption)
    if number:
        stem = f"figure-{number:03d}"
    elif linked_section in {"method", "pipeline"}:
        stem = "method-architecture"
    else:
        stem = "visual"
    return f"{stem}-p{page:03d}.png"


def _figure_number(*values: str) -> int | None:
    for value in values:
        match = re.search(r"(?:Figure|Fig\.?|图)\s*(\d+)", value or "", re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _visual_item(
    asset_path: Path,
    page: int,
    bbox: list[int],
    label: str,
    caption: str,
    linked_section: str,
    dpi: int,
) -> dict[str, Any]:
    display_label = label or "方法架构图"
    return {
        "label": display_label,
        "label_original": _label_original(display_label),
        "caption": caption,
        "caption_zh": caption if _contains_cjk(caption) else "",
        "page": page,
        "bbox": bbox,
        "asset_path": str(asset_path.resolve()),
        "dpi": dpi,
        "visual_type": "figure",
        "crop_status": "cropped_with_poppler_pillow",
        "evidence_summary": "",
        "linked_section": linked_section or "method",
    }


def _label_original(label: str) -> str:
    match = re.search(r"图\s*(\d+)", label)
    if match:
        return f"Figure {match.group(1)}"
    return label


def _contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u3400-\u4dbf\u4e00-\u9fff]", text))


def _write_visuals_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
