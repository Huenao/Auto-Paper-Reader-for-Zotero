import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from config import (
    APRZConfig,
    ConfigError,
    global_config_path,
    load_config,
    save_global_config,
    save_project_config,
)


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
                    "HOME": str(root / "home"),
                    "APRZ_ZOTERO_ATTACHMENT_ROOT": str(pdf_root),
                    "APRZ_NOTES_ROOT": str(notes_root),
                },
            )

            self.assertEqual(cfg.zotero_attachment_root, pdf_root.resolve())
            self.assertEqual(cfg.notes_root, notes_root.resolve())

    def test_save_global_config_uses_home_from_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_root = root / "pdfs"
            notes_root = root / "notes"
            pdf_root.mkdir()
            notes_root.mkdir()
            cfg = APRZConfig(zotero_attachment_root=pdf_root.resolve(), notes_root=notes_root.resolve())
            env = {"HOME": str(root / "home")}

            path = save_global_config(cfg, env=env)

            self.assertEqual(path, global_config_path(env))
            saved = json.loads(path.read_text())
            self.assertEqual(saved["zotero_attachment_root"], str(pdf_root.resolve()))
            self.assertEqual(saved["notes_root"], str(notes_root.resolve()))

    def test_project_config_takes_priority_over_global_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cwd = root / "workspace"
            cwd.mkdir()
            project_pdf = root / "project-pdfs"
            project_notes = root / "project-notes"
            global_pdf = root / "global-pdfs"
            global_notes = root / "global-notes"
            for path in [project_pdf, project_notes, global_pdf, global_notes]:
                path.mkdir()
            env = {"HOME": str(root / "home")}

            save_global_config(
                APRZConfig(zotero_attachment_root=global_pdf.resolve(), notes_root=global_notes.resolve()),
                env=env,
            )
            save_project_config(
                APRZConfig(zotero_attachment_root=project_pdf.resolve(), notes_root=project_notes.resolve()),
                cwd=cwd,
            )

            cfg = load_config(cwd=cwd, env=env)

            self.assertEqual(cfg.zotero_attachment_root, project_pdf.resolve())
            self.assertEqual(cfg.notes_root, project_notes.resolve())

    def test_missing_config_raises_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ConfigError):
                load_config(cwd=root, env={"HOME": str(root / "home")})


if __name__ == "__main__":
    unittest.main()
