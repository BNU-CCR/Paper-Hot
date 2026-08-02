import unittest
import csv
from pathlib import Path
from tempfile import TemporaryDirectory

from journal_tracker.storage import Paper, PaperStorage


class StorageWorkflowTests(unittest.TestCase):
    def test_storage_creates_missing_parent_directory(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "nested" / "data" / "papers.db"

            storage = PaperStorage(db_path)

            self.assertTrue(db_path.exists())
            self.assertEqual(storage.get_statistics()["total"], 0)

    def test_new_schema_tracks_source_and_screening_status(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            storage = PaperStorage(Path(tmp_dir) / "papers.db")
            paper_id = storage.add_paper(
                Paper(
                    title="Tracked paper",
                    journal="Communication Research",
                    link="https://example.org/tracked",
                    doi="10.1000/tracked",
                    relevance="",
                    source_type="openalex",
                    source_run_id="run-1",
                    tracked_journal="Communication Research",
                    openalex_id="W123",
                    screening_status="pending",
                )
            )

            paper = storage.get_paper_by_id(paper_id)

            self.assertEqual(paper.source_type, "openalex")
            self.assertEqual(paper.source_run_id, "run-1")
            self.assertEqual(paper.tracked_journal, "Communication Research")
            self.assertEqual(paper.openalex_id, "W123")
            self.assertEqual(paper.screening_status, "pending")
            self.assertTrue(paper.discovered_at)

    def test_duplicate_check_matches_either_link_or_doi(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            storage = PaperStorage(Path(tmp_dir) / "papers.db")
            storage.add_paper(
                Paper(
                    title="Original",
                    link="https://example.org/original",
                    doi="10.1000/same",
                    relevance="High",
                )
            )

            self.assertTrue(storage.paper_exists(link="https://example.org/other", doi="10.1000/same"))
            self.assertTrue(storage.paper_exists(link="https://example.org/original", doi="10.1000/other"))

    def test_pending_screening_queue_only_returns_openalex_pending_papers(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            storage = PaperStorage(Path(tmp_dir) / "papers.db")
            storage.add_paper(
                Paper(
                    title="Pending OpenAlex",
                    link="https://example.org/pending",
                    source_type="openalex",
                    screening_status="pending",
                )
            )
            storage.add_paper(
                Paper(
                    title="Quarantined",
                    link="https://example.org/quarantined",
                    source_type="semantic_scholar",
                    screening_status="quarantined",
                )
            )
            storage.add_paper(
                Paper(
                    title="Already screened",
                    link="https://example.org/screened",
                    source_type="openalex",
                    relevance="High",
                    screening_status="screened",
                )
            )

            papers = storage.get_pending_screening_papers()

            self.assertEqual([paper.title for paper in papers], ["Pending OpenAlex"])

    def test_repair_unscreened_queue_quarantines_non_redlist_papers(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            storage = PaperStorage(Path(tmp_dir) / "papers.db")
            redlist_id = storage.add_paper(
                Paper(
                    title="Redlist unscreened",
                    journal="Communication Research",
                    link="https://example.org/redlist",
                    relevance="Unscreened",
                )
            )
            dirty_id = storage.add_paper(
                Paper(
                    title="Dirty unscreened",
                    journal="Random Journal",
                    link="https://example.org/dirty",
                    relevance="Unscreened",
                )
            )

            report = storage.repair_unscreened_queue(
                tracked_journals=[
                    {
                        "name": "Communication Research",
                        "openalex_source_id": "S28604305",
                    }
                ]
            )

            redlist = storage.get_paper_by_id(redlist_id)
            dirty = storage.get_paper_by_id(dirty_id)
            self.assertEqual(report, {"pending": 1, "quarantined": 1})
            self.assertEqual(redlist.screening_status, "pending")
            self.assertEqual(redlist.source_type, "openalex")
            self.assertEqual(redlist.tracked_journal, "Communication Research")
            self.assertEqual(dirty.screening_status, "quarantined")
            self.assertEqual(dirty.source_type, "legacy")

    def test_csv_export_includes_source_and_screening_fields(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            storage = PaperStorage(base_dir / "papers.db")
            storage.add_paper(
                Paper(
                    title="Exported pending paper",
                    journal="Communication Research",
                    link="https://example.org/exported-pending-paper",
                    source_type="openalex",
                    source_run_id="run-1",
                    tracked_journal="Communication Research",
                    openalex_id="W123",
                    screening_status="pending",
                )
            )

            export_path = base_dir / "papers.csv"
            storage.export_to_csv(export_path)

            with export_path.open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))

            self.assertEqual(rows[0]["source_type"], "openalex")
            self.assertEqual(rows[0]["source_run_id"], "run-1")
            self.assertEqual(rows[0]["tracked_journal"], "Communication Research")
            self.assertEqual(rows[0]["openalex_id"], "W123")
            self.assertEqual(rows[0]["screening_status"], "pending")


if __name__ == "__main__":
    unittest.main()
