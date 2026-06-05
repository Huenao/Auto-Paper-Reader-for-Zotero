import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from config import APRZConfig
from extract_visuals import extract_visuals_for_pdf, extract_visuals_for_paper_id
from scan_pdfs import scan_pdfs


class FakeImage:
    def save(self, target, format="PNG"):
        data = b"\x89PNG\r\n\x1a\nfake"
        if hasattr(target, "write"):
            target.write(data)
            return
        Path(target).write_bytes(data)


class FakePictureItem:
    def __init__(self, caption, page_no):
        self._caption = caption
        self.prov = [SimpleNamespace(page_no=page_no)]

    def caption_text(self, doc=None):
        return self._caption

    def get_image(self, doc):
        return FakeImage()


class FakeTableItem(FakePictureItem):
    pass


class FakeDocument:
    def __init__(self):
        self._items = [
            (FakePictureItem("Figure 1: Overall architecture.", 2), 0),
            (FakeTableItem("Table 1: Main results.", 5), 0),
        ]

    def iterate_items(self):
        return iter(self._items)


class FakeConversion:
    document = FakeDocument()


class ExtractVisualsTests(unittest.TestCase):
    def make_config(self, root):
        pdf_root = root / "zotero"
        notes_root = root / "notes"
        pdf_root.mkdir()
        notes_root.mkdir()
        return APRZConfig(zotero_attachment_root=pdf_root, notes_root=notes_root)

    def test_extract_visuals_for_paper_id_writes_images_and_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            pdf = cfg.zotero_attachment_root / "Vision" / "Paper.pdf"
            pdf.parent.mkdir(parents=True)
            pdf.write_bytes(b"%PDF")
            item = scan_pdfs(cfg)["items"][0]

            with mock.patch(
                "extract_visuals.convert_pdf_with_docling",
                return_value=(FakeConversion(), FakePictureItem, FakeTableItem),
            ):
                result = extract_visuals_for_paper_id(cfg, item["paper_id"])

            self.assertEqual(result["visual_extraction_status"], "ok")
            self.assertEqual(result["paper_id"], item["paper_id"])
            self.assertEqual(len(result["visuals"]), 2)
            self.assertEqual(result["visuals"][0]["label"], "图 1")
            self.assertEqual(result["visuals"][0]["visual_type"], "figure")
            self.assertEqual(result["visuals"][1]["label"], "表 1")
            self.assertEqual(result["visuals"][1]["visual_type"], "table")
            self.assertTrue(Path(result["visuals"][0]["asset_path"]).exists())
            self.assertTrue(Path(result["visuals_json_path"]).exists())
            self.assertIn("/assets/papers/", result["visuals"][0]["asset_path"])

    def test_extract_visuals_degrades_when_docling_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            pdf = cfg.zotero_attachment_root / "Paper.pdf"
            pdf.write_bytes(b"%PDF")

            with mock.patch("extract_visuals.convert_pdf_with_docling", side_effect=ModuleNotFoundError("docling")):
                result = extract_visuals_for_pdf(cfg, pdf)

            self.assertEqual(result["visual_extraction_status"], "no_visual_extractor_available")
            self.assertEqual(result["visuals"], [])
            self.assertIn("Docling", result["message"])

    def test_extract_visuals_rejects_pdf_outside_attachment_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            outside = root / "outside" / "Paper.pdf"
            outside.parent.mkdir()
            outside.write_bytes(b"%PDF")

            result = extract_visuals_for_pdf(cfg, outside)

            self.assertEqual(result["visual_extraction_status"], "outside_attachment_root")
            self.assertIn("outside zotero_attachment_root", result["message"])


if __name__ == "__main__":
    unittest.main()
