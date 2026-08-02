"""Generate the auto-updated README preview and workflow statistics."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional
from zoneinfo import ZoneInfo


PREVIEW_START = "<!-- paper-hot:auto-preview:start -->"
PREVIEW_END = "<!-- paper-hot:auto-preview:end -->"
STATS_START = "<!-- paper-hot:auto-stats:start -->"
STATS_END = "<!-- paper-hot:auto-stats:end -->"
SHANGHAI = ZoneInfo("Asia/Shanghai")


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _escape_markdown(value: Any) -> str:
    return str(value or "").replace("\n", " ").replace("|", "\\|").strip()


def _paper_sort_key(paper: dict[str, Any]) -> tuple[str, int]:
    raw_id = paper.get("id")
    try:
        paper_id = int(raw_id)
    except (TypeError, ValueError):
        paper_id = 0
    return str(paper.get("published_date") or ""), paper_id


def _paper_link(paper: dict[str, Any]) -> str:
    title = _escape_markdown(paper.get("title") or "Untitled paper").replace("]", "\\]")
    url = str(paper.get("source_url") or "").strip()
    return f"[{title}](<{url}>)" if url else title


def render_preview(featured: Iterable[dict[str, Any]], updated_at: datetime, limit: int = 5) -> str:
    papers = sorted(featured, key=_paper_sort_key, reverse=True)[:limit]
    lines = [
        PREVIEW_START,
        "## 本期精选（自动更新）",
        "",
        f"> 更新于 {updated_at.astimezone(SHANGHAI):%Y-%m-%d %H:%M} GMT+8，展示最新 {len(papers)} 篇精选论文。",
        "",
        "| 日期 | 论文 | 期刊 | 推荐摘要 |",
        "| --- | --- | --- | --- |",
    ]
    if papers:
        for paper in papers:
            lines.append(
                "| {date} | {title} | {journal} | {summary} |".format(
                    date=_escape_markdown(paper.get("published_date") or "待补充"),
                    title=_paper_link(paper),
                    journal=_escape_markdown(paper.get("journal") or "待补充"),
                    summary=_escape_markdown(paper.get("summary") or paper.get("reason") or "待补充"),
                )
            )
    else:
        lines.append("| — | 暂无精选论文 | — | 等待下一次自动更新 |")
    lines.extend(["", PREVIEW_END])
    return "\n".join(lines)


def _fallback_stats(all_papers: Iterable[dict[str, Any]]) -> dict[str, Any]:
    papers = list(all_papers)
    relevance = Counter(str(paper.get("relevance") or "") for paper in papers)
    screening = Counter(str(paper.get("screening_status") or "unknown") for paper in papers)
    return {
        "total": len(papers),
        "relevance": dict(relevance),
        "screening_status": dict(screening),
        "this_week": 0,
    }


def render_stats(
    featured: list[dict[str, Any]],
    all_papers: list[dict[str, Any]],
    report: Optional[dict[str, Any]],
    updated_at: datetime,
) -> str:
    stats = (report or {}).get("after") or _fallback_stats(all_papers)
    relevance = stats.get("relevance", {})
    screening = stats.get("screening_status", {})
    lines = [
        STATS_START,
        "### 自动更新状态",
        "",
        f"> 最近更新：{updated_at.astimezone(SHANGHAI):%Y-%m-%d %H:%M} GMT+8",
        "",
        "| 指标 | 数量 |",
        "| --- | ---: |",
        f"| 数据库论文 | {stats.get('total', len(all_papers))} |",
        f"| 当期新增 | {stats.get('this_week', 0)} |",
        f"| High / Medium / Low | {relevance.get('High', 0)} / {relevance.get('Medium', 0)} / {relevance.get('Low', 0)} |",
        f"| Pending / Screened / Quarantined / Error | {screening.get('pending', 0)} / {screening.get('screened', 0)} / {screening.get('quarantined', 0)} / {screening.get('error', 0)} |",
        f"| 已发布精选 | {len(featured)} |",
        f"| 期刊全量导出 | {len(all_papers)} |",
    ]

    coverage = (report or {}).get("steps", {}).get("verify_coverage", {})
    if coverage and not coverage.get("skipped"):
        lines.extend(
            [
                "",
                "覆盖验证：OpenAlex DOI {openalex}，Crossref DOI {crossref}，匹配 {matched}，"
                "Crossref 中尚缺 {missing}。".format(
                    openalex=coverage.get("total_openalex_dois", 0),
                    crossref=coverage.get("total_crossref_dois", 0),
                    matched=coverage.get("total_matched", 0),
                    missing=coverage.get("total_missing_in_openalex", 0),
                ),
            ]
        )
    lines.extend(["", STATS_END])
    return "\n".join(lines)


def replace_section(text: str, start: str, end: str, replacement: str) -> str:
    start_index = text.find(start)
    end_index = text.find(end)
    if start_index < 0 or end_index < 0 or end_index < start_index:
        raise ValueError(f"README markers are missing or invalid: {start} ... {end}")
    end_index += len(end)
    return text[:start_index] + replacement + text[end_index:]


def update_readme(
    readme_path: Path,
    featured_path: Path,
    all_papers_path: Path,
    report_path: Optional[Path] = None,
    updated_at: Optional[datetime] = None,
) -> None:
    featured = _load_json(featured_path, [])
    all_papers = _load_json(all_papers_path, [])
    report = _load_json(report_path, None) if report_path else None
    if not isinstance(featured, list) or not isinstance(all_papers, list):
        raise ValueError("Public paper JSON files must contain arrays")
    if report is not None and not isinstance(report, dict):
        raise ValueError("Weekly report must contain an object")

    now = updated_at or datetime.now(SHANGHAI)
    text = readme_path.read_text(encoding="utf-8-sig")
    text = replace_section(text, PREVIEW_START, PREVIEW_END, render_preview(featured, now))
    text = replace_section(text, STATS_START, STATS_END, render_stats(featured, all_papers, report, now))
    readme_path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Update README statistics and featured preview")
    project_root = Path(__file__).resolve().parents[2]
    parser.add_argument("--readme", type=Path, default=project_root / "README.md")
    parser.add_argument(
        "--featured",
        type=Path,
        default=project_root / "frontend" / "public" / "data" / "papers.json",
    )
    parser.add_argument(
        "--all-papers",
        type=Path,
        default=project_root / "frontend" / "public" / "data" / "all_papers.json",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=project_root / "backend" / "data" / "reports" / "weekly_run_latest.json",
    )
    args = parser.parse_args()
    update_readme(args.readme, args.featured, args.all_papers, args.report)
    print(f"Updated README: {args.readme}")


if __name__ == "__main__":
    main()
