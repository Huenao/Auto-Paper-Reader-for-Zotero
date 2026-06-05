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
        code, text = self.run_main(argv, cwd, home)
        self.assertEqual(code, 0)
        return json.loads(text)

    def run_main(self, argv, cwd, home):
        previous_cwd = Path.cwd()
        buffer = io.StringIO()
        try:
            os.chdir(cwd)
            with patch.dict(os.environ, {"HOME": str(home)}, clear=False):
                with redirect_stdout(buffer):
                    code = main(argv)
        finally:
            os.chdir(previous_cwd)
        return code, buffer.getvalue()

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

    def test_readpack_accepts_direct_pdf_path_under_attachment_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_root, notes_root = self.make_roots(root)
            workspace = root / "workspace"
            home = root / "home"
            workspace.mkdir()
            self.run_main_json(
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

            result = self.run_main_json(
                ["readpack", "--pdf-path", str(pdf_root / "Paper.pdf"), "--json"],
                cwd=workspace,
                home=home,
            )

            self.assertEqual(result["pdf_rel_path"], "Paper.pdf")
            self.assertEqual(result["note_rel_path"], "Paper.html")
            self.assertEqual(result["source_resolution"], "direct_pdf_path")

    def test_readpack_rejects_direct_pdf_path_outside_attachment_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_root, notes_root = self.make_roots(root)
            outside = root / "outside" / "Other.pdf"
            outside.parent.mkdir()
            outside.write_bytes(b"%PDF")
            workspace = root / "workspace"
            home = root / "home"
            workspace.mkdir()
            self.run_main_json(
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

            code, text = self.run_main(
                ["readpack", "--pdf-path", str(outside), "--json"],
                cwd=workspace,
                home=home,
            )
            result = json.loads(text)

            self.assertEqual(code, 2)
            self.assertEqual(result["match_status"], "outside_attachment_root")
            self.assertIn("outside zotero_attachment_root", result["message"])


if __name__ == "__main__":
    unittest.main()
