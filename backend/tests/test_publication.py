import json
import io
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from journal_tracker import main as main_module
from journal_tracker.publication import PublicPaperExporter
from journal_tracker.storage import Paper, PaperStorage


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
            paper_id = storage.add_paper(
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
                    method="计算传播学",
                    summary="Public summary",
                    score=92,
                    is_public=True,
                    volume="16",
                    issue="2",
                )
            )
            storage.replace_paper_author_enrichment(paper_id, [{
                "author_order": 0,
                "display_name": "Alice Smith",
                "affiliations": ["University A", "Institute B"],
                "match_method": "crossref_only",
                "match_confidence": 0.4,
            }, {
                "author_order": 1,
                "display_name": "Bob Lee",
                "affiliations": ["University A"],
                "match_method": "crossref_only",
                "match_confidence": 0.4,
            }])
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
            self.assertEqual(exported[0]["institutions"], ["University A", "Institute B"])
            self.assertEqual(exported[0]["tags"], ["LLM", "platform"])
            self.assertEqual(exported[0]["method"], "计算传播学")
            self.assertEqual(exported[0]["abstract"], "Abstract")
            self.assertEqual(exported[0]["score"], 92)
            self.assertEqual(exported[0]["source_url"], "https://example.org/public-paper")
            self.assertEqual(exported[0]["detail_slug"], "public-llm-paper")
            self.assertEqual(exported[0]["volume"], "16")
            self.assertEqual(exported[0]["issue"], "2")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_all_journal_export_includes_openalex_papers_and_excludes_quarantine(self) -> None:
        tmp_dir = tempfile.mkdtemp()
        try:
            base_dir = Path(tmp_dir)
            storage = PaperStorage(base_dir / "papers.db")
            storage.add_paper(
                Paper(
                    title="OpenAlex High Paper",
                    journal="Communication Research",
                    published_date="2026-06-10",
                    link="https://example.org/openalex-high",
                    relevance="High",
                    source_type="openalex",
                    screening_status="screened",
                    is_public=True,
                )
            )
            storage.add_paper(
                Paper(
                    title="OpenAlex Low Paper",
                    journal="Communication Research",
                    published_date="2026-05-10",
                    link="https://example.org/openalex-low",
                    relevance="Low",
                    source_type="openalex",
                    screening_status="screened",
                    is_public=False,
                )
            )
            storage.add_paper(
                Paper(
                    title="Quarantined Legacy Paper",
                    journal="Random Journal",
                    link="https://example.org/quarantined-legacy",
                    source_type="legacy",
                    screening_status="quarantined",
                )
            )

            export_path = base_dir / "all-papers.json"
            PublicPaperExporter(storage).export_all_journal_updates_json(export_path)
            exported = json.loads(export_path.read_text(encoding="utf-8"))

            self.assertEqual(
                [paper["title"] for paper in exported],
                ["OpenAlex High Paper", "OpenAlex Low Paper"],
            )
            self.assertEqual(exported[0]["screening_status"], "screened")
            self.assertEqual(exported[0]["source_type"], "openalex")
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

    def test_cli_workflow_status_reports_screening_queue_counts(self) -> None:
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
                    title="Pending Paper",
                    journal="Communication Research",
                    link="https://example.org/pending-paper",
                    source_type="openalex",
                    screening_status="pending",
                )
            )
            storage.add_paper(
                Paper(
                    title="Quarantined Paper",
                    journal="Random Journal",
                    link="https://example.org/quarantined-paper",
                    screening_status="quarantined",
                )
            )

            stdout = io.StringIO()
            with patch("sys.argv", ["main", "--config", str(config_dir), "workflow-status"]):
                with patch("sys.stdout", stdout):
                    main_module.main()

            output = stdout.getvalue()
            self.assertIn("Pending screening: 1", output)
            self.assertIn("Quarantined: 1", output)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_cli_repair_queue_marks_redlist_pending_and_other_quarantined(self) -> None:
        tmp_dir = tempfile.mkdtemp()
        try:
            project_dir = Path(tmp_dir)
            config_dir = project_dir / "config"
            data_dir = project_dir / "data"
            config_dir.mkdir()
            data_dir.mkdir()
            (config_dir / "journals.yaml").write_text(
                "journals:\n"
                "  - name: Communication Research\n"
                "    openalex_source_id: S28604305\n",
                encoding="utf-8",
            )
            (config_dir / "prompts.yaml").write_text("{}", encoding="utf-8")
            (config_dir / "settings.yaml").write_text("{}", encoding="utf-8")

            storage = PaperStorage(data_dir / "papers.db")
            redlist_id = storage.add_paper(
                Paper(
                    title="Redlist Legacy Paper",
                    journal="Communication Research",
                    link="https://example.org/redlist-legacy-paper",
                    relevance="Unscreened",
                )
            )
            dirty_id = storage.add_paper(
                Paper(
                    title="Dirty Legacy Paper",
                    journal="Random Journal",
                    link="https://example.org/dirty-legacy-paper",
                    relevance="Unscreened",
                )
            )

            stdout = io.StringIO()
            with patch("sys.argv", ["main", "--config", str(config_dir), "repair-queue"]):
                with patch("sys.stdout", stdout):
                    main_module.main()

            repaired_storage = PaperStorage(data_dir / "papers.db")
            redlist = repaired_storage.get_paper_by_id(redlist_id)
            dirty = repaired_storage.get_paper_by_id(dirty_id)
            self.assertEqual(redlist.screening_status, "pending")
            self.assertEqual(redlist.source_type, "openalex")
            self.assertEqual(dirty.screening_status, "quarantined")
            self.assertIn("Pending red-list papers: 1", stdout.getvalue())
            self.assertIn("Quarantined non-red-list papers: 1", stdout.getvalue())
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_cli_screen_pending_filters_only_pending_queue(self) -> None:
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
            pending_id = storage.add_paper(
                Paper(
                    title="Pending AI Paper",
                    abstract="Computational communication abstract",
                    journal="Communication Research",
                    link="https://example.org/pending-ai-paper",
                    source_type="openalex",
                    screening_status="pending",
                )
            )
            quarantined_id = storage.add_paper(
                Paper(
                    title="Quarantined Paper",
                    journal="Random Journal",
                    link="https://example.org/quarantined-ai-paper",
                    screening_status="quarantined",
                )
            )

            fake_filter = patch("journal_tracker.main.PaperFilter").start()
            fake_filter.return_value.filter_paper.return_value = {
                "relevance": "High",
                "reason": "Strong computational communication match",
                "tags": ["computational communication"],
                "summary": "Uses computational methods.",
                "method": "计算传播学",
            }
            try:
                stdout = io.StringIO()
                with patch("sys.argv", ["main", "--config", str(config_dir), "screen-pending"]):
                    with patch("sys.stdout", stdout):
                        with self.assertRaises(SystemExit) as exit_info:
                            main_module.main()
            finally:
                patch.stopall()

            self.assertEqual(exit_info.exception.code, 0)
            updated_storage = PaperStorage(data_dir / "papers.db")
            pending = updated_storage.get_paper_by_id(pending_id)
            quarantined = updated_storage.get_paper_by_id(quarantined_id)
            self.assertEqual(pending.screening_status, "screened")
            self.assertEqual(pending.relevance, "High")
            self.assertEqual(pending.method, "计算传播学")
            self.assertEqual(quarantined.screening_status, "quarantined")
            self.assertIn("Screened pending papers: 1", stdout.getvalue())
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_cli_screen_pending_marks_error_and_continues_batch(self) -> None:
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
            failed_id = storage.add_paper(
                Paper(
                    title="Broken AI Response Paper",
                    journal="Communication Research",
                    link="https://example.org/broken-ai-response",
                    source_type="openalex",
                    screening_status="pending",
                )
            )
            screened_id = storage.add_paper(
                Paper(
                    title="Next Paper",
                    abstract="Computational communication abstract",
                    journal="Communication Research",
                    link="https://example.org/next-paper",
                    source_type="openalex",
                    screening_status="pending",
                )
            )

            fake_filter = patch("journal_tracker.main.PaperFilter").start()
            fake_filter.return_value.filter_paper.side_effect = [
                ValueError("truncated JSON"),
                {
                    "relevance": "High",
                    "reason": "Strong computational communication match",
                    "tags": ["computational communication"],
                    "summary": "Uses computational methods.",
                    "method": "计算传播学",
                },
            ]
            try:
                stdout = io.StringIO()
                with patch("sys.argv", ["main", "--config", str(config_dir), "screen-pending", "--limit", "2"]):
                    with patch("sys.stdout", stdout):
                        with self.assertRaises(SystemExit) as exit_info:
                            main_module.main()
            finally:
                patch.stopall()

            self.assertEqual(exit_info.exception.code, 0)
            updated_storage = PaperStorage(data_dir / "papers.db")
            updated_papers = [
                updated_storage.get_paper_by_id(failed_id),
                updated_storage.get_paper_by_id(screened_id),
            ]
            self.assertEqual(
                sorted(paper.screening_status for paper in updated_papers),
                ["error", "screened"],
            )
            error_paper = next(paper for paper in updated_papers if paper.screening_status == "error")
            screened_paper = next(paper for paper in updated_papers if paper.screening_status == "screened")
            self.assertIn("筛选出错", error_paper.reason)
            self.assertEqual(screened_paper.relevance, "High")
            self.assertEqual(screened_paper.method, "计算传播学")
            self.assertIn("Screening errors: 1", stdout.getvalue())
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_cli_label_methods_backfills_screened_papers(self) -> None:
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
            unlabeled_id = storage.add_paper(
                Paper(
                    title="No Method Label Yet",
                    journal="Communication Research",
                    link="https://example.org/unlabeled",
                    relevance="High",
                    source_type="openalex",
                    screening_status="screened",
                )
            )
            labeled_id = storage.add_paper(
                Paper(
                    title="Already Labeled",
                    journal="Communication Research",
                    link="https://example.org/labeled",
                    relevance="Medium",
                    method="综述",
                    source_type="openalex",
                    screening_status="screened",
                )
            )

            fake_filter = patch("journal_tracker.main.PaperFilter").start()
            fake_filter.return_value.label_method.return_value = "计算传播学"
            try:
                stdout = io.StringIO()
                with patch("sys.argv", ["main", "--config", str(config_dir), "label-methods"]):
                    with patch("sys.stdout", stdout):
                        main_module.main()
            finally:
                patch.stopall()

            updated_storage = PaperStorage(data_dir / "papers.db")
            unlabeled = updated_storage.get_paper_by_id(unlabeled_id)
            labeled = updated_storage.get_paper_by_id(labeled_id)
            self.assertEqual(unlabeled.method, "计算传播学")
            self.assertEqual(labeled.method, "综述")
            self.assertIn("Backfill complete", stdout.getvalue())
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_cli_label_methods_reports_failures_without_stopping(self) -> None:
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
                    title="Method Label Fails",
                    journal="Communication Research",
                    link="https://example.org/fails",
                    relevance="High",
                    source_type="openalex",
                    screening_status="screened",
                )
            )

            fake_filter = patch("journal_tracker.main.PaperFilter").start()
            fake_filter.return_value.label_method.side_effect = ValueError("API timeout")
            try:
                stdout = io.StringIO()
                with patch("sys.argv", ["main", "--config", str(config_dir), "label-methods"]):
                    with patch("sys.stdout", stdout):
                        main_module.main()
            finally:
                patch.stopall()

            updated_storage = PaperStorage(data_dir / "papers.db")
            paper = updated_storage.get_paper_by_id(paper_id)
            self.assertEqual(paper.method, "")
            self.assertIn("Method label failed", stdout.getvalue())
            self.assertIn("1 failed", stdout.getvalue())
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

            fake_filter = patch("journal_tracker.main.PaperFilter").start()
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
