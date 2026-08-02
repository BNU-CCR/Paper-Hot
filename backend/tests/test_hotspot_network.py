"""Tests for the hotspot network pipeline.

Pure unit tests guard the heavy analysis imports; when numpy / scipy /
scikit-learn / igraph are unavailable (base CI install), these tests are
skipped rather than erroring. The integration test exercises the full
build_hotspot_network pipeline against a synthetic database with fake
embeddings, so it runs offline and deterministically.
"""

import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

try:
    import numpy as np  # noqa: F401
    from journal_tracker.hotspot_network import (
        _topic_jaccard,
        _reference_jaccard,
        _form_topics,
        _compute_heat_scores,
        build_hotspot_network,
    )
    HAVE_ANALYSIS = True
except ImportError:
    HAVE_ANALYSIS = False

from journal_tracker.config import Config
from journal_tracker.storage import Paper, PaperStorage


@unittest.skipUnless(HAVE_ANALYSIS, "analysis deps not installed")
class HotspotNetworkUnitTests(unittest.TestCase):
    def test_topic_jaccard_shared_topics(self):
        topics_a = [{"id": "T1", "name": "A"}, {"id": "T2", "name": "B"}]
        topics_b = [{"id": "T2", "name": "B"}, {"id": "T3", "name": "C"}]
        self.assertAlmostEqual(_topic_jaccard(topics_a, topics_b), 1 / 3)

    def test_topic_jaccard_empty_returns_zero(self):
        self.assertEqual(_topic_jaccard([], [{"id": "T1"}]), 0.0)

    def test_reference_jaccard(self):
        refs_a = ["W1", "W2", "W3"]
        refs_b = ["W2", "W3", "W4"]
        self.assertAlmostEqual(_reference_jaccard(refs_a, refs_b), 2 / 4)

    def test_form_topics_small_cluster_is_emerging(self):
        membership = {0: 0, 1: 0, 2: 1, 3: 1, 4: 1, 5: 1}
        candidates = [{"id": i} for i in range(6)]
        embeddings = np.zeros((6, 4), dtype=np.float32)
        topics = _form_topics(membership, candidates, embeddings, min_cluster_size=4)
        by_size = {t["size"]: t["status"] for t in topics}
        self.assertEqual(by_size[2], "emerging")
        self.assertEqual(by_size[4], "formal")

    def test_heat_scores_finite_and_bounded(self):
        anchor = date.today()
        candidates = []
        for i in range(6):
            candidates.append({
                "id": i + 1,
                "journal": f"Journal {i % 2}",
                "published_date": (anchor - timedelta(days=10)).isoformat(),
            })
        topics = [{
            "cluster_id": 0,
            "paper_indices": [0, 1, 2, 3],
            "size": 4,
            "status": "formal",
        }]
        scored = _compute_heat_scores(
            topics, candidates, recent_days=30, baseline_days=150,
            anchor_date=anchor, min_recent_for_hot=3,
        )
        topic = scored[0]
        self.assertEqual(topic["recent_count"], 4)
        self.assertGreaterEqual(topic["hot_score"], 0.0)
        self.assertLessEqual(topic["hot_score"], 1.0)
        self.assertTrue(np.isfinite(topic["hot_score"]))
        self.assertTrue(topic["is_hot"])


def _make_config(tmp: Path) -> Config:
    """Build a Config pointing into a temp dir, isolating DB and output."""
    config_dir = tmp / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "settings.yaml").write_text(
        "database:\n  path: data/papers.db\n", encoding="utf-8"
    )
    return Config(config_dir)


_N_CLUSTERS = 4
_CLUSTER_SIZE = 4


