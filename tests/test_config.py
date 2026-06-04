import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from config import ConfigError, load_config


class ConfigTests(unittest.TestCase):
    def test_explicit_config_path_has_priority(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_root = root / "pdfs"
            notes_root = root / "notes"
            pdf_root.mkdir()
            notes_root.mkdir()
            explicit = root / "explicit.json"
            explicit.write_text(
                json.dumps(
                    {
                        "zotero_attachment_root": str(pdf_root),
                        "notes_root": str(notes_root),
                        "language": "zh-CN",
                    }
                )
            )

            cfg = load_config(
                config_path=explicit,
                cwd=root / "elsewhere",
                env={
                    "APRZ_ZOTERO_ATTACHMENT_ROOT": str(root / "wrong-pdfs"),
                    "APRZ_NOTES_ROOT": str(root / "wrong-notes"),
                },
            )

            self.assertEqual(cfg.zotero_attachment_root, pdf_root.resolve())
            self.assertEqual(cfg.notes_root, notes_root.resolve())
            self.assertEqual(cfg.language, "zh-CN")

    def test_env_paths_are_used_when_no_config_file_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_root = root / "pdfs"
            notes_root = root / "notes"
            pdf_root.mkdir()
            notes_root.mkdir()

            cfg = load_config(
                cwd=root,
                env={
                    "APRZ_ZOTERO_ATTACHMENT_ROOT": str(pdf_root),
                    "APRZ_NOTES_ROOT": str(notes_root),
                },
            )

            self.assertEqual(cfg.zotero_attachment_root, pdf_root.resolve())
            self.assertEqual(cfg.notes_root, notes_root.resolve())

    def test_missing_config_raises_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ConfigError):
                load_config(cwd=Path(tmp), env={})


if __name__ == "__main__":
    unittest.main()
