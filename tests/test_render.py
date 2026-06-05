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
            html = note_path.read_text()
            self.assertIn("Self-RAG", html)
            self.assertIn("paper-summary", html)
            self.assertIn("reading-status", html)
            self.assertIn("证据来源", html)
            self.assertIn("目录", html)
            self.assertIn("可借鉴到 RAG 代理。", html)
            backups = list((cfg.notes_root / "data" / "backups").glob("*.html"))
            self.assertEqual(len(backups), 1)
            self.assertTrue((cfg.notes_root / "data" / "note_index.json").exists())
            self.assertTrue((cfg.notes_root / "index.html").exists())

    def test_render_note_accepts_optional_vault_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            pdf = cfg.zotero_attachment_root / "Agents" / "Toolformer.pdf"
            pdf.parent.mkdir(parents=True)
            pdf.write_bytes(b"%PDF")
            index = scan_pdfs(cfg)
            item = index["items"][0]

            result = render_note(
                cfg,
                {
                    "paper_id": item["paper_id"],
                    "title": "Toolformer",
                    "summary": "让语言模型学会调用工具。",
                    "problem": "大模型需要外部工具增强。",
                    "method_overview": "用自监督方式学习 API 调用。",
                    "pipeline": "sample calls -> filter -> train",
                    "experiments": "语言建模和问答任务。",
                    "findings": "工具调用提升任务能力。",
                    "limitations": "工具选择有限。",
                    "value_for_user": "适合作为 agent 工具使用基线。",
                    "research_area": "Agent Systems",
                    "primary_subtopic": "Tool Use",
                    "priority": "High",
                    "reading_status": "fulltext-read",
                    "evidence_basis": "PDF full text extraction",
                    "next_action": "Compare with ReAct and API-Bank.",
                },
            )

            html = Path(result["note_abs_path"]).read_text()
            self.assertIn("Agent Systems", html)
            self.assertIn("Tool Use", html)
            self.assertIn("High", html)
            self.assertIn("fulltext-read", html)
            self.assertIn("PDF full text extraction", html)
            self.assertIn("Compare with ReAct and API-Bank.", html)

    def test_render_note_supports_markdown_like_blocks_and_visuals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            pdf = cfg.zotero_attachment_root / "Vision" / "Paper.pdf"
            pdf.parent.mkdir(parents=True)
            pdf.write_bytes(b"%PDF")
            index = scan_pdfs(cfg)
            item = index["items"][0]
            image = cfg.notes_root / "assets" / "papers" / "sha256-test" / "images" / "figure-001.png"
            image.parent.mkdir(parents=True)
            image.write_bytes(b"\x89PNG\r\n\x1a\n")

            result = render_note(
                cfg,
                {
                    "paper_id": item["paper_id"],
                    "title": "Visual Paper",
                    "summary": "带有结构化笔记和图表证据。",
                    "problem": "- 问题一\n- 问题二",
                    "method_overview": "> 关键直觉：先检测，再解释。\n\n方法分成两步。",
                    "pipeline": "1. 提取候选图表\n2. 写入 HTML note",
                    "experiments": "| 数据集 | 指标 |\n| --- | --- |\n| A | Accuracy |",
                    "findings": "图表证据帮助复核结论。",
                    "limitations": "视觉提取依赖本地工具。",
                    "value_for_user": "更适合复习论文。",
                    "visuals": [
                        {
                            "label": "图 1",
                            "caption": "整体方法流程。",
                            "page": 3,
                            "asset_path": str(image),
                            "visual_type": "figure",
                            "evidence_summary": "展示检测和解释两个阶段。",
                            "linked_section": "method",
                        }
                    ],
                },
            )

            html = Path(result["note_abs_path"]).read_text()
            self.assertIn('<ul class="note-list">', html)
            self.assertIn('<ol class="note-list ordered">', html)
            self.assertIn('<blockquote class="note-callout">', html)
            self.assertIn('<table class="note-table">', html)
            self.assertIn('<section id="visuals" class="note-section visual-section">', html)
            self.assertIn('<figure class="paper-visual">', html)
            self.assertIn('alt="图 1 整体方法流程。"', html)
            self.assertIn("展示检测和解释两个阶段。", html)

    def test_render_note_skips_visuals_outside_notes_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            pdf = cfg.zotero_attachment_root / "Paper.pdf"
            pdf.write_bytes(b"%PDF")
            index = scan_pdfs(cfg)
            item = index["items"][0]
            outside = root / "outside.png"
            outside.write_bytes(b"not really an image")

            result = render_note(
                cfg,
                {
                    "paper_id": item["paper_id"],
                    "title": "Unsafe Visual",
                    "summary": "测试外部图片路径。",
                    "problem": "问题。",
                    "method_overview": "方法。",
                    "pipeline": "流程。",
                    "experiments": "实验。",
                    "findings": "发现。",
                    "limitations": "限制。",
                    "value_for_user": "价值。",
                    "visuals": [
                        {
                            "label": "图 X",
                            "caption": "外部图片。",
                            "asset_path": str(outside),
                        }
                    ],
                },
            )

            html = Path(result["note_abs_path"]).read_text()
            self.assertIn("图片路径被安全策略跳过", html)
            self.assertNotIn(str(outside), html)

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
            self.assertIn("dashboard-shell", html)
            self.assertIn("categoryGrid", html)
            self.assertIn("statusFilters", html)
            self.assertIn("paperCardTemplate", html)
            self.assertIn("queueList", html)

    def test_refresh_index_embeds_preview_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            pdf = cfg.zotero_attachment_root / "1.LLM" / "RAG" / "Self-RAG.pdf"
            pdf.parent.mkdir(parents=True)
            pdf.write_bytes(b"%PDF")
            index = scan_pdfs(cfg)
            item = index["items"][0]
            render_note(
                cfg,
                {
                    "paper_id": item["paper_id"],
                    "title": "Self-RAG",
                    "summary": "提出自反思式检索增强生成框架，用于提高开放域问答事实性。",
                    "problem": "模型需要判断何时检索以及如何评价生成内容。",
                    "method_overview": "引入反思 token 控制检索、生成与 critique。",
                    "pipeline": "retrieve -> generate -> critique",
                    "experiments": "开放域问答和长文本生成实验。",
                    "findings": "提升事实性并降低不必要检索。",
                    "limitations": "依赖检索质量。",
                    "value_for_user": "可借鉴到 RAG 代理。",
                    "research_area": "RAG",
                    "primary_subtopic": "Self-Reflection",
                    "priority": "Medium",
                    "reading_status": "fulltext-read",
                    "evidence_basis": "Zotero indexed full text",
                    "next_action": "Compare retrieval triggers.",
                },
            )

            note_index = json.loads((cfg.notes_root / "data" / "note_index.json").read_text())
            item = note_index["items"][0]
            self.assertEqual(item["research_area"], "RAG")
            self.assertEqual(item["primary_subtopic"], "Self-Reflection")
            self.assertEqual(item["priority"], "Medium")
            self.assertEqual(item["reading_status"], "fulltext-read")
            self.assertEqual(item["evidence_basis"], "Zotero indexed full text")
            self.assertEqual(item["next_action"], "Compare retrieval triggers.")
            self.assertIn("判断何时检索", item["problem_preview"])
            self.assertIn("反思 token", item["method_preview"])
            self.assertIn("提升事实性", item["findings_preview"])


if __name__ == "__main__":
    unittest.main()
