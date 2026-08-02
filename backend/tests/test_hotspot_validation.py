"""Tests for hotspot output validation. Pure — no heavy analysis deps."""

import json
import tempfile
import unittest
from pathlib import Path

from journal_tracker.hotspot_validation import (
    HotspotValidationError,
    validate_hotspot_data,
    validate_and_report,
)


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _valid_graph():
    return {
        "schema_version": 1,
        "nodes": [
            {"id": "a", "x": 0.1, "y": -0.2, "size": 20.0, "hotScore": 80, "detailFile": "topics/a.json"},
            {"id": "b", "x": 0.5, "y": 0.3, "size": 15.0, "hotScore": 60, "detailFile": "topics/b.json"},
            {"id": "c", "x": -0.4, "y": 0.7, "size": 12.0, "hotScore": 40, "detailFile": "topics/c.json"},
        ],
        "edges": [
            {"id": "a__b", "source": "a", "target": "b", "weight": 0.5},
            {"id": "b__c", "source": "b", "target": "c", "weight": 0.3},
        ],
    }


def _build_valid_output(tmp: Path) -> Path:
    data_dir = tmp / "hotspots"
    _write_json(data_dir / "manifest.json", {
        "schema_version": 1,
        "topic_count": 3,
        "paper_count": 12,
        "edge_count": 2,
    })
    _write_json(data_dir / "graph.json", _valid_graph())
    _write_json(data_dir / "trends.json", [
        {"topic_id": "a", "label": "甲"},
        {"topic_id": "b", "label": "乙"},
        {"topic_id": "c", "label": "丙"},
    ])
    for node in _valid_graph()["nodes"]:
        _write_json(data_dir / node["detailFile"], {
            "topic_id": node["id"],
            "label": node["label"] if "label" in node else node["id"],
            "papers": [
                {"id": 1, "title": "Paper one"},
                {"id": 2, "title": "Paper two"},
            ],
        })
    return data_dir


class HotspotValidationTests(unittest.TestCase):
    def test_valid_output_passes(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = _build_valid_output(Path(td))
            warnings = validate_hotspot_data(data_dir)
            self.assertEqual(warnings, [])

    def test_missing_required_file_raises(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = Path(td) / "hotspots"
            data_dir.mkdir()
            _write_json(data_dir / "graph.json", _valid_graph())
            with self.assertRaises(HotspotValidationError):
                validate_hotspot_data(data_dir)

    def test_non_finite_coordinate_fails(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = _build_valid_output(Path(td))
            graph_path = data_dir / "graph.json"
            graph = json.loads(graph_path.read_text(encoding="utf-8"))
            graph["nodes"][0]["x"] = float("nan")
            _write_json(graph_path, graph)
            with self.assertRaises(HotspotValidationError) as ctx:
                validate_hotspot_data(data_dir)
            self.assertIn("x coordinate", str(ctx.exception))

    def test_hotscore_out_of_range_fails(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = _build_valid_output(Path(td))
            graph = json.loads((data_dir / "graph.json").read_text(encoding="utf-8"))
            graph["nodes"][0]["hotScore"] = 120
            _write_json(data_dir / "graph.json", graph)
            with self.assertRaises(HotspotValidationError) as ctx:
                validate_hotspot_data(data_dir)
            self.assertIn("hotScore", str(ctx.exception))

    def test_duplicate_node_id_fails(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = _build_valid_output(Path(td))
            graph = json.loads((data_dir / "graph.json").read_text(encoding="utf-8"))
            graph["nodes"][1]["id"] = graph["nodes"][0]["id"]
            _write_json(data_dir / "graph.json", graph)
            with self.assertRaises(HotspotValidationError) as ctx:
                validate_hotspot_data(data_dir)
            self.assertIn("Duplicate node id", str(ctx.exception))

    def test_edge_source_missing_fails(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = _build_valid_output(Path(td))
            graph = json.loads((data_dir / "graph.json").read_text(encoding="utf-8"))
            graph["edges"][0]["source"] = "nonexistent"
            _write_json(data_dir / "graph.json", graph)
            with self.assertRaises(HotspotValidationError) as ctx:
                validate_hotspot_data(data_dir)
            self.assertIn("not in nodes", str(ctx.exception))

    def test_self_loop_fails(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = _build_valid_output(Path(td))
            graph = json.loads((data_dir / "graph.json").read_text(encoding="utf-8"))
            graph["edges"][0]["source"] = "a"
            graph["edges"][0]["target"] = "a"
            _write_json(data_dir / "graph.json", graph)
            with self.assertRaises(HotspotValidationError) as ctx:
                validate_hotspot_data(data_dir)
            self.assertIn("self-loop", str(ctx.exception))

    def test_wrong_schema_version_fails(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = _build_valid_output(Path(td))
            manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
            manifest["schema_version"] = 2
            _write_json(data_dir / "manifest.json", manifest)
            with self.assertRaises(HotspotValidationError):
                validate_hotspot_data(data_dir)

    def test_fewer_than_3_topics_fails(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = _build_valid_output(Path(td))
            graph = json.loads((data_dir / "graph.json").read_text(encoding="utf-8"))
            graph["nodes"] = graph["nodes"][:2]
            graph["edges"] = []
            _write_json(data_dir / "graph.json", graph)
            with self.assertRaises(HotspotValidationError):
                validate_hotspot_data(data_dir)

    def test_validate_and_report_returns_false_on_failure(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = Path(td) / "hotspots"
            data_dir.mkdir()
            self.assertFalse(validate_and_report(data_dir))


if __name__ == "__main__":
    unittest.main()
