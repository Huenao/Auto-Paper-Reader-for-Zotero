import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from aprz import main


class CliInitTests(unittest.TestCase):
    def make_roots(self, root):
        pdf_root = root / "zotero"
        notes_root = root / "notes"
        pdf_root.mkdir()
        notes_root.mkdir()
        (pdf_root / "Paper.pdf").write_bytes(b"%PDF")
        return pdf_root, notes_root

    def run_main_json(self, argv, cwd, home):
        previous_cwd = Path.cwd()
        buffer = io.StringIO()
        try:
            os.chdir(cwd)
            with patch.dict(os.environ, {"HOME": str(home)}, clear=False):
                with redirect_stdout(buffer):
                    code = main(argv)
        finally:
            os.chdir(previous_cwd)
        self.assertEqual(code, 0)
        return json.loads(buffer.getvalue())

    def test_init_defaults_to_global_config_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_root, notes_root = self.make_roots(root)
            workspace = root / "workspace"
            home = root / "home"
            workspace.mkdir()

            result = self.run_main_json(
                [
                    "init",
                    "--zotero-attachment-root",
                    str(pdf_root),
                    "--notes-root",
                    str(notes_root),
                ],
                cwd=workspace,
                home=home,
            )

            expected = home / ".config" / "auto-paper-reader-for-zotero" / "config.json"
            self.assertEqual(Path(result["config_path"]).resolve(), expected.resolve())
            self.assertTrue(expected.exists())
            self.assertFalse((workspace / ".auto-paper-reader" / "config.json").exists())

    def test_init_project_scope_preserves_project_config_behavior(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_root, notes_root = self.make_roots(root)
            workspace = root / "workspace"
            home = root / "home"
            workspace.mkdir()

            result = self.run_main_json(
                [
                    "init",
                    "--scope",
                    "project",
                    "--zotero-attachment-root",
                    str(pdf_root),
                    "--notes-root",
                    str(notes_root),
                ],
                cwd=workspace,
                home=home,
            )

            expected = workspace / ".auto-paper-reader" / "config.json"
            self.assertEqual(Path(result["config_path"]).resolve(), expected.resolve())
            self.assertTrue(expected.exists())
            self.assertFalse((home / ".config" / "auto-paper-reader-for-zotero" / "config.json").exists())


if __name__ == "__main__":
    unittest.main()
