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
    class GbkStrictStream:
        encoding = "gbk"

        def __init__(self) -> None:
            self.value = ""

        def write(self, text: str) -> int:
            text.encode(self.encoding)
            self.value += text
            return len(text)

        def flush(self) -> None:
            return None

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

    def test_cli_can_list_all_papers(self) -> None:
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
            storage.add_paper(
                Paper(
                    title="List All Paper",
                    authors="Alice Smith",
                    journal="Journal A",
                    link="https://example.org/list-all-paper",
                    relevance="High",
                    is_public=False,
                )
            )

            stdout = io.StringIO()
            with patch("sys.argv", ["main", "--config", str(config_dir), "list"]):
                with patch("sys.stdout", stdout):
                    main_module.main()

            output = stdout.getvalue()
            self.assertIn("全部论文: 1", output)
            self.assertIn("List All Paper", output)
            self.assertIn("public=0", output)
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

    def test_cli_publish_high_only_publishes_high_papers(self) -> None:
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
            storage.add_paper(
                Paper(
                    title="High Paper",
                    authors="Alice Smith",
                    journal="Journal A",
                    link="https://example.org/high-paper",
                    relevance="High",
                    is_public=False,
                )
            )
            storage.add_paper(
                Paper(
                    title="Low Paper",
                    authors="Bob Lee",
                    journal="Journal B",
                    link="https://example.org/low-paper",
                    relevance="Low",
                    is_public=False,
                )
            )
            storage.add_paper(
                Paper(
                    title="Test Paper",
                    authors="Test Author",
                    journal="Test Journal",
                    link="https://example.org/test-paper",
                    relevance="High",
                    is_public=False,
                )
            )

            stdout = io.StringIO()
            with patch("sys.argv", ["main", "--config", str(config_dir), "publish-high"]):
                with patch("sys.stdout", stdout):
                    with self.assertRaises(SystemExit) as exit_info:
                        main_module.main()

            self.assertEqual(exit_info.exception.code, 0)
            self.assertIn("已公开 High 论文: 1", stdout.getvalue())
            exported = json.loads(
                (project_dir / "public" / "data" / "papers.json").read_text(encoding="utf-8")
            )
            self.assertEqual([paper["title"] for paper in exported], ["High Paper"])
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_search_only_handles_non_gbk_titles(self) -> None:
        class FakeDiscovery:
            def __init__(self, api_key: str = "") -> None:
                self.api_key = api_key

            def search_recent_papers(self, limit: int = 20):
                return [
                    Paper(
                        title="Networked İstanbul communication",
                        authors="Alice Smith",
                        journal="Journal A",
                        published_date="2026",
                        link="https://example.org/non-gbk",
                        doi="10.1000/non-gbk",
                    )
                ]

        tmp_dir = tempfile.mkdtemp()
        try:
            config_dir = Path(tmp_dir) / "config"
            config_dir.mkdir()
            (config_dir / "journals.yaml").write_text("journals: []\n", encoding="utf-8")
            (config_dir / "prompts.yaml").write_text("{}", encoding="utf-8")
            (config_dir / "settings.yaml").write_text("{}", encoding="utf-8")
            stream = self.GbkStrictStream()

            with patch.object(main_module, "PaperDiscovery", FakeDiscovery):
                with patch("sys.stdout", stream):
                    main_module.search_only(main_module.Config(config_dir))

            self.assertIn("Networked ?stanbul communication", stream.value)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_cli_update_public_publishes_high_and_refreshes_json(self) -> None:
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
            storage.add_paper(
                Paper(
                    title="Workflow High Paper",
                    authors="Alice Smith",
                    journal="Journal A",
                    link="https://example.org/workflow-high-paper",
                    relevance="High",
                    is_public=False,
                )
            )
            storage.add_paper(
                Paper(
                    title="Workflow Low Paper",
                    authors="Bob Lee",
                    journal="Journal B",
                    link="https://example.org/workflow-low-paper",
                    relevance="Low",
                    is_public=False,
                )
            )

            stdout = io.StringIO()
            with patch("sys.argv", ["main", "--config", str(config_dir), "update-public"]):
                with patch("sys.stdout", stdout):
                    with self.assertRaises(SystemExit) as exit_info:
                        main_module.main()

            self.assertEqual(exit_info.exception.code, 0)
            self.assertIn("公开刷新完成", stdout.getvalue())
            exported = json.loads(
                (project_dir / "public" / "data" / "papers.json").read_text(encoding="utf-8")
            )
            self.assertEqual([paper["title"] for paper in exported], ["Workflow High Paper"])
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_full_pipeline_publishes_high_papers_to_public_json(self) -> None:
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

            class FakeDiscovery:
                def __init__(self, api_key: str = "") -> None:
                    self.api_key = api_key
                    self.last_run_report = {}

                def search_recent_papers(self, limit: int = 20):
                    self.last_run_report = {
                        "requested_queries": 1,
                        "successful_queries": 1,
                        "empty_queries": 0,
                        "failed_queries": 0,
                        "returned_papers": 1,
                    }
                    return [
                        Paper(
                            title="Pipeline High Paper",
                            authors="Alice Smith",
                            abstract="Computational communication abstract",
                            journal="Journal A",
                            published_date="2026-05-10",
                            link="https://example.org/pipeline-high-paper",
                            relevance="",
                        )
                    ]

            class FakeFilter:
                def filter_papers(self, papers):
                    filtered = []
                    for paper in papers:
                        filtered.append(
                            {
                                **paper,
                                "relevance": "High",
                                "reason": "Strong match",
                                "tags": ["methods"],
                                "summary": "Short summary",
                            }
                        )
                    return filtered

            class FakeNotifier:
                def send_paper_notification(self, paper):
                    return True

                def send_batch_notification(self, papers):
                    return True

            with patch.object(main_module, "PaperDiscovery", FakeDiscovery):
                with patch.object(main_module, "PaperFilter", FakeFilter):
                    with patch.object(main_module, "NotificationSender", FakeNotifier):
                        stdout = io.StringIO()
                        with patch("sys.stdout", stdout):
                            saved_count = main_module.run_full_pipeline(
                                main_module.Config(config_dir),
                                max_papers=1,
                            )

            self.assertEqual(saved_count, 1)
            self.assertIn("发现请求: 1", stdout.getvalue())
            self.assertIn("成功: 1", stdout.getvalue())
            exported = json.loads(
                (project_dir / "public" / "data" / "papers.json").read_text(encoding="utf-8")
            )
            self.assertEqual([paper["title"] for paper in exported], ["Pipeline High Paper"])
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_cli_workflow_status_reports_public_and_error_counts(self) -> None:
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
            storage.add_paper(
                Paper(
                    title="Public High Paper",
                    authors="Alice Smith",
                    journal="Journal A",
                    link="https://example.org/public-high-paper",
                    relevance="High",
                    reason="Good match",
                    is_public=True,
                )
            )
            storage.add_paper(
                Paper(
                    title="Failed Paper",
                    authors="Bob Lee",
                    journal="Journal B",
                    link="https://example.org/failed-paper",
                    relevance="Low",
                    reason="筛选出错: API",
                    is_public=False,
                )
            )

            stdout = io.StringIO()
            with patch("sys.argv", ["main", "--config", str(config_dir), "workflow-status"]):
                with patch("sys.stdout", stdout):
                    main_module.main()

            output = stdout.getvalue()
            self.assertIn("总计论文: 2", output)
            self.assertIn("已公开论文: 1", output)
            self.assertIn("筛选错误: 1", output)
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
