"""Tests for the paper_features table and analysis query methods."""

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from journal_tracker.storage import Paper, PaperFeatures, PaperStorage


class PaperFeaturesStorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.storage = PaperStorage(Path(self.tmp.name) / "test.db")

    def tearDown(self):
        self.tmp.cleanup()

    def _add_paper(self, pid_note: str = "", days_ago: int = 5) -> int:
        anchor = date.today() - timedelta(days=days_ago)
        return self.storage.add_paper(Paper(
            title=f"Title {pid_note}",
            authors="Author",
            abstract=f"Abstract {pid_note}",
            journal=f"Journal {pid_note}",
            published_date=anchor.isoformat(),
            link=f"https://example.org/{pid_note}-{days_ago}",
            doi=f"10.1000/{pid_note}-{days_ago}",
            relevance="High",
            source_type="openalex",
            screening_status="screened",
        ))

    def test_upsert_and_get_roundtrip(self):
        pid = self._add_paper("one")
        features = PaperFeatures(
            paper_id=pid,
            text_hash="abc123",
            embedding_model="test-model",
            embedding_dim=4,
            embedding_bytes=b"\x00\x00\x00\x00",
            openalex_topics_json='[{"id": "T1", "name": "A"}]',
            openalex_keywords_json='[{"name": "kw"}]',
            referenced_works_json='["W1"]',
            cited_by_count=5,
            is_retracted=False,
        )
        self.assertTrue(self.storage.upsert_paper_features(features))

        loaded = self.storage.get_paper_features(pid)
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded.paper_id, pid)
        self.assertEqual(loaded.text_hash, "abc123")
        self.assertEqual(loaded.embedding_model, "test-model")
        self.assertEqual(loaded.embedding_dim, 4)
        self.assertEqual(loaded.embedding_bytes, b"\x00\x00\x00\x00")
        self.assertIn("T1", loaded.openalex_topics_json)
        self.assertEqual(loaded.cited_by_count, 5)

    def test_upsert_overwrites_existing(self):
        pid = self._add_paper("two")
        first = PaperFeatures(paper_id=pid, text_hash="v1", embedding_dim=2, embedding_bytes=b"aa")
        second = PaperFeatures(paper_id=pid, text_hash="v2", embedding_dim=2, embedding_bytes=b"bb")
        self.storage.upsert_paper_features(first)
        self.storage.upsert_paper_features(second)
        loaded = self.storage.get_paper_features(pid)
        assert loaded is not None
        self.assertEqual(loaded.text_hash, "v2")
        self.assertEqual(loaded.embedding_bytes, b"bb")

    def test_get_missing_returns_none(self):
        self.assertIsNone(self.storage.get_paper_features(99999))

    def test_analysis_candidates_filters_by_relevance_and_window(self):
        recent = self._add_paper("recent", days_ago=3)
        old = self._add_paper("old", days_ago=60)
        low = self.storage.add_paper(Paper(
            title="Low paper", abstract="x", journal="J",
            published_date=(date.today() - timedelta(days=1)).isoformat(),
            link="https://example.org/low", doi="10.1000/low",
            relevance="Low", source_type="openalex", screening_status="screened",
        ))

        # recent + old are High and within window → both returned
        candidates = self.storage.get_analysis_candidates(
            min_date=(date.today() - timedelta(days=180)).isoformat(),
        )
        ids = {c["id"] for c in candidates}
        self.assertIn(recent, ids)
        self.assertIn(old, ids)
        self.assertNotIn(low, ids)

        # Narrow window excludes the old paper
        narrow = self.storage.get_analysis_candidates(
            min_date=(date.today() - timedelta(days=7)).isoformat(),
        )
        narrow_ids = {c["id"] for c in narrow}
        self.assertIn(recent, narrow_ids)
        self.assertNotIn(old, narrow_ids)

    def test_analysis_candidates_excludes_retracted(self):
        pid = self._add_paper("retracted")
        self.storage.upsert_paper_features(PaperFeatures(
            paper_id=pid, is_retracted=True,
        ))
        candidates = self.storage.get_analysis_candidates(
            min_date=(date.today() - timedelta(days=180)).isoformat(),
        )
        self.assertNotIn(pid, {c["id"] for c in candidates})

    def test_get_papers_missing_features(self):
        pid_with = self._add_paper("has-features")
        pid_without = self._add_paper("no-features")
        self.storage.upsert_paper_features(PaperFeatures(
            paper_id=pid_with,
            embedding_dim=2,
            embedding_bytes=b"aa",
        ))
        missing = self.storage.get_papers_missing_features()
        self.assertIn(pid_without, missing)
        self.assertNotIn(pid_with, missing)

    def test_compute_text_hash_is_deterministic(self):
        h1 = self.storage.compute_text_hash("Title", "Abstract", "model")
        h2 = self.storage.compute_text_hash("Title", "Abstract", "model")
        h3 = self.storage.compute_text_hash("Title", "Changed", "model")
        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, h3)


if __name__ == "__main__":
    unittest.main()
