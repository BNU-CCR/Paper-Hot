import json
import shutil
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
