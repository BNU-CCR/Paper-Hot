import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from journal_tracker.config import Config
from journal_tracker.hotspots import MonthlyHotspotGenerator, generate_monthly_hotspots
from journal_tracker.storage import Paper, PaperStorage


class MonthlyHotspotTests(unittest.TestCase):
    def test_validation_keeps_only_known_paper_ids_and_caps_topics(self):
        topics = MonthlyHotspotGenerator._validate_topics(
            [
                {"title": "AI", "description": "A", "paper_ids": [1, 999]},
                {"title": "平台", "description": "B", "paper_ids": [2]},
                {"title": "网络", "description": "C", "paper_ids": [3]},
            ],
            {1, 2, 3},
        )
        self.assertEqual([topic["paper_ids"] for topic in topics], [[1], [2], [3]])

    def test_generation_exports_only_recent_public_papers(self):
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_dir = root / "config"
            config_dir.mkdir()
            (config_dir / "journals.yaml").write_text("journals: []\n", encoding="utf-8")
            (config_dir / "prompts.yaml").write_text("{}\n", encoding="utf-8")
            (config_dir / "settings.yaml").write_text("database:\n  path: data/papers.db\n", encoding="utf-8")
            config = Config(config_dir)
            storage = PaperStorage(config.database_path)
            for index, published_date in enumerate(("2026-07-30", "2026-07-20", "2026-06-01"), start=1):
                paper_id = storage.add_paper(Paper(
                    title=f"Paper {index}", journal="Journal", published_date=published_date,
                    link=f"https://example.org/{index}", relevance="High", summary="Summary",
                    screening_status="screened",
                ))
                storage.set_paper_publication(paper_id, True)

            generator = Mock()
            generator.generate.return_value = [
                {"title": "议题一", "description": "说明", "paper_ids": [1]},
                {"title": "议题二", "description": "说明", "paper_ids": [2]},
                {"title": "议题三", "description": "说明", "paper_ids": [1, 2]},
            ]
            with patch("journal_tracker.hotspots.MonthlyHotspotGenerator", return_value=generator):
                output_path = generate_monthly_hotspots(config)

            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["period_start"], "2026-06-30")
            self.assertEqual(payload["period_end"], "2026-07-30")
            self.assertEqual(payload["source_paper_count"], 2)
            self.assertEqual(len(payload["topics"]), 3)
            self.assertEqual(len(generator.generate.call_args.args[0]), 2)


if __name__ == "__main__":
    unittest.main()
