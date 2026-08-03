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
        "schema_version": 3,
        "points": [
            # topic anchors (only these carry a label + detail file)
            {"id": "a", "type": "topic", "topic": 0, "label": "甲", "heat": 80, "x": 0.1, "y": -0.2, "detailFile": "topics/a.json", "size": 11.4, "trend": "up"},
            {"id": "b", "type": "topic", "topic": 1, "label": "乙", "heat": 60, "x": 0.5, "y": 0.3, "detailFile": "topics/b.json", "size": 9.6, "trend": "flat"},
            {"id": "c", "type": "topic", "topic": 2, "label": "丙", "heat": 40, "x": -0.4, "y": 0.7, "detailFile": "topics/c.json", "size": 8.0, "trend": "down"},
            # paper points in each group
            {"id": "p1", "type": "paper", "topic": 0, "label": "", "heat": 50, "x": 0.12, "y": -0.2, "size": 2.5, "trend": ""},
            {"id": "p2", "type": "paper", "topic": 1, "label": "", "heat": 40, "x": 0.51, "y": 0.31, "size": 2.5, "trend": ""},
            {"id": "p3", "type": "paper", "topic": 2, "label": "", "heat": 30, "x": -0.41, "y": 0.71, "size": 2.5, "trend": ""},
        ],
        "links": [
            {"id": "a__b", "source": "a", "target": "b", "weight": 0.5},
            {"id": "b__c", "source": "b", "target": "c", "weight": 0.3},
        ],
    }


def _build_valid_output(tmp: Path) -> Path:
    data_dir = tmp / "hotspots"
    _write_json(data_dir / "manifest.json", {
        "schema_version": 3,
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
    for point in _valid_graph()["points"]:
        if point["type"] != "topic":
            continue
        _write_json(data_dir / point["detailFile"], {
            "topic_id": point["id"],
            "label": point["label"],
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
            graph["points"][0]["x"] = float("nan")
            _write_json(graph_path, graph)
            with self.assertRaises(HotspotValidationError) as ctx:
                validate_hotspot_data(data_dir)
            self.assertIn("x coordinate", str(ctx.exception))

    def test_heat_out_of_range_fails(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = _build_valid_output(Path(td))
            graph = json.loads((data_dir / "graph.json").read_text(encoding="utf-8"))
            graph["points"][0]["heat"] = 120
            _write_json(data_dir / "graph.json", graph)
            with self.assertRaises(HotspotValidationError) as ctx:
                validate_hotspot_data(data_dir)
            self.assertIn("heat", str(ctx.exception))

    def test_duplicate_point_id_fails(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = _build_valid_output(Path(td))
            graph = json.loads((data_dir / "graph.json").read_text(encoding="utf-8"))
            graph["points"][1]["id"] = graph["points"][0]["id"]
            _write_json(data_dir / "graph.json", graph)
            with self.assertRaises(HotspotValidationError) as ctx:
                validate_hotspot_data(data_dir)
            self.assertIn("Duplicate point id", str(ctx.exception))

    def test_link_source_missing_fails(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = _build_valid_output(Path(td))
            graph = json.loads((data_dir / "graph.json").read_text(encoding="utf-8"))
            graph["links"][0]["source"] = "nonexistent"
            _write_json(data_dir / "graph.json", graph)
            with self.assertRaises(HotspotValidationError) as ctx:
                validate_hotspot_data(data_dir)
            self.assertIn("not in points", str(ctx.exception))

    def test_self_loop_fails(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = _build_valid_output(Path(td))
            graph = json.loads((data_dir / "graph.json").read_text(encoding="utf-8"))
            graph["links"][0]["source"] = "a"
            graph["links"][0]["target"] = "a"
            _write_json(data_dir / "graph.json", graph)
            with self.assertRaises(HotspotValidationError) as ctx:
                validate_hotspot_data(data_dir)
            self.assertIn("self-loop", str(ctx.exception))

    def test_wrong_schema_version_fails(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = _build_valid_output(Path(td))
            manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
            manifest["schema_version"] = 1
            _write_json(data_dir / "manifest.json", manifest)
            with self.assertRaises(HotspotValidationError):
                validate_hotspot_data(data_dir)

    def test_fewer_than_3_points_fails(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = _build_valid_output(Path(td))
            graph = json.loads((data_dir / "graph.json").read_text(encoding="utf-8"))
            graph["points"] = graph["points"][:2]
            graph["links"] = []
            _write_json(data_dir / "graph.json", graph)
            with self.assertRaises(HotspotValidationError):
                validate_hotspot_data(data_dir)

    def test_missing_size_or_trend_fails(self):
        # Sparse size/trend columns crash Cosmograph's DuckDB SUMMARIZE, so the
        # validator must hard-fail if any point omits either field.
        with tempfile.TemporaryDirectory() as td:
            data_dir = _build_valid_output(Path(td))
            graph = json.loads((data_dir / "graph.json").read_text(encoding="utf-8"))
            del graph["points"][0]["size"]
            _write_json(data_dir / "graph.json", graph)
            with self.assertRaises(HotspotValidationError) as ctx:
                validate_hotspot_data(data_dir)
            self.assertIn("size", str(ctx.exception))

        with tempfile.TemporaryDirectory() as td:
            data_dir = _build_valid_output(Path(td))
            graph = json.loads((data_dir / "graph.json").read_text(encoding="utf-8"))
            del graph["points"][1]["trend"]
            _write_json(data_dir / "graph.json", graph)
            with self.assertRaises(HotspotValidationError) as ctx:
                validate_hotspot_data(data_dir)
            self.assertIn("trend", str(ctx.exception))

    def test_validate_and_report_returns_false_on_failure(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = Path(td) / "hotspots"
            data_dir.mkdir()
            self.assertFalse(validate_and_report(data_dir))


if __name__ == "__main__":
    unittest.main()