def _seed_papers(storage: PaperStorage) -> None:
    """Insert papers in clear clusters, all within the recent window."""
    anchor = date.today()
    for i in range(_N_CLUSTERS * _CLUSTER_SIZE):
        cluster = i // _CLUSTER_SIZE
        storage.add_paper(Paper(
            title=f"Paper {i} cluster {cluster}",
            authors="Author",
            abstract=f"Abstract about computational communication topic {cluster}.",
            journal=f"Journal {cluster}",
            published_date=(anchor - timedelta(days=7 + i % 5)).isoformat(),
            link=f"https://example.org/{i}",
            doi=f"10.1000/{i}",
            relevance="High" if i % 2 == 0 else "Medium",
            summary=f"Summary {i}",
            source_type="openalex",
            screening_status="screened",
        ))


def _fake_embeddings(candidates, storage, embedding_model, cache_dir):
    """Deterministic synthetic embeddings forming clean, orthogonal clusters."""
    rng = np.random.RandomState(0)
    # Mutually orthogonal unit centroids — within-cluster cosine ~1, cross ~0.
    centroids = np.zeros((_N_CLUSTERS, 8), dtype=np.float32)
    for c in range(_N_CLUSTERS):
        centroids[c, c] = 1.0
    rows = []
    for idx, _paper in enumerate(candidates):
        c = idx // _CLUSTER_SIZE
        rows.append(centroids[c] + rng.normal(0, 0.01, 8).astype(np.float32))
    return np.array(rows, dtype=np.float32)


class _FakeLabeler:
    def __init__(self, config):
        pass

    def label_topics(self, topics, candidates):
        for i, topic in enumerate(topics):
            topic["label_zh"] = f"主题{i}"
            topic["description"] = "测试描述"
            topic["why_hot"] = "测试说明"
            topic["keywords"] = ["keyword"]
        return topics


@unittest.skipUnless(HAVE_ANALYSIS, "analysis deps not installed")
class HotspotNetworkPipelineTests(unittest.TestCase):
    def test_full_pipeline_produces_valid_output(self):
        import journal_tracker.hotspot_network as hn

        # Patch embeddings and LLM labeling so the test runs offline
        hn._compute_embeddings = _fake_embeddings
        hn.TopicLabeler = _FakeLabeler

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            config = _make_config(tmp)
            storage = PaperStorage(config.database_path)
            _seed_papers(storage)

            output_dir = hn.build_hotspot_network(
                config,
                analysis_days=180,
                recent_days=30,
                baseline_days=150,
                max_topics=40,
            )

            self.assertTrue((output_dir / "graph.json").is_file())
            self.assertTrue((output_dir / "manifest.json").is_file())
            self.assertTrue((output_dir / "trends.json").is_file())

            graph = json.loads((output_dir / "graph.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(graph["nodes"]), 3)
            self.assertLessEqual(len(graph["nodes"]), 60)
            node_ids = {n["id"] for n in graph["nodes"]}
            for edge in graph["edges"]:
                self.assertIn(edge["source"], node_ids)
                self.assertIn(edge["target"], node_ids)

            # Validate via the validation module
            from journal_tracker.hotspot_validation import validate_hotspot_data
            self.assertEqual(validate_hotspot_data(output_dir), [])

    def test_deterministic_same_input_same_output(self):
        import journal_tracker.hotspot_network as hn

        hn._compute_embeddings = _fake_embeddings
        hn.TopicLabeler = _FakeLabeler

        results = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as td:
                tmp = Path(td)
                config = _make_config(tmp)
                storage = PaperStorage(config.database_path)
                _seed_papers(storage)
                output_dir = hn.build_hotspot_network(config, max_topics=40)
                graph = json.loads((output_dir / "graph.json").read_text(encoding="utf-8"))
                results.append(graph)

        first, second = results
        # Topic UUIDs are random each run, so compare stable structure:
        # cluster labels and fixed layout coordinates.
        def structural(graph):
            return sorted(
                (n["label"], round(n["x"], 2), round(n["y"], 2))
                for n in graph["nodes"]
            )

        self.assertEqual(structural(first), structural(second))
        self.assertEqual(
            {e["weight"] for e in first["edges"]},
            {e["weight"] for e in second["edges"]},
        )


if __name__ == "__main__":
    unittest.main()
