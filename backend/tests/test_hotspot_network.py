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
from types import SimpleNamespace
from unittest.mock import patch

try:
    import numpy as np  # noqa: F401
    from journal_tracker.hotspot_network import (
        _topic_jaccard,
        _reference_jaccard,
        _form_topics,
        _compute_heat_scores,
        _compute_topic_graph,
        _compute_anchor_positions,
        _ensure_output_dirs,
        _build_output,
        _compute_umap,
        _paper_recency_heat,
        _match_topics,
        _load_previous_topics,
        build_hotspot_network,
    )
    HAVE_ANALYSIS = True
except ImportError:
    HAVE_ANALYSIS = False

from journal_tracker.config import Config
from journal_tracker.hotspot_labels import TopicLabeler, normalize_keywords
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
        by_size = {t["size"]: t["cluster_kind"] for t in topics}
        self.assertEqual(by_size[2], "emerging")
        self.assertEqual(by_size[4], "formal")

    def test_topic_match_inherits_previous_human_label(self):
        current = [{
            "cluster_id": 0,
            "paper_indices": [0, 1],
            "centroid": np.array([1.0, 0.0]),
        }]
        previous = [{
            "topic_id": "topic_stable",
            "paper_ids": [1, 2],
            "centroid": [1.0, 0.0],
            "label_zh": "平台算法与政治传播生态",
            "description": "旧描述",
            "why_hot": "旧说明",
            "keywords": ["平台算法"],
            "_label_fingerprint": "old-fingerprint",
        }]
        candidates = [{"id": 1}, {"id": 2}]

        matched = _match_topics(
            current, previous, np.array([[1.0, 0.0], [1.0, 0.0]]),
            candidates, match_threshold=0.5, drift_threshold=0.3,
        )

        self.assertEqual(matched[0]["topic_id"], "topic_stable")
        self.assertEqual(matched[0]["label_zh"], "平台算法与政治传播生态")
        self.assertEqual(matched[0]["_label_fingerprint"], "old-fingerprint")

    def test_previous_topics_recover_labels_from_legacy_detail_files(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = Path(td) / "hotspots"
            (data_dir / "topics").mkdir(parents=True)
            (data_dir / "graph.json").write_text(json.dumps({
                "topics_meta": [{
                    "topic_id": "topic_stable",
                    "paper_ids": [1, 2],
                    "centroid": [1.0, 0.0],
                }],
                "points": [{
                    "id": "topic_stable",
                    "type": "topic",
                    "label": "topic_stable",
                }],
            }), encoding="utf-8")
            (data_dir / "topics/topic_stable.json").write_text(json.dumps({
                "topic_id": "topic_stable",
                "label": "平台算法与政治传播生态",
                "description": "旧描述",
                "why_hot": "旧说明",
                "keywords": ["平台算法"],
            }), encoding="utf-8")

            previous = _load_previous_topics(data_dir)

            self.assertEqual(previous[0]["label_zh"], "平台算法与政治传播生态")
            self.assertEqual(previous[0]["description"], "旧描述")
            self.assertEqual(previous[0]["keywords"], ["平台算法"])

    def test_topic_graph_and_anchor_positions_use_cluster_ids(self):
        # Regression: _compute_topic_graph previously keyed edges by the
        # enumerate index of each topic, while _compute_anchor_positions and
        # _build_output look edges/anchors up by cluster_id. With non-contiguous
        # Leiden cluster ids (e.g. 10/20/30) the two never matched, so the real
        # pipeline crashed with KeyError at layout time.
        topics = [
            {"cluster_id": 10, "topic_id": "topic_a", "paper_indices": [0, 1, 2, 3], "size": 4, "status": "formal"},
            {"cluster_id": 20, "topic_id": "topic_b", "paper_indices": [4, 5, 6, 7], "size": 4, "status": "formal"},
            {"cluster_id": 30, "topic_id": "topic_c", "paper_indices": [8, 9, 10, 11], "size": 4, "status": "formal"},
        ]
        candidates = [{"id": i} for i in range(12)]
        # paper 0 -> cluster 10, paper 4 -> cluster 20, paper 8 -> cluster 30
        paper_edges = [(0, 4, 0.5), (4, 8, 0.5)]
        edges = _compute_topic_graph(topics, candidates, paper_edges)
        self.assertEqual({(a, b) for a, b, _ in edges}, {(10, 20), (20, 30)})

        # Anchors sit at the centroid of each topic's member UMAP coords.
        umap_coords = np.array([[float(i), float(i + 1)] for i in range(12)])
        anchors = _compute_anchor_positions(topics, umap_coords)
        self.assertEqual(set(anchors.keys()), {10, 20, 30})
        # members 0..3 of coords [(0,1),(1,2),(2,3),(3,4)] -> centroid (1.5, 2.5)
        self.assertEqual(anchors[10], (1.5, 2.5))

    def test_umap_is_deterministic_and_normalized(self):
        rng = np.random.RandomState(7)
        embeddings = rng.normal(0, 1, (40, 8)).astype(np.float32)
        a = _compute_umap(embeddings, n_neighbors=8, min_dist=0.1, random_state=42)
        b = _compute_umap(embeddings, n_neighbors=8, min_dist=0.1, random_state=42)
        np.testing.assert_allclose(a, b)
        self.assertEqual(a.shape, (40, 2))
        self.assertLessEqual(float(np.max(np.abs(a))), 1.0)

    def test_paper_recency_heat_decays_with_age(self):
        anchor = date.today()
        candidates = [
            {"id": 1, "published_date": anchor.isoformat()},
            {"id": 2, "published_date": (anchor - timedelta(days=100)).isoformat()},
            {"id": 3, "published_date": "not-a-date"},
        ]
        heats = _paper_recency_heat(candidates, anchor)
        self.assertGreater(heats[0], heats[1])
        self.assertEqual(heats[2], 50.0)

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
            "cluster_kind": "formal",
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
        # Rate-based growth: 4 papers over 30 days, none in the 150-day baseline.
        self.assertEqual(topic["status"], "hot")
        self.assertAlmostEqual(topic["recent_rate"], 4 / 30, places=4)
        self.assertAlmostEqual(topic["baseline_rate"], 0.0, places=4)
        self.assertGreater(topic["growth_rate"], 0.0)
        self.assertTrue(np.isfinite(topic["growth_score"]))
        self.assertGreaterEqual(topic["growth_score"], 0.0)
        self.assertLessEqual(topic["growth_score"], 1.0)
        self.assertEqual(topic["trend"], "up")

    def test_growth_uses_per_day_rates(self):
        # 4 papers in the 30-day window vs 10 in the 150-day baseline: the raw
        # counts fall (4 < 10) but the per-day rate doubles, so growth ~ +100%.
        anchor = date.today()
        candidates = []
        for _ in range(4):
            candidates.append({"id": len(candidates) + 1, "journal": "J",
                               "published_date": (anchor - timedelta(days=10)).isoformat()})
        for _ in range(10):
            candidates.append({"id": len(candidates) + 1, "journal": "J",
                               "published_date": (anchor - timedelta(days=100)).isoformat()})
        topics = [{
            "cluster_id": 0,
            "paper_indices": list(range(14)),
            "size": 14,
            "cluster_kind": "formal",
        }]
        scored = _compute_heat_scores(
            topics, candidates, recent_days=30, baseline_days=150,
            anchor_date=anchor, min_recent_for_hot=3,
        )
        topic = scored[0]
        self.assertEqual(topic["recent_count"], 4)
        self.assertEqual(topic["baseline_count"], 10)
        self.assertAlmostEqual(topic["growth_rate"], 1.0, places=2)

    def test_inactive_topics_excluded_from_graph(self):
        # An active topic (3 recent papers) renders as an anchor; an inactive
        # topic (0 recent papers) is absent from graph points / trends.json but
        # stays in topics_meta with status == "inactive" for lineage.
        anchor = date.today()
        candidates = [
            {"id": 1, "journal": "J", "published_date": (anchor - timedelta(days=5)).isoformat()},
            {"id": 2, "journal": "J", "published_date": (anchor - timedelta(days=6)).isoformat()},
            {"id": 3, "journal": "J", "published_date": (anchor - timedelta(days=7)).isoformat()},
            {"id": 4, "journal": "J", "published_date": (anchor - timedelta(days=120)).isoformat()},
            {"id": 5, "journal": "J", "published_date": (anchor - timedelta(days=121)).isoformat()},
        ]
        topics = [
            {"cluster_id": 0, "topic_id": "t_active", "paper_indices": [0, 1, 2], "size": 3,
             "cluster_kind": "formal", "centroid": np.zeros(8)},
            {"cluster_id": 1, "topic_id": "t_inactive", "paper_indices": [3, 4], "size": 2,
             "cluster_kind": "emerging", "centroid": np.zeros(8)},
        ]
        scored = _compute_heat_scores(
            topics, candidates, recent_days=30, baseline_days=150,
            anchor_date=anchor, min_recent_for_hot=3,
        )
        by_id = {t["topic_id"]: t for t in scored}
        self.assertEqual(by_id["t_active"]["status"], "hot")
        self.assertEqual(by_id["t_inactive"]["status"], "inactive")

        with tempfile.TemporaryDirectory() as td:
            temp_dir, _final_dir = _ensure_output_dirs(Path(td))
            umap_coords = np.array(
                [[0, 0], [0.1, 0.1], [0.2, 0.2], [1, 1], [1.1, 1.1]], dtype=np.float32)
            paper_heat = [100.0, 90.0, 80.0, 30.0, 20.0]
            anchors = _compute_anchor_positions(scored, umap_coords)
            _build_output(
                scored, [], anchors, umap_coords, paper_heat, candidates,
                {}, anchor, "test-model", 8, {}, temp_dir,
            )

            graph = json.loads((temp_dir / "graph.json").read_text(encoding="utf-8"))
            anchor_ids = {p["id"] for p in graph["points"] if p["type"] == "topic"}
            self.assertIn("t_active", anchor_ids)
            self.assertNotIn("t_inactive", anchor_ids)
            meta_by_id = {t["topic_id"]: t for t in graph["topics_meta"]}
            self.assertEqual(meta_by_id["t_inactive"]["status"], "inactive")
            self.assertIn("t_active", meta_by_id)

            trends = json.loads((temp_dir / "trends.json").read_text(encoding="utf-8"))
            self.assertEqual({t["topic_id"] for t in trends}, {"t_active"})


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
            self.assertEqual(graph["schema_version"], 3)
            # 16 paper points + 4 topic anchors
            self.assertGreaterEqual(len(graph["points"]), 3)
            point_ids = {p["id"] for p in graph["points"]}
            topic_points = [p for p in graph["points"] if p["type"] == "topic"]
            self.assertGreaterEqual(len(topic_points), 3)
            for link in graph["links"]:
                self.assertIn(link["source"], point_ids)
                self.assertIn(link["target"], point_ids)

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
        # point type/label and fixed UMAP coordinates.
        def structural(graph):
            return sorted(
                (p["type"], p["label"], round(p["x"], 2), round(p["y"], 2))
                for p in graph["points"]
            )

        self.assertEqual(structural(first), structural(second))
        self.assertEqual(
            {l["weight"] for l in first["links"]},
            {l["weight"] for l in second["links"]},
        )


class TopicLabelerResponseTests(unittest.TestCase):
    def test_failed_refresh_preserves_inherited_label_and_retries_later(self) -> None:
        labeler = TopicLabeler.__new__(TopicLabeler)
        labeler.client = SimpleNamespace(messages=SimpleNamespace(
            create=lambda **_kwargs: SimpleNamespace(
                content=[SimpleNamespace(type="text", text="not json")]
            )
        ))
        labeler.model = "test-model"
        labeler.system_prompt = "test"
        labeler.config = SimpleNamespace(topic_overrides={})
        topics = [{
            "topic_id": "topic_stable",
            "paper_indices": [0],
            "label_zh": "已有中文主题名",
            "description": "已有描述",
            "why_hot": "已有说明",
            "keywords": ["已有关键词"],
            "_label_fingerprint": "old-fingerprint",
        }]
        candidates = [{"id": 1, "title": "Changed paper", "abstract": "Changed"}]

        with patch("journal_tracker.hotspot_labels.time.sleep"):
            result = labeler.label_topics(topics, candidates)

        self.assertEqual(result[0]["label_zh"], "已有中文主题名")
        self.assertEqual(result[0]["description"], "已有描述")
        self.assertEqual(result[0]["_label_fingerprint"], "old-fingerprint")

    def test_parse_label_response_handles_markdown_fence(self) -> None:
        text = "```json\n[{\"topic_index\": 0, \"label_zh\": \"算法中介\"}]\n```"
        result = TopicLabeler._parse_label_response(text, 1)
        self.assertEqual(result[0]["label_zh"], "算法中介")

    def test_parse_label_response_handles_single_object(self) -> None:
        result = TopicLabeler._parse_label_response(
            '{"topic_index": 2, "label_zh": "平台治理"}', 1
        )
        self.assertEqual(result[0]["label_zh"], "平台治理")

    def test_parse_label_response_extracts_array_from_prose(self) -> None:
        text = "以下是结果：\n[{\"topic_index\": 0, \"label_zh\": \"NLP\"}]\n（完毕）"
        result = TopicLabeler._parse_label_response(text, 1)
        self.assertEqual(result[0]["label_zh"], "NLP")

    def test_normalize_keywords_accepts_llm_string_output(self) -> None:
        self.assertEqual(normalize_keywords("性别政治, 社会；数字动员"), ["性别政治", "社会", "数字动员"])


if __name__ == "__main__":
    unittest.main()
