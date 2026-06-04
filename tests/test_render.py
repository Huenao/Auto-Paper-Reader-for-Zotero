import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from config import APRZConfig
from render_index import refresh_index
from render_note import render_note
from scan_pdfs import scan_pdfs


class RenderTests(unittest.TestCase):
    def make_config(self, root):
        pdf_root = root / "zotero"
        notes_root = root / "notes"
        pdf_root.mkdir()
        notes_root.mkdir()
        return APRZConfig(zotero_attachment_root=pdf_root, notes_root=notes_root)

    def test_render_note_creates_backup_and_refreshes_indexes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            pdf = cfg.zotero_attachment_root / "1.LLM" / "RAG" / "Self-RAG.pdf"
            pdf.parent.mkdir(parents=True)
            pdf.write_bytes(b"%PDF")
            index = scan_pdfs(cfg)
            item = index["items"][0]
            note_path = cfg.notes_root / item["note_rel_path"]
            note_path.parent.mkdir(parents=True)
            note_path.write_text("old note")

            result = render_note(
                cfg,
                {
                    "paper_id": item["paper_id"],
                    "title": "Self-RAG",
                    "authors": ["Asai et al."],
                    "year": 2023,
                    "venue": "",
                    "summary": "提出自反思式检索增强生成框架。",
                    "problem": "模型需要判断何时检索。",
                    "method_overview": "引入反思 token 控制检索与评价。",
                    "pipeline": "retrieve -> generate -> critique",
                    "innovations": ["检索触发自适应"],
                    "experiments": "开放域问答实验。",
                    "findings": "提升事实性。",
                    "limitations": "依赖检索质量。",
                    "value_for_user": "可借鉴到 RAG 代理。",
                    "follow_up_questions": ["如何迁移到中文语料？"],
                },
            )

            self.assertTrue(Path(result["note_abs_path"]).exists())
            self.assertIn("Self-RAG", note_path.read_text())
            backups = list((cfg.notes_root / "data" / "backups").glob("*.html"))
            self.assertEqual(len(backups), 1)
            self.assertTrue((cfg.notes_root / "data" / "note_index.json").exists())
            self.assertTrue((cfg.notes_root / "index.html").exists())

    def test_refresh_index_contains_unread_and_search_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            pdf = cfg.zotero_attachment_root / "Paper.pdf"
            pdf.write_bytes(b"%PDF")
            scan_pdfs(cfg)

            result = refresh_index(cfg)
            html = Path(result["index_abs_path"]).read_text()

            self.assertIn("Auto-Paper-Reader-for-Zotero", html)
            self.assertIn("Paper.pdf", html)
            self.assertIn("index.js", html)


if __name__ == "__main__":
    unittest.main()
