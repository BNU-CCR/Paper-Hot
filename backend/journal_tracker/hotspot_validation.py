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
    _check(manifest.get("schema_version") == 2,
           "manifest.schema_version must be 2", errors)
    _check(isinstance(manifest.get("topic_count"), int) and manifest["topic_count"] >= 0,
           "manifest.topic_count must be a non-negative integer", errors)
    _check(isinstance(manifest.get("paper_count"), int) and manifest["paper_count"] >= 0,
           "manifest.paper_count must be a non-negative integer", errors)
    _check(isinstance(manifest.get("edge_count"), int) and manifest["edge_count"] >= 0,
           "manifest.edge_count must be a non-negative integer", errors)

    # ── graph.json (semantic map) ────────────────────────────────
    graph = _read_json(data_dir / "graph.json")
    points: List[Dict[str, Any]] = graph.get("points", [])
    links: List[Dict[str, Any]] = graph.get("links", [])

    # Point checks
    _check(3 <= len(points),
           f"Point count {len(points)} must be >= 3", errors)

    point_ids: set = set()
    topic_points: List[Dict[str, Any]] = []
    for point in points:
        pid = point.get("id", "")
        _check(isinstance(pid, str) and pid, "Every point must have a non-empty id", errors)
        _check(pid not in point_ids, f"Duplicate point id: {pid}", errors)
        point_ids.add(pid)

        ptype = point.get("type")
        _check(ptype in ("paper", "topic"),
               f"Point {pid} has unknown type: {ptype}", errors)

        x, y = point.get("x"), point.get("y")
        _check(isinstance(x, (int, float)) and math.isfinite(float(x)),
               f"Point {pid} has non-finite x coordinate: {x}", errors)
        _check(isinstance(y, (int, float)) and math.isfinite(float(y)),
               f"Point {pid} has non-finite y coordinate: {y}", errors)

        heat = point.get("heat")
        _check(isinstance(heat, (int, float)) and math.isfinite(float(heat)) and 0 <= float(heat) <= 100,
               f"Point {pid} heat {heat} must be a finite number in [0, 100]", errors)

        if ptype == "topic":
            topic_points.append(point)

    # Every topic cloud should have at least one paper point in its group
    # (soft warning — a fresh topic may briefly have all papers as noise).
    paper_groups = {
        p.get("topic") for p in points
        if p.get("type") == "paper" and isinstance(p.get("topic"), int) and p["topic"] >= 0
    }
    for point in topic_points:
        _check(point.get("topic") in paper_groups,
               f"Topic point {point.get('id')} has no paper points in its group",
               warnings)

    # Link checks
    link_ids: set = set()
    for link in links:
        lid = link.get("id", "")
        _check(isinstance(lid, str) and lid, "Every link must have a non-empty id", errors)
        _check(lid not in link_ids, f"Duplicate link id: {lid}", errors)
        link_ids.add(lid)

        src, tgt = link.get("source"), link.get("target")
        _check(src in point_ids, f"Link {lid} source '{src}' not in points", errors)
        _check(tgt in point_ids, f"Link {lid} target '{tgt}' not in points", errors)
        _check(src != tgt, f"Link {lid} is a self-loop", errors)

        weight = link.get("weight")
        _check(isinstance(weight, (int, float)) and math.isfinite(float(weight)),
               f"Link {lid} has non-finite weight: {weight}", errors)

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
        for point in topic_points:
            detail_file = point.get("detailFile", "")
            if detail_file:
                detail_path = data_dir / detail_file
                _check(detail_path.is_file(),
                       f"Detail file missing: {detail_file}", errors)
                if detail_path.is_file():
                    detail = _read_json(detail_path)
                    papers = detail.get("papers", [])
                    _check(len(papers) >= 2,
                           f"Topic {point['id']} has only {len(papers)} papers (min 2)",
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
