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


if __name__ == "__main__":
    unittest.main()
