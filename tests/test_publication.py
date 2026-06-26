import json
import io
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import main as main_module
from src.publication import PublicPaperExporter
from src.storage import Paper, PaperStorage


class PublicPaperExporterTests(unittest.TestCase):
    def test_public_export_only_includes_published_papers(self) -> None:
        tmp_dir = tempfile.mkdtemp()
        try:
            base_dir = Path(tmp_dir)
            storage = PaperStorage(base_dir / "papers.db")
            storage.add_paper(
                Paper(
                    title="Public LLM Paper",
                    authors="Alice Smith, Bob Lee",
                    abstract="Abstract",
                    journal="Journal of Communication",
                    published_date="2026-05-10",
                    link="https://example.org/public-paper",
                    doi="10.1000/public",
                    relevance="High",
                    reason="Strong match",
                    tags="LLM,platform",
                    summary="Public summary",
                    score=92,
                    is_public=True,
                )
            )
            storage.add_paper(
                Paper(
                    title="Private Medium Paper",
                    authors="Carol Jones",
                    journal="New Media & Society",
                    link="https://example.org/private-paper",
                    relevance="Medium",
                    reason="Not ready",
                    tags="private",
                    summary="Should stay private",
                    score=74,
                    is_public=False,
                )
            )

            export_path = base_dir / "public-papers.json"
            PublicPaperExporter(storage).export_json(export_path)

            exported = json.loads(export_path.read_text(encoding="utf-8"))

            self.assertEqual(len(exported), 1)
            self.assertEqual(exported[0]["title"], "Public LLM Paper")
            self.assertEqual(exported[0]["authors"], ["Alice Smith", "Bob Lee"])
            self.assertEqual(exported[0]["tags"], ["LLM", "platform"])
            self.assertEqual(exported[0]["score"], 92)
            self.assertEqual(exported[0]["source_url"], "https://example.org/public-paper")
            self.assertEqual(exported[0]["detail_slug"], "public-llm-paper")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_storage_can_toggle_publication_status(self) -> None:
        tmp_dir = tempfile.mkdtemp()
        try:
            base_dir = Path(tmp_dir)
            storage = PaperStorage(base_dir / "papers.db")
            paper_id = storage.add_paper(
                Paper(
                    title="Toggle Paper",
                    authors="Alice Smith",
                    journal="Journal A",
                    link="https://example.org/toggle-paper",
                    relevance="High",
                    is_public=False,
                )
            )

            storage.set_paper_publication(paper_id, True)
            public_papers = storage.get_public_papers()
            self.assertEqual(len(public_papers), 1)
            self.assertTrue(public_papers[0].is_public)

            storage.set_paper_publication(paper_id, False)
            public_papers = storage.get_public_papers()
            self.assertEqual(public_papers, [])
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_cli_can_publish_and_list_public_papers(self) -> None:
        tmp_dir = tempfile.mkdtemp()
        try:
            project_dir = Path(tmp_dir)
            config_dir = project_dir / "config"
            data_dir = project_dir / "data"
            config_dir.mkdir()
            data_dir.mkdir()
            (config_dir / "journals.yaml").write_text("journals: []\n", encoding="utf-8")
            (config_dir / "prompts.yaml").write_text("{}", encoding="utf-8")
            (config_dir / "settings.yaml").write_text("{}", encoding="utf-8")

            storage = PaperStorage(data_dir / "papers.db")
            paper_id = storage.add_paper(
                Paper(
                    title="CLI Publish Paper",
                    authors="Alice Smith",
                    journal="Journal A",
                    link="https://example.org/cli-publish-paper",
                    relevance="High",
                )
            )

            stdout = io.StringIO()
            with patch("sys.argv", ["main", "--config", str(config_dir), "publish", str(paper_id)]):
                with patch("sys.stdout", stdout):
                    with self.assertRaises(SystemExit) as exit_info:
                        main_module.main()
            self.assertEqual(exit_info.exception.code, 0)
            self.assertIn("已设为公开发布", stdout.getvalue())

            stdout = io.StringIO()
            with patch("sys.argv", ["main", "--config", str(config_dir), "list-public"]):
                with patch("sys.stdout", stdout):
                    main_module.main()
            self.assertIn("CLI Publish Paper", stdout.getvalue())
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_cli_publish_refreshes_public_json(self) -> None:
        tmp_dir = tempfile.mkdtemp()
        try:
            project_dir = Path(tmp_dir)
            config_dir = project_dir / "config"
            data_dir = project_dir / "data"
            config_dir.mkdir()
            data_dir.mkdir()
            (config_dir / "journals.yaml").write_text("journals: []\n", encoding="utf-8")
            (config_dir / "prompts.yaml").write_text("{}", encoding="utf-8")
            (config_dir / "settings.yaml").write_text("{}", encoding="utf-8")

            storage = PaperStorage(data_dir / "papers.db")
            paper_id = storage.add_paper(
                Paper(
                    title="Website Refresh Paper",
                    authors="Alice Smith",
                    journal="Journal A",
                    link="https://example.org/website-refresh-paper",
                    relevance="High",
                    summary="Ready for public website",
                )
            )

            with patch("sys.argv", ["main", "--config", str(config_dir), "publish", str(paper_id)]):
                with patch("sys.stdout", io.StringIO()):
                    with self.assertRaises(SystemExit) as exit_info:
                        main_module.main()

            self.assertEqual(exit_info.exception.code, 0)
            public_json = project_dir / "public" / "data" / "papers.json"
            exported = json.loads(public_json.read_text(encoding="utf-8"))
            self.assertEqual(len(exported), 1)
            self.assertEqual(exported[0]["title"], "Website Refresh Paper")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_cli_refilter_errors_updates_failed_filter_results(self) -> None:
        tmp_dir = tempfile.mkdtemp()
        try:
            project_dir = Path(tmp_dir)
            config_dir = project_dir / "config"
            data_dir = project_dir / "data"
            config_dir.mkdir()
            data_dir.mkdir()
            (config_dir / "journals.yaml").write_text("journals: []\n", encoding="utf-8")
            (config_dir / "prompts.yaml").write_text("{}", encoding="utf-8")
            (config_dir / "settings.yaml").write_text("{}", encoding="utf-8")

            storage = PaperStorage(data_dir / "papers.db")
            paper_id = storage.add_paper(
                Paper(
                    title="Failed Filter Paper",
                    authors="Alice Smith",
                    abstract="Computational communication abstract",
                    journal="Journal A",
                    link="https://example.org/failed-filter-paper",
                    relevance="Low",
                    reason="筛选出错: ThinkingBlock",
                )
            )

            fake_filter = patch("src.main.PaperFilter").start()
            fake_filter.return_value.filter_paper.return_value = {
                "relevance": "High",
                "reason": "计算传播相关",
                "tags": ["计算传播", "AI"],
                "summary": "使用 AI 方法研究传播问题。",
            }
            try:
                stdout = io.StringIO()
                with patch("sys.argv", ["main", "--config", str(config_dir), "refilter-errors"]):
                    with patch("sys.stdout", stdout):
                        with self.assertRaises(SystemExit) as exit_info:
                            main_module.main()
            finally:
                patch.stopall()

            self.assertEqual(exit_info.exception.code, 0)
            updated = PaperStorage(data_dir / "papers.db").get_paper_by_id(paper_id)
            self.assertEqual(updated.relevance, "High")
            self.assertEqual(updated.reason, "计算传播相关")
            self.assertEqual(updated.tags, "计算传播,AI")
            self.assertIn("已重筛 1 篇", stdout.getvalue())
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
