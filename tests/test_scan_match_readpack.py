import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import scan_pdfs as scan_module
from build_readpack import build_readpack, build_readpack_from_pdf_path
from config import APRZConfig
from match_paper import find_paper
from scan_pdfs import index_pdf_path, scan_pdfs


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

    def test_scan_reuses_fingerprint_for_unchanged_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            pdf = cfg.zotero_attachment_root / "Paper.pdf"
            pdf.write_bytes(b"%PDF")
            first = scan_pdfs(cfg)
            original_id = first["items"][0]["paper_id"]

            with patch.object(scan_module, "sha256_file", side_effect=AssertionError("should not rehash unchanged PDF")):
                second = scan_pdfs(cfg)

            self.assertEqual(second["items"][0]["paper_id"], original_id)
            self.assertEqual(second["items"][0]["content_fingerprint"], original_id)

    def test_scan_rehashes_changed_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            pdf = cfg.zotero_attachment_root / "Paper.pdf"
            pdf.write_bytes(b"%PDF")
            scan_pdfs(cfg)
            pdf.write_bytes(b"%PDF changed")
            os.utime(pdf, None)

            with patch.object(scan_module, "sha256_file", return_value="sha256:changed") as digest:
                second = scan_pdfs(cfg)

            digest.assert_called_once_with(pdf)
            self.assertEqual(second["items"][0]["paper_id"], "sha256:changed")

    def test_scan_force_hash_rehashes_unchanged_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            pdf = cfg.zotero_attachment_root / "Paper.pdf"
            pdf.write_bytes(b"%PDF")
            scan_pdfs(cfg)

            with patch.object(scan_module, "sha256_file", return_value="sha256:forced") as digest:
                second = scan_pdfs(cfg, force_hash=True)

            digest.assert_called_once_with(pdf)
            self.assertEqual(second["items"][0]["paper_id"], "sha256:forced")

    def test_index_pdf_path_updates_only_one_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            first = cfg.zotero_attachment_root / "A.pdf"
            second = cfg.zotero_attachment_root / "B.pdf"
            first.write_bytes(b"%PDF A")
            second.write_bytes(b"%PDF B")
            scan_pdfs(cfg)
            first.unlink()

            result = index_pdf_path(cfg, second)
            index = scan_module.load_paper_index(cfg)

            self.assertEqual(result["match_status"], "single_match")
            self.assertEqual(result["pdf_rel_path"], "B.pdf")
            self.assertEqual(len(index["items"]), 2)
            self.assertEqual([item["pdf_rel_path"] for item in index["items"]], ["A.pdf", "B.pdf"])
            self.assertEqual(index["items"][0]["source_status"], "available")

    def test_index_pdf_path_rejects_path_outside_attachment_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            outside = root / "outside" / "Paper.pdf"
            outside.parent.mkdir()
            outside.write_bytes(b"%PDF")

            result = index_pdf_path(cfg, outside)

            self.assertEqual(result["match_status"], "outside_attachment_root")
            self.assertIn("outside zotero_attachment_root", result["message"])

    def test_index_pdf_path_rejects_non_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            text = cfg.zotero_attachment_root / "Paper.txt"
            text.write_text("not a pdf")

            result = index_pdf_path(cfg, text)

            self.assertEqual(result["match_status"], "not_pdf")

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
            self.assertEqual(pack["source_resolution"], "query_match")
            self.assertTrue(pack["note_abs_path"].endswith("Paper.html"))

    def test_readpack_from_pdf_path_inside_attachment_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            pdf = cfg.zotero_attachment_root / "1.LLM" / "RAG" / "Self-RAG.pdf"
            pdf.parent.mkdir(parents=True)
            pdf.write_bytes(b"%PDF")

            pack = build_readpack_from_pdf_path(cfg, pdf, extractors=[])

            self.assertEqual(pack["extraction_status"], "no_extractor_available")
            self.assertEqual(pack["pdf_abs_path"], str(pdf.resolve()))
            self.assertEqual(pack["pdf_rel_path"], "1.LLM/RAG/Self-RAG.pdf")
            self.assertEqual(pack["note_rel_path"], "1.LLM/RAG/Self-RAG.html")
            self.assertTrue(pack["note_abs_path"].endswith("1.LLM/RAG/Self-RAG.html"))
            self.assertTrue(pack["full_text_path"].endswith(".txt"))
            self.assertEqual(pack["title"], "Self RAG")

    def test_readpack_from_pdf_path_rejects_path_outside_attachment_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            outside = root / "outside" / "Paper.pdf"
            outside.parent.mkdir()
            outside.write_bytes(b"%PDF")

            pack = build_readpack_from_pdf_path(cfg, outside, extractors=[])

            self.assertEqual(pack["match_status"], "outside_attachment_root")
            self.assertIn("outside zotero_attachment_root", pack["message"])
            self.assertEqual(pack["pdf_abs_path"], str(outside.resolve()))


if __name__ == "__main__":
    unittest.main()
