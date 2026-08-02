import json
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

from journal_tracker.readme_update import update_readme


class ReadmeUpdateTests(unittest.TestCase):
    def test_update_readme_replaces_preview_and_stats_idempotently(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            readme = root / "README.md"
            featured = root / "papers.json"
            all_papers = root / "all_papers.json"
            report = root / "weekly_run_latest.json"
            readme.write_text(
                "# Paper HOT\n\n"
                "<!-- paper-hot:auto-preview:start -->\nold preview\n"
                "<!-- paper-hot:auto-preview:end -->\n\n"
                "<!-- paper-hot:auto-stats:start -->\nold stats\n"
                "<!-- paper-hot:auto-stats:end -->\n",
                encoding="utf-8",
            )
            featured.write_text(
                json.dumps(
                    [
                        {
                            "id": 2,
                            "title": "New | Paper",
                            "journal": "Journal A",
                            "published_date": "2026-08-01",
                            "summary": "A useful summary",
                            "source_url": "https://example.org/new",
                        },
                        {
                            "id": 1,
                            "title": "Older Paper",
                            "journal": "Journal B",
                            "published_date": "2026-07-01",
                        },
                    ]
                ),
                encoding="utf-8",
            )
            all_papers.write_text(json.dumps([{"id": 1}, {"id": 2}, {"id": 3}]), encoding="utf-8")
            report.write_text(
                json.dumps(
                    {
                        "after": {
                            "total": 4,
                            "this_week": 3,
                            "relevance": {"High": 2, "Medium": 1, "Low": 1},
                            "screening_status": {"pending": 0, "screened": 4},
                        },
                        "steps": {
                            "verify_coverage": {
                                "total_openalex_dois": 3,
                                "total_crossref_dois": 4,
                                "total_matched": 3,
                                "total_missing_in_openalex": 1,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            now = datetime(2026, 8, 2, 13, 0, tzinfo=ZoneInfo("Asia/Shanghai"))

            update_readme(readme, featured, all_papers, report, now)
            first = readme.read_text(encoding="utf-8")
            update_readme(readme, featured, all_papers, report, now)
            second = readme.read_text(encoding="utf-8")

            self.assertEqual(first, second)
            self.assertIn("New \\| Paper", first)
            self.assertIn("2026-08-02 13:00 GMT+8", first)
            self.assertIn("| 数据库论文 | 4 |", first)
            self.assertIn("| 已发布精选 | 2 |", first)
            self.assertIn("Crossref 中尚缺 1", first)
            self.assertNotIn("old preview", first)
            self.assertNotIn("old stats", first)

    def test_update_readme_requires_markers(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            readme = root / "README.md"
            featured = root / "papers.json"
            all_papers = root / "all_papers.json"
            readme.write_text("# Missing markers", encoding="utf-8")
            featured.write_text("[]", encoding="utf-8")
            all_papers.write_text("[]", encoding="utf-8")

            with self.assertRaises(ValueError):
                update_readme(readme, featured, all_papers)


if __name__ == "__main__":
    unittest.main()
