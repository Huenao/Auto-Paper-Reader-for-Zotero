import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from config import APRZConfig
from extract_visuals import extract_visuals_for_pdf, extract_visuals_for_paper_id
from scan_pdfs import scan_pdfs


class ExtractVisualsTests(unittest.TestCase):
    def make_config(self, root):
        pdf_root = root / "zotero"
        notes_root = root / "notes"
        pdf_root.mkdir()
        notes_root.mkdir()
        return APRZConfig(zotero_attachment_root=pdf_root, notes_root=notes_root)

    def fake_poppler_run(self, png_color=(255, 255, 255)):
        def run(cmd, check, stdout=None, stderr=None, text=None):
            if Path(cmd[0]).name == "pdfinfo":
                return mock.Mock(stdout="Pages: 4\nPage size: 612 x 792 pts\n", stderr="")
            if Path(cmd[0]).name == "pdftoppm":
                from PIL import Image

                output_prefix = Path(cmd[-1])
                output_prefix.parent.mkdir(parents=True, exist_ok=True)
                Image.new("RGB", (800, 1000), png_color).save(output_prefix.with_suffix(".png"))
                return mock.Mock(stdout="", stderr="")
            raise AssertionError(f"unexpected command: {cmd}")

        return run

    def test_extract_visuals_crops_explicit_page_bbox_and_writes_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            pdf = cfg.zotero_attachment_root / "Vision" / "Paper.pdf"
            pdf.parent.mkdir(parents=True)
            pdf.write_bytes(b"%PDF")
            item = scan_pdfs(cfg)["items"][0]

            with mock.patch("extract_visuals._resolve_tool", side_effect=lambda name: f"/usr/bin/{name}"):
                with mock.patch("extract_visuals.subprocess.run", side_effect=self.fake_poppler_run()):
                    result = extract_visuals_for_paper_id(
                        cfg,
                        item["paper_id"],
                        page=2,
                        bbox="10,20,210,320",
                        label="图 1",
                        caption="Overall architecture.",
                        linked_section="method",
                    )

            self.assertEqual(result["visual_extraction_status"], "ok")
            self.assertEqual(result["paper_id"], item["paper_id"])
            self.assertEqual(result["page_count"], 4)
            self.assertEqual(len(result["visuals"]), 1)
            visual = result["visuals"][0]
            self.assertEqual(visual["label"], "图 1")
            self.assertEqual(visual["label_original"], "Figure 1")
            self.assertEqual(visual["caption"], "Overall architecture.")
            self.assertEqual(visual["page"], 2)
            self.assertEqual(visual["bbox"], [10, 20, 210, 320])
            self.assertEqual(visual["visual_type"], "figure")
            self.assertEqual(visual["crop_status"], "cropped_with_poppler_pillow")
            self.assertEqual(visual["linked_section"], "method")
            self.assertTrue(visual["asset_path"].endswith("figure-001-p002.png"))
            self.assertTrue(Path(visual["asset_path"]).exists())
            self.assertTrue(Path(result["visuals_json_path"]).exists())
            self.assertIn("/assets/papers/", visual["asset_path"])
            self.assertIn("/data/visuals/", result["visuals_json_path"])
            self.assertFalse((Path(result["visuals_json_path"]).parent / "page-renders" / "page-002.png").exists())

    def test_render_page_preview_writes_page_render_without_bbox(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            pdf = cfg.zotero_attachment_root / "Paper.pdf"
            pdf.write_bytes(b"%PDF")

            with mock.patch("extract_visuals._resolve_tool", side_effect=lambda name: f"/usr/bin/{name}"):
                with mock.patch("extract_visuals.subprocess.run", side_effect=self.fake_poppler_run()):
                    result = extract_visuals_for_pdf(cfg, pdf, page=2, render_page=True)

            self.assertEqual(result["visual_extraction_status"], "page_rendered")
            self.assertEqual(result["visuals"], [])
            self.assertTrue(result["page_render_abs_path"].endswith("page-002.png"))
            self.assertTrue(Path(result["page_render_abs_path"]).exists())

    def test_extract_visuals_requires_page_and_bbox_for_crop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            pdf = cfg.zotero_attachment_root / "Paper.pdf"
            pdf.write_bytes(b"%PDF")

            result = extract_visuals_for_pdf(cfg, pdf)

            self.assertEqual(result["visual_extraction_status"], "needs_page_and_bbox")
            self.assertIn("--page", result["message"])
            self.assertIn("--bbox", result["message"])

    def test_extract_visuals_reports_missing_poppler(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            pdf = cfg.zotero_attachment_root / "Paper.pdf"
            pdf.write_bytes(b"%PDF")

            with mock.patch("extract_visuals._resolve_tool", return_value=""):
                result = extract_visuals_for_pdf(cfg, pdf, page=1, bbox="1,1,10,10")

            self.assertEqual(result["visual_extraction_status"], "no_visual_extractor_available")
            self.assertIn("Poppler", result["message"])

    def test_extract_visuals_reports_missing_pillow(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            pdf = cfg.zotero_attachment_root / "Paper.pdf"
            pdf.write_bytes(b"%PDF")

            with mock.patch("extract_visuals._resolve_tool", side_effect=lambda name: f"/usr/bin/{name}"):
                with mock.patch("extract_visuals._load_pillow_image", side_effect=ModuleNotFoundError("PIL")):
                    result = extract_visuals_for_pdf(cfg, pdf, page=1, bbox="1,1,10,10")

            self.assertEqual(result["visual_extraction_status"], "no_visual_extractor_available")
            self.assertIn("Pillow", result["message"])

    def test_extract_visuals_rejects_invalid_bbox(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            pdf = cfg.zotero_attachment_root / "Paper.pdf"
            pdf.write_bytes(b"%PDF")

            with mock.patch("extract_visuals._resolve_tool", side_effect=lambda name: f"/usr/bin/{name}"):
                with mock.patch("extract_visuals.subprocess.run", side_effect=self.fake_poppler_run()):
                    result = extract_visuals_for_pdf(cfg, pdf, page=1, bbox="20,20,10,10")

            self.assertEqual(result["visual_extraction_status"], "invalid_bbox")
            self.assertIn("x2/y2", result["message"])

    def test_extract_visuals_rejects_pdf_outside_attachment_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            outside = root / "outside" / "Paper.pdf"
            outside.parent.mkdir()
            outside.write_bytes(b"%PDF")

            result = extract_visuals_for_pdf(cfg, outside, page=1, bbox="1,1,10,10")

            self.assertEqual(result["visual_extraction_status"], "outside_attachment_root")
            self.assertIn("outside zotero_attachment_root", result["message"])


if __name__ == "__main__":
    unittest.main()
