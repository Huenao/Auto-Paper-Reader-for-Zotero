import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from path_utils import PathSafetyError, note_rel_path_for_pdf, require_within_root


class PathMappingTests(unittest.TestCase):
    def test_pdf_path_maps_to_mirrored_html_note_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_root = root / "zotero"
            pdf_path = pdf_root / "1.LLM" / "RAG" / "Self-RAG: Learning to Retrieve.pdf"
            pdf_path.parent.mkdir(parents=True)
            pdf_path.write_bytes(b"%PDF test")

            note_rel = note_rel_path_for_pdf(pdf_path, pdf_root)

            self.assertEqual(
                note_rel.as_posix(),
                "1.LLM/RAG/Self-RAG - Learning to Retrieve.html",
            )

    def test_rejects_write_path_outside_notes_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            notes_root = root / "notes"
            notes_root.mkdir()
            target = root / "outside.html"

            with self.assertRaises(PathSafetyError):
                require_within_root(target, notes_root)


if __name__ == "__main__":
    unittest.main()
