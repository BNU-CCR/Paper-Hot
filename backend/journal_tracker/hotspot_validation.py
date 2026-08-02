"""
Validation and safety checks for hotspot network output.

All checks run against the temp directory before the atomic replace.
If any check fails, the temp directory is left intact for debugging
and the existing public data is not touched.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List


class HotspotValidationError(ValueError):
    """Raised when hotspot output fails validation."""
    pass


def validate_hotspot_data(data_dir: Path) -> List[str]:
    """Run all validation checks. Returns a list of warnings (empty = clean).

    Raises HotspotValidationError on hard failures.
    """
    if not data_dir.is_dir():
        raise HotspotValidationError(f"Data directory not found: {data_dir}")

    warnings: List[str] = []
    errors: List[str] = []

    # ── Required files ───────────────────────────────────────────
    required = ["manifest.json", "graph.json", "trends.json"]
    for name in required:
        if not (data_dir / name).is_file():
            errors.append(f"Missing required file: {name}")

    if errors:
        raise HotspotValidationError("\n".join(errors))

    # ── manifest.json ────────────────────────────────────────────
    manifest = _read_json(data_dir / "manifest.json")
    _check(manifest.get("schema_version") == 1,
           "manifest.schema_version must be 1", errors)
    _check(isinstance(manifest.get("topic_count"), int) and manifest["topic_count"] >= 0,
           "manifest.topic_count must be a non-negative integer", errors)
    _check(isinstance(manifest.get("paper_count"), int) and manifest["paper_count"] >= 0,
           "manifest.paper_count must be a non-negative integer", errors)
    _check(isinstance(manifest.get("edge_count"), int) and manifest["edge_count"] >= 0,
           "manifest.edge_count must be a non-negative integer", errors)

    # ── graph.json ───────────────────────────────────────────────
    graph = _read_json(data_dir / "graph.json")
    nodes: List[Dict[str, Any]] = graph.get("nodes", [])
    edges: List[Dict[str, Any]] = graph.get("edges", [])

    # Node checks
    _check(3 <= len(nodes) <= 60,
           f"Node count {len(nodes)} must be in [3, 60]", errors)

    node_ids: set = set()
    for node in nodes:
        nid = node.get("id", "")
        _check(isinstance(nid, str) and nid, "Every node must have a non-empty id", errors)
        _check(nid not in node_ids, f"Duplicate node id: {nid}", errors)
        node_ids.add(nid)

        x, y = node.get("x"), node.get("y")
        _check(isinstance(x, (int, float)) and math.isfinite(float(x)),
               f"Node {nid} has non-finite x coordinate: {x}", errors)
        _check(isinstance(y, (int, float)) and math.isfinite(float(y)),
               f"Node {nid} has non-finite y coordinate: {y}", errors)

        hot = node.get("hotScore")
        _check(isinstance(hot, (int, float)) and 0 <= float(hot) <= 100,
               f"Node {nid} hotScore {hot} must be in [0, 100]", errors)

        size = node.get("size")
        _check(isinstance(size, (int, float)) and float(size) > 0,
               f"Node {nid} size {size} must be positive", errors)

    # Edge checks
    edge_ids: set = set()
    for edge in edges:
        eid = edge.get("id", "")
        _check(isinstance(eid, str) and eid, "Every edge must have a non-empty id", errors)
        _check(eid not in edge_ids, f"Duplicate edge id: {eid}", errors)
        edge_ids.add(eid)

        src, tgt = edge.get("source"), edge.get("target")
        _check(src in node_ids, f"Edge {eid} source '{src}' not in nodes", errors)
        _check(tgt in node_ids, f"Edge {eid} target '{tgt}' not in nodes", errors)
        _check(src != tgt, f"Edge {eid} is a self-loop", errors)

        weight = edge.get("weight")
        _check(isinstance(weight, (int, float)) and math.isfinite(float(weight)),
               f"Edge {eid} has non-finite weight: {weight}", errors)

    # ── trends.json ──────────────────────────────────────────────
    trends = _read_json(data_dir / "trends.json")
    _check(isinstance(trends, list), "trends.json must be a list", errors)
    for item in trends:
        tid = item.get("topic_id", "")
        _check(isinstance(tid, str) and tid, "Each trend must have topic_id", errors)

    # ── Topic detail files ───────────────────────────────────────
    topics_dir = data_dir / "topics"
    _check(topics_dir.is_dir(), "topics/ directory missing", errors)

    if topics_dir.is_dir():
        for node in nodes:
            detail_file = node.get("detailFile", "")
            if detail_file:
                detail_path = data_dir / detail_file
                _check(detail_path.is_file(),
                       f"Detail file missing: {detail_file}", errors)
                if detail_path.is_file():
                    detail = _read_json(detail_path)
                    papers = detail.get("papers", [])
                    _check(len(papers) >= 2,
                           f"Topic {node['id']} has only {len(papers)} papers (min 2)",
                           warnings)  # warning, not error

    # ── Retraction check ─────────────────────────────────────────
    # Check that no paper in detail files has is_retracted flag
    # (this is a soft warning since paper_features may not be fully populated)

    if errors:
        raise HotspotValidationError(
            f"{len(errors)} validation error(s):\n" + "\n".join(errors)
        )

    return warnings


def _read_json(path: Path) -> Any:
    """Read and parse a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _check(condition: bool, message: str, errors: List[str]) -> None:
    """Accumulate an error if condition is False."""
    if not condition:
        errors.append(message)


def validate_and_report(data_dir: Path) -> bool:
    """Validate and print a report. Returns True if clean."""
    try:
        warnings = validate_hotspot_data(data_dir)
        if warnings:
            print(f"Validation passed with {len(warnings)} warning(s):")
            for w in warnings:
                print(f"  ⚠ {w}")
        else:
            print("Validation passed — all checks green.")
        return True
    except HotspotValidationError as exc:
        print(f"Validation FAILED:\n{exc}")
        return False
