import unittest
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from journal_tracker import main as main_module
from journal_tracker.config import Config
from journal_tracker.discovery import DiscoveredPaper
from journal_tracker.storage import Paper, PaperStorage


def write_file(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


class JournalWorkflowTests(unittest.TestCase):
    def test_ingest_journal_updates_saves_new_papers_as_pending(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)
            config_dir = project_dir / "config"
            config_dir.mkdir()
            write_file(
                config_dir / "journals.yaml",
                """
journals:
  - name: "Journal A"
    priority: "core"
    track_from_year: 2026
""".strip(),
            )
            write_file(config_dir / "prompts.yaml", "{}")
            write_file(
                config_dir / "settings.yaml",
                """
database:
  path: "data/papers.db"
""".strip(),
            )
            config = Config(config_dir)

            fake_openalex = Mock()
            fake_openalex.search_journal_updates.return_value = [
                DiscoveredPaper(
                    title="Journal-first paper",
                    abstract="A paper from the red-list workflow.",
                    authors="Alice",
                    journal="Journal A",
                    published_date="2026",
                    link="https://example.org/journal-first",
                    doi="10.1000/journal-first",
                )
            ]
            fake_openalex.last_run_report = {"requested_queries": 1, "returned_papers": 1}

            with patch("journal_tracker.main.OpenAlexDiscovery", return_value=fake_openalex):
                with patch("sys.stdout", io.StringIO()):
                    saved_count = main_module.ingest_journal_updates(config, limit_per_journal=1)

            self.assertEqual(saved_count, 1)
            papers = PaperStorage(config.database_path).get_papers(limit=10)
            self.assertEqual(len(papers), 1)
            self.assertEqual(papers[0].title, "Journal-first paper")
            self.assertEqual(papers[0].relevance, "")
            self.assertEqual(papers[0].reason, "Pending AI screening")
            self.assertEqual(papers[0].source_type, "openalex")
            self.assertEqual(papers[0].screening_status, "pending")

    def test_fetch_journals_cli_returns_normally_when_papers_are_saved(self) -> None:
        with patch("sys.argv", ["main", "fetch-journals", "--limit-per-journal", "1"]):
            with patch("journal_tracker.main.ingest_journal_updates", return_value=2) as ingest:
                main_module.main()

        ingest.assert_called_once()

    def test_verify_coverage_cli_writes_report(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)
            config_dir = project_dir / "config"
            config_dir.mkdir()
            write_file(
                config_dir / "journals.yaml",
                """
journals:
  - name: "Communication Research"
    priority: "core"
    issn: ["0093-6502"]
    track_from_year: 2026
""".strip(),
            )
            write_file(config_dir / "prompts.yaml", "{}")
            write_file(config_dir / "settings.yaml", "database:\n  path: \"data/papers.db\"\n")

            fake_verifier = Mock()
            fake_verifier.verify.return_value = {
                "summary": {
                    "journals_checked": 1,
                    "total_missing_in_openalex": 0,
                    "total_missing_in_crossref": 0,
                    "errors": [],
                },
                "journals": [],
            }

            with patch("journal_tracker.main.CoverageVerifier", return_value=fake_verifier):
                stdout = io.StringIO()
                with patch("sys.stdout", stdout):
                    with patch("sys.argv", ["main", "--config", str(config_dir), "verify-coverage"]):
                        with self.assertRaises(SystemExit) as exit_info:
                            main_module.main()

            self.assertEqual(exit_info.exception.code, 0)
            report_path = project_dir / "data" / "reports" / "coverage_latest.json"
            self.assertTrue(report_path.exists())
            saved = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["summary"]["journals_checked"], 1)
            self.assertIn("Coverage report", stdout.getvalue())

    def test_weekly_run_cli_writes_report_and_runs_journal_first_steps(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)
            config_dir = project_dir / "config"
            data_dir = project_dir / "data"
            config_dir.mkdir()
            data_dir.mkdir()
            write_file(config_dir / "journals.yaml", "journals: []\n")
            write_file(config_dir / "prompts.yaml", "{}")
            write_file(config_dir / "settings.yaml", "database:\n  path: \"data/papers.db\"\n")

            storage = PaperStorage(data_dir / "papers.db")
            storage.add_paper(
                Paper(
                    title="Pending weekly paper",
                    journal="Communication Research",
                    link="https://example.org/pending-weekly-paper",
                    source_type="openalex",
                    screening_status="pending",
                )
            )

            calls = []

            def fake_fetch(config, limit_per_journal):
                calls.append(("fetch", limit_per_journal))
                return 3

            def fake_repair(config):
                calls.append(("repair", None))
                return {"pending": 1, "quarantined": 0}

            def fake_screen(config, limit):
                calls.append(("screen", limit))
                return 0

            def fake_update(config, refilter_limit):
                calls.append(("update", refilter_limit))
                return 0

            stdout = io.StringIO()
            with patch("journal_tracker.main.ingest_journal_updates", side_effect=fake_fetch):
                with patch("journal_tracker.main.repair_local_screening_queue", side_effect=fake_repair):
                    with patch("journal_tracker.main.screen_pending_papers", side_effect=fake_screen):
                        with patch("journal_tracker.main.update_public_workflow", side_effect=fake_update):
                            with patch("journal_tracker.main.generate_monthly_hotspots", return_value=data_dir / "hotspots.json"):
                                with patch("sys.argv", [
                                "main",
                                "--config",
                                str(config_dir),
                                "weekly-run",
                                "--limit-per-journal",
                                "7",
                                "--screen-limit",
                                "5",
                                "--max-screen-batches",
                                "1",
                                "--refilter-limit",
                                "2",
                                "--skip-coverage",
                                ]):
                                    with patch("sys.stdout", stdout):
                                        with self.assertRaises(SystemExit) as exit_info:
                                            main_module.main()

            self.assertEqual(exit_info.exception.code, 0)
            self.assertEqual(calls, [("fetch", 7), ("repair", None), ("screen", 5), ("update", 2)])
            report_path = data_dir / "reports" / "weekly_run_latest.json"
            self.assertTrue(report_path.exists())
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["steps"]["fetch_journals"]["saved_new_papers"], 3)
            self.assertEqual(report["steps"]["verify_coverage"], {"skipped": True})
            self.assertIn("Weekly report:", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
