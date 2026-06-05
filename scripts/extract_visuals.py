#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from config import APRZConfig, data_dir, ensure_notes_layout
from path_utils import PathSafetyError, relative_to_root, require_within_root, safe_id_filename
from scan_pdfs import load_paper_index, sha256_file


DEFAULT_IMAGE_SCALE = 3.0
CAPTION_RE = re.compile(
    r"^(Figure|Fig\.?|Table|图|表)\s*([A-Za-z0-9.\-一二三四五六七八九十]+)?[:.\s-]*(.*)$",
    re.IGNORECASE,
)


def convert_pdf_with_docling(pdf_path: Path, image_scale: float = DEFAULT_IMAGE_SCALE) -> tuple[Any, type[Any], type[Any]]:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling_core.types.doc import PictureItem, TableItem

    options = PdfPipelineOptions()
    _configure_docling_options(options, image_scale=image_scale)
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=options),
        }
    )
    return converter.convert(pdf_path), PictureItem, TableItem


def _configure_docling_options(options: Any, image_scale: float) -> Any:
    if hasattr(options, "images_scale"):
        options.images_scale = image_scale
    if hasattr(options, "generate_picture_images"):
        options.generate_picture_images = True
    if hasattr(options, "generate_table_images"):
        options.generate_table_images = True
    if hasattr(options, "generate_page_images"):
        options.generate_page_images = False
    if hasattr(options, "do_table_structure"):
        options.do_table_structure = True
    if hasattr(options, "enable_remote_services"):
        options.enable_remote_services = False
    if hasattr(options, "do_picture_description"):
        options.do_picture_description = False
    if hasattr(options, "do_picture_classification"):
        options.do_picture_classification = False
    return options


def extract_visuals_for_paper_id(
    cfg: APRZConfig,
    paper_id: str,
    image_scale: float = DEFAULT_IMAGE_SCALE,
) -> dict[str, Any]:
    ensure_notes_layout(cfg)
    for item in load_paper_index(cfg).get("items", []):
        if item.get("paper_id") == paper_id:
            return extract_visuals_for_pdf(cfg, Path(str(item["pdf_abs_path"])), paper_id=paper_id, image_scale=image_scale)
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
    image_scale: float = DEFAULT_IMAGE_SCALE,
) -> dict[str, Any]:
    ensure_notes_layout(cfg)
    pdf_path = Path(pdf_path).expanduser().resolve()
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

    resolved_paper_id = paper_id or sha256_file(pdf_path)
    visuals_dir = require_within_root(
        cfg.notes_root / "assets" / "papers" / safe_id_filename(resolved_paper_id) / "images",
        cfg.notes_root,
    )
    visuals_json_path = require_within_root(
        data_dir(cfg) / "visuals" / (safe_id_filename(resolved_paper_id) + ".json"),
        cfg.notes_root,
    )

    try:
        conversion, picture_cls, table_cls = convert_pdf_with_docling(pdf_path, image_scale=image_scale)
    except ModuleNotFoundError:
        result = {
            "visual_extraction_status": "no_visual_extractor_available",
            "paper_id": resolved_paper_id,
            "pdf_abs_path": str(pdf_path),
            "visuals": [],
            "visuals_json_path": str(visuals_json_path),
            "message": "Docling is not installed; visual extraction was skipped.",
        }
        _write_visuals_json(visuals_json_path, result)
        return result
    except Exception as exc:
        result = {
            "visual_extraction_status": "failed",
            "paper_id": resolved_paper_id,
            "pdf_abs_path": str(pdf_path),
            "visuals": [],
            "visuals_json_path": str(visuals_json_path),
            "message": f"Docling visual extraction failed: {exc}",
        }
        _write_visuals_json(visuals_json_path, result)
        return result

    document = conversion.document
    visuals = _extract_docling_visuals(document, picture_cls, table_cls, visuals_dir, image_scale)
    result = {
        "visual_extraction_status": "ok" if visuals else "no_visuals_found",
        "paper_id": resolved_paper_id,
        "pdf_abs_path": str(pdf_path),
        "visuals": visuals,
        "visuals_json_path": str(visuals_json_path),
        "message": f"Extracted {len(visuals)} visual item(s) with Docling.",
    }
    _write_visuals_json(visuals_json_path, result)
    return result


def _extract_docling_visuals(
    document: Any,
    picture_cls: type[Any],
    table_cls: type[Any],
    visuals_dir: Path,
    image_scale: float,
) -> list[dict[str, Any]]:
    visuals: list[dict[str, Any]] = []
    figure_count = 0
    table_count = 0
    for element, _level in document.iterate_items():
        if isinstance(element, table_cls):
            table_count += 1
            visuals.append(_visual_item(document, element, visuals_dir, "table", table_count, image_scale))
        elif isinstance(element, picture_cls):
            figure_count += 1
            visuals.append(_visual_item(document, element, visuals_dir, "figure", figure_count, image_scale))
    return visuals


def _visual_item(
    document: Any,
    element: Any,
    visuals_dir: Path,
    visual_type: str,
    index: int,
    image_scale: float,
) -> dict[str, Any]:
    caption = _caption_text(element, document)
    label, label_original = _visual_label(caption, visual_type, index)
    filename = f"{visual_type}-{index:03d}.png"
    asset_path = _save_image(element, document, visuals_dir / filename)
    linked_section = "experiments" if visual_type == "table" else "method"
    return {
        "label": label,
        "label_original": label_original,
        "caption": caption,
        "caption_zh": caption if _contains_cjk(caption) else "",
        "page": _page_no(element),
        "asset_path": asset_path,
        "image_scale": image_scale,
        "visual_type": visual_type,
        "crop_status": "exported_with_docling" if asset_path else "docling_item_without_image",
        "evidence_summary": "",
        "linked_section": linked_section,
    }


def _caption_text(element: Any, document: Any) -> str:
    caption_method = getattr(element, "caption_text", None)
    if callable(caption_method):
        try:
            return str(caption_method(doc=document) or "").strip()
        except TypeError:
            return str(caption_method(document) or "").strip()
    return str(getattr(element, "text", "") or getattr(element, "orig", "") or "").strip()


def _visual_label(caption: str, visual_type: str, index: int) -> tuple[str, str]:
    match = CAPTION_RE.match(caption.strip())
    if match:
        kind = match.group(1)
        number = (match.group(2) or str(index)).strip()
        if kind.lower().startswith("table") or kind == "表":
            return f"表 {number}".strip(), f"Table {number}".strip()
        return f"图 {number}".strip(), f"Figure {number}".strip()
    if visual_type == "table":
        return f"表 {index}", f"Table {index}"
    return f"图 {index}", f"Figure {index}"


def _save_image(element: Any, document: Any, output_path: Path) -> str:
    get_image = getattr(element, "get_image", None)
    if not callable(get_image):
        return ""
    image = get_image(document)
    if image is None:
        return ""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        image.save(output_path, format="PNG")
    except TypeError:
        with output_path.open("wb") as handle:
            image.save(handle, format="PNG")
    return str(output_path.resolve())


def _page_no(element: Any) -> int | None:
    prov = getattr(element, "prov", None) or []
    if not prov:
        return None
    page = getattr(prov[0], "page_no", None)
    return int(page) if isinstance(page, int) else page


def _contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u3400-\u4dbf\u4e00-\u9fff]", text))


def _write_visuals_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
