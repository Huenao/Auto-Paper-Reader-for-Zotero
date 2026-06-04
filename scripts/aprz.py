#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from build_readpack import build_readpack
from config import APRZConfig, ConfigError, ensure_notes_layout, load_config, save_global_config, save_project_config
from match_paper import find_paper
from render_index import refresh_index
from render_note import render_note
from scan_pdfs import scan_pdfs


def _json(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _load(args) -> APRZConfig:
    return load_config(config_path=args.config)


def cmd_init(args) -> int:
    pdf_root = Path(args.zotero_attachment_root).expanduser().resolve()
    notes_root = Path(args.notes_root).expanduser().resolve()
    if not pdf_root.exists() or not pdf_root.is_dir():
        raise ConfigError(f"zotero_attachment_root is not a readable directory: {pdf_root}")
    notes_root.mkdir(parents=True, exist_ok=True)
    cfg = APRZConfig(zotero_attachment_root=pdf_root, notes_root=notes_root)
    ensure_notes_layout(cfg)
    if args.scope == "project":
        config_path = save_project_config(cfg)
    else:
        config_path = save_global_config(cfg)
    scan_result = scan_pdfs(cfg)
    index_result = refresh_index(cfg)
    _json(
        {
            "ok": True,
            "config_path": str(config_path),
            "paper_index": scan_result["summary"],
            "index_abs_path": index_result["index_abs_path"],
        }
    )
    return 0


def cmd_doctor(args) -> int:
    cfg = _load(args)
    from extract_pdf import DEFAULT_EXTRACTORS
    import importlib.util
    import shutil

    tools = {
        "pypdf": bool(importlib.util.find_spec("pypdf")),
        "pdfplumber": bool(importlib.util.find_spec("pdfplumber")),
        "pdftotext": bool(shutil.which("pdftotext")),
    }
    result = {
        "config_loaded": True,
        "zotero_attachment_root": str(cfg.zotero_attachment_root),
        "zotero_attachment_root_readable": cfg.zotero_attachment_root.is_dir(),
        "notes_root": str(cfg.notes_root),
        "notes_root_writable": cfg.notes_root.exists() and cfg.notes_root.is_dir(),
        "extractors": {key: tools.get(key, False) for key in DEFAULT_EXTRACTORS},
    }
    _json(result)
    return 0 if result["zotero_attachment_root_readable"] and result["notes_root_writable"] else 2


def cmd_scan(args) -> int:
    _json(scan_pdfs(_load(args)))
    return 0


def cmd_find(args) -> int:
    _json(find_paper(_load(args), args.query))
    return 0


def cmd_readpack(args) -> int:
    pack = build_readpack(_load(args), args.query)
    _json(pack)
    return 0 if pack.get("match_status", "single_match") == "single_match" or "paper_id" in pack else 2


def cmd_note_path(args) -> int:
    match = find_paper(_load(args), args.query)
    if match.get("match_status") != "single_match":
        _json(match)
        return 2
    _json(
        {
            "pdf_rel_path": match["pdf_rel_path"],
            "note_rel_path": match["note_rel_path"],
            "note_abs_path": match["note_abs_path"],
        }
    )
    return 0


def cmd_render_note(args) -> int:
    payload = json.loads(Path(args.payload).read_text())
    if args.paper_id:
        payload["paper_id"] = args.paper_id
    _json(render_note(_load(args), payload))
    return 0


def cmd_refresh_index(args) -> int:
    _json(refresh_index(_load(args)))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Auto-Paper-Reader-for-Zotero CLI")
    parser.add_argument("--config", type=Path, help="Path to config.json")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Initialize config, notes layout, scan, and index")
    init.add_argument("--scope", choices=["global", "project"], default="global", help="Where to save config.json")
    init.add_argument("--zotero-attachment-root", required=True)
    init.add_argument("--notes-root", required=True)
    init.set_defaults(func=cmd_init)

    doctor = sub.add_parser("doctor", help="Check config, paths, and extraction tools")
    doctor.set_defaults(func=cmd_doctor)

    scan = sub.add_parser("scan", help="Scan PDFs and write paper_index.json")
    scan.set_defaults(func=cmd_scan)

    find = sub.add_parser("find", help="Find a paper by path, filename, or title fragment")
    find.add_argument("query")
    find.set_defaults(func=cmd_find)

    readpack = sub.add_parser("readpack", help="Build a reading pack for Codex")
    readpack.add_argument("query")
    readpack.add_argument("--json", action="store_true", help="Accepted for compatibility; output is always JSON")
    readpack.set_defaults(func=cmd_readpack)

    note_path = sub.add_parser("note-path", help="Print mirrored note path for a paper")
    note_path.add_argument("query")
    note_path.add_argument("--json", action="store_true", help="Accepted for compatibility; output is always JSON")
    note_path.set_defaults(func=cmd_note_path)

    render = sub.add_parser("render-note", help="Render an HTML note from a note payload JSON")
    render.add_argument("--paper-id", required=False)
    render.add_argument("--payload", required=True)
    render.set_defaults(func=cmd_render_note)

    refresh = sub.add_parser("refresh-index", help="Refresh note_index.json and index.html")
    refresh.set_defaults(func=cmd_refresh_index)
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
