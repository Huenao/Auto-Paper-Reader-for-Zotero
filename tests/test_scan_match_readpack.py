import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build_readpack import build_readpack
from config import APRZConfig
from match_paper import find_paper
from scan_pdfs import scan_pdfs


class ScanMatchReadpackTests(unittest.TestCase):
    def make_config(self, root):
        pdf_root = root / "zotero"
        notes_root = root / "notes"
        pdf_root.mkdir()
        notes_root.mkdir()
        return APRZConfig(zotero_attachment_root=pdf_root, notes_root=notes_root)

    def test_scan_writes_index_and_marks_missing_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            pdf = cfg.zotero_attachment_root / "1.LLM" / "RAG" / "Self-RAG.pdf"
            pdf.parent.mkdir(parents=True)
            pdf.write_bytes(b"%PDF-1.4\nsample")

            first = scan_pdfs(cfg)
            self.assertEqual(first["summary"]["pdf_total"], 1)
            self.assertEqual(first["items"][0]["pdf_rel_path"], "1.LLM/RAG/Self-RAG.pdf")
            self.assertEqual(first["items"][0]["note_rel_path"], "1.LLM/RAG/Self-RAG.html")

            pdf.unlink()
            second = scan_pdfs(cfg)
            self.assertEqual(second["summary"]["source_missing"], 1)
            self.assertEqual(second["items"][0]["source_status"], "source_missing")

    def test_match_exact_fuzzy_and_multiple_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            for rel in ["A/Self-RAG.pdf", "B/Self-Reflection RAG.pdf"]:
                pdf = cfg.zotero_attachment_root / rel
                pdf.parent.mkdir(parents=True, exist_ok=True)
                pdf.write_bytes(b"%PDF")
            scan_pdfs(cfg)

            exact = find_paper(cfg, "A/Self-RAG.pdf")
            self.assertEqual(exact["match_status"], "single_match")
            self.assertEqual(exact["pdf_rel_path"], "A/Self-RAG.pdf")

            multiple = find_paper(cfg, "self")
            self.assertEqual(multiple["match_status"], "multiple_candidates")
            self.assertEqual(len(multiple["candidates"]), 2)

    def test_readpack_degrades_when_no_extractor_is_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            pdf = cfg.zotero_attachment_root / "Paper.pdf"
            pdf.write_bytes(b"%PDF")
            scan_pdfs(cfg)

            pack = build_readpack(cfg, "Paper", extractors=[])

            self.assertEqual(pack["extraction_status"], "no_extractor_available")
            self.assertEqual(pack["pdf_rel_path"], "Paper.pdf")
            self.assertTrue(pack["note_abs_path"].endswith("Paper.html"))


if __name__ == "__main__":
    unittest.main()
