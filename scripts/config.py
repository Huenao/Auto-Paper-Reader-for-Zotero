#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Mapping, Optional


PROJECT_CONFIG = Path(".auto-paper-reader") / "config.json"
GLOBAL_CONFIG = Path("~/.config/auto-paper-reader-for-zotero/config.json")


class ConfigError(RuntimeError):
    pass


@dataclass
class APRZConfig:
    zotero_attachment_root: Path
    notes_root: Path
    language: str = "zh-CN"
    note_format: str = "html"
    mirror_attachment_tree: bool = True
    index_filename: str = "index.html"
    default_note_style: str = "technical-readable"
    include_pdf_link_in_note: bool = True
    include_backlink_to_index: bool = True
    metadata_mode: str = "path-first"
    optional_bibtex_path: str = ""
    optional_csl_json_path: str = ""
    optional_zotero_sqlite_path: str = ""

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object], base_dir: Optional[Path] = None) -> "APRZConfig":
        if "zotero_attachment_root" not in raw or "notes_root" not in raw:
            raise ConfigError("Config requires zotero_attachment_root and notes_root.")
        base = base_dir or Path.cwd()
        data = dict(raw)
        data["zotero_attachment_root"] = _resolve_path(str(data["zotero_attachment_root"]), base)
        data["notes_root"] = _resolve_path(str(data["notes_root"]), base)
        allowed = {field.name for field in cls.__dataclass_fields__.values()}
        filtered = {key: value for key, value in data.items() if key in allowed}
        return cls(**filtered)

    def to_json_dict(self) -> Dict[str, object]:
        data = asdict(self)
        data["zotero_attachment_root"] = str(self.zotero_attachment_root)
        data["notes_root"] = str(self.notes_root)
        return data


def _resolve_path(value: str, base_dir: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def project_config_path(cwd: Optional[Path] = None) -> Path:
    return (cwd or Path.cwd()) / PROJECT_CONFIG


def global_config_path(env: Optional[Mapping[str, str]] = None) -> Path:
    source = env if env is not None else os.environ
    home = Path(source.get("HOME", str(Path.home()))).expanduser()
    return home / ".config" / "auto-paper-reader-for-zotero" / "config.json"


def load_config(
    config_path: Optional[Path] = None,
    cwd: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
    overrides: Optional[Mapping[str, str]] = None,
) -> APRZConfig:
    cwd = (cwd or Path.cwd()).resolve()
    env = env if env is not None else os.environ
    overrides = dict(overrides or {})

    candidates = []
    if config_path:
        candidates.append(Path(config_path).expanduser())
    elif env.get("APRZ_CONFIG_PATH"):
        candidates.append(Path(env["APRZ_CONFIG_PATH"]).expanduser())
    else:
        candidates.extend([project_config_path(cwd), global_config_path(env)])

    raw = None
    base_dir = cwd
    explicit_missing = config_path or env.get("APRZ_CONFIG_PATH")
    for candidate in candidates:
        candidate = candidate if candidate.is_absolute() else cwd / candidate
        if candidate.exists():
            try:
                raw = json.loads(candidate.read_text())
            except json.JSONDecodeError as exc:
                raise ConfigError(f"Invalid JSON config: {candidate}: {exc}") from exc
            base_dir = candidate.parent
            break
    if raw is None and explicit_missing:
        raise ConfigError(f"Config file not found: {candidates[0]}")

    if raw is None:
        pdf_root = env.get("APRZ_ZOTERO_ATTACHMENT_ROOT")
        notes_root = env.get("APRZ_NOTES_ROOT")
        if pdf_root and notes_root:
            raw = {
                "zotero_attachment_root": pdf_root,
                "notes_root": notes_root,
            }
            base_dir = cwd
        else:
            raise ConfigError(
                "Missing config. Provide --config, APRZ_CONFIG_PATH, .auto-paper-reader/config.json, "
                "global config, or APRZ_ZOTERO_ATTACHMENT_ROOT plus APRZ_NOTES_ROOT."
            )

    raw.update({key: value for key, value in overrides.items() if value})
    return APRZConfig.from_mapping(raw, base_dir=base_dir)


def save_project_config(cfg: APRZConfig, cwd: Optional[Path] = None) -> Path:
    path = project_config_path(cwd)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg.to_json_dict(), ensure_ascii=False, indent=2) + "\n")
    return path


def save_global_config(cfg: APRZConfig, env: Optional[Mapping[str, str]] = None) -> Path:
    path = global_config_path(env)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg.to_json_dict(), ensure_ascii=False, indent=2) + "\n")
    return path


def data_dir(cfg: APRZConfig) -> Path:
    return cfg.notes_root / "data"


def ensure_notes_layout(cfg: APRZConfig) -> None:
    for path in [
        cfg.notes_root,
        data_dir(cfg),
        data_dir(cfg) / "extracted_text",
        data_dir(cfg) / "backups",
        data_dir(cfg) / "note_payloads",
        cfg.notes_root / "assets",
    ]:
        path.mkdir(parents=True, exist_ok=True)
