"""
计算传播论文追踪系统 - 主入口

用法:
    py -m journal_tracker.main                       # 运行完整流程
    py -m journal_tracker.main search                # 仅搜索论文
    py -m journal_tracker.main screen-pending        # 筛选待处理论文
    py -m journal_tracker.main workflow-status       # 查看状态
    py -m journal_tracker.main export-public         # 导出公开 JSON
"""

import argparse
import json
import time
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .config import Config, get_config
from .storage import PaperStorage, Paper, PaperFeatures
from .discovery import OpenAlexDiscovery, PaperDiscovery, DiscoveredPaper
from .filter import PaperFilter
from .notification import NotificationSender
from .publication import PublicPaperExporter
from .coverage import CoverageVerifier
from .hotspots import generate_monthly_hotspots
from .translation import SiliconFlowTranslator, translate_pending_papers


def safe_print(message: str = "") -> None:
    """在 Windows 非 UTF-8 控制台中安全打印包含特殊字符的论文标题。"""
    encoding = sys.stdout.encoding or "utf-8"
    print(str(message).encode(encoding, errors="replace").decode(encoding))


def run_full_pipeline(
    config: Optional[Config] = None,
    max_papers: int = 20
) -> int:
    """
    运行完整流程: 搜索 -> 筛选 -> 存储 -> 通知

    Returns:
        int: 处理的新论文数量
    """
    if config is None:
        config = get_config()

    config.database_path.parent.mkdir(parents=True, exist_ok=True)
    storage = PaperStorage(config.database_path)
    discovery = PaperDiscovery(config.semantic_scholar_api_key)
    paper_filter = PaperFilter()
    notifier = NotificationSender()

    print("=" * 50)
    print("开始论文追踪流程")
    print("=" * 50)

    # 1. 搜索论文
    print("\n[1/4] 搜索论文...")
    papers = discovery.search_recent_papers(limit=max_papers)
    print(f"   发现 {len(papers)} 篇论文")
    _print_discovery_report(getattr(discovery, "last_run_report", {}))

    if not papers:
        print("   没有发现新论文")
        return 0

    # 2. 去重检查
    print("\n[2/4] 检查重复...")
    new_papers = []
    for p in papers:
        if not storage.paper_exists(link=p.link, doi=p.doi):
            new_papers.append(p)
        else:
            print(f"   跳过已有: {p.title[:40]}...")

    print(f"   新论文: {len(new_papers)} 篇")

    if not new_papers:
        print("   没有新论文需要处理")
        return 0

    # 3. AI筛选
    print("\n[3/4] AI筛选...")
    papers_data = [p.to_dict() for p in new_papers]
    filtered = paper_filter.filter_papers(papers_data)

    high_count = sum(1 for p in filtered if p.get("relevance") == "High")
    medium_count = sum(1 for p in filtered if p.get("relevance") == "Medium")
    print(f"   High: {high_count}, Medium: {medium_count}, Low: {len(filtered) - high_count - medium_count}")

    # 4. 存储
    print("\n[4/4] 存储论文...")
    saved_count = 0
    for p in filtered:
        paper = Paper(
            title=p.get("title", ""),
            authors=p.get("authors", ""),
            abstract=p.get("abstract", ""),
            journal=p.get("journal", ""),
            published_date=p.get("published_date", ""),
            link=p.get("link", ""),
            doi=p.get("doi", ""),
            relevance=p.get("relevance", "Low"),
            reason=p.get("reason", ""),
            tags=",".join(p.get("tags", [])) if isinstance(p.get("tags"), list) else str(p.get("tags", "")),
            summary=p.get("summary", ""),
            method=p.get("method", ""),
        )
        paper_id = storage.add_paper(paper)
        if paper_id:
            saved_count += 1
            # 发送通知
            notifier.send_paper_notification(p)

    print(f"   已存储 {saved_count} 篇")

    # 5. 批量通知
    if high_count > 0 or medium_count > 0:
        print("\n[通知] 发送汇总通知...")
        notifier.send_batch_notification(filtered)

    print("\n[公开站] 刷新公开数据...")
    publish_high_papers(config)

    print("\n" + "=" * 50)
    print(f"完成! 处理了 {saved_count} 篇新论文")
    print("=" * 50)

    return saved_count


def _print_discovery_report(report: dict) -> None:
    """打印最近一次发现运行的轻量报告。"""
    if not report:
        return
    print(
        "   发现请求: "
        f"{report.get('requested_queries', 0)} | "
        f"成功: {report.get('successful_queries', 0)} | "
        f"空结果: {report.get('empty_queries', 0)} | "
        f"失败: {report.get('failed_queries', 0)}"
    )
    if report.get("duplicate_papers"):
        print(f"   去重论文: {report.get('duplicate_papers', 0)}")
    errors = report.get("errors") or []
    if errors:
        print("   发现错误:")
        for error in errors[:3]:
            safe_print(f"   - {error}")


def search_only(config: Optional[Config] = None):
    """仅搜索并显示论文"""
    if config is None:
        config = get_config()

    discovery = PaperDiscovery(config.semantic_scholar_api_key)
    print("搜索最近论文...")
    papers = discovery.search_recent_papers(limit=20)

    print(f"\n发现 {len(papers)} 篇论文:\n")
    for i, p in enumerate(papers, 1):
        safe_print(f"{i}. {p.title}")
        safe_print(f"   Authors: {p.authors}")
        safe_print(f"   Journal: {p.journal} ({p.published_date})")
        safe_print(f"   DOI: {p.doi}")
        print()


def ingest_journal_updates(
    config: Optional[Config] = None,
    limit_per_journal: int = 10,
) -> int:
    """Fetch red-list journal updates and save them before AI screening."""
    if config is None:
        config = get_config()

    config.database_path.parent.mkdir(parents=True, exist_ok=True)
    storage = PaperStorage(config.database_path)
    discovery = OpenAlexDiscovery()
    journals = config.get_tracked_journals()
    source_run_id = f"openalex-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    tracked_by_name = _tracked_by_name_map(journals)

    print("Red-list journal update fetch")
    print("=" * 40)
    print(f"Tracked journals: {len(journals)}")
    print(f"Limit per journal: {limit_per_journal}")

    papers = discovery.search_journal_updates(
        journals=journals,
        limit_per_journal=limit_per_journal,
    )
    print(f"Discovered papers: {len(papers)}")
    _print_discovery_report(getattr(discovery, "last_run_report", {}))

    saved_count = _save_discovered_papers(storage, papers, source_run_id, tracked_by_name)
    print(f"Saved new papers: {saved_count}")
    return saved_count


def ingest_journal_backfill(
    config: Optional[Config] = None,
    from_year: int = 2025,
    to_year: int = 2026,
    max_per_journal: int = 1000,
) -> int:
    """Fetch ALL works published within [from_year, to_year] for tracked journals.

    One-time catch-up: imports historical content the weekly update (which filters
    by each journal's ``track_from_year``) would otherwise never see, and stores it
    as pending for screening. Safe to re-run — existing DOIs/links are skipped.
    """
    if config is None:
        config = get_config()

    config.database_path.parent.mkdir(parents=True, exist_ok=True)
    storage = PaperStorage(config.database_path)
    discovery = OpenAlexDiscovery()
    journals = config.get_tracked_journals()
    source_run_id = (
        f"openalex-backfill-{from_year}-{to_year}-"
        f"{datetime.now().strftime('%Y%m%d%H%M%S')}"
    )
    tracked_by_name = _tracked_by_name_map(journals)

    print("Red-list journal backfill fetch")
    print("=" * 40)
    print(f"Tracked journals: {len(journals)}")
    print(f"Year range: {from_year}-01-01 ~ {to_year}-12-31")
    print(f"Limit per journal: {max_per_journal}")

    papers = discovery.backfill_journal_updates(
        journals=journals,
        from_year=from_year,
        to_year=to_year,
        max_per_journal=max_per_journal,
    )
    print(f"Discovered papers: {len(papers)}")
    _print_discovery_report(getattr(discovery, "last_run_report", {}))

    saved_count = _save_discovered_papers(storage, papers, source_run_id, tracked_by_name)
    print(f"Saved new papers: {saved_count}")
    return saved_count


def _tracked_by_name_map(journals: List[dict]) -> dict:
    """Map normalized journal names to their configs for tracked_journal attribution."""
    return {
        _normalize_journal_name(journal.get("name", "")): journal
        for journal in journals
    }


def _save_discovered_papers(
    storage: PaperStorage,
    papers: List[DiscoveredPaper],
    source_run_id: str,
    tracked_by_name: dict,
) -> int:
    """Persist discovered papers as pending, skipping existing rows by DOI/link."""
    saved_count = 0
    for discovered in papers:
        if storage.paper_exists(link=discovered.link, doi=discovered.doi):
            safe_print(f"Skip existing: {discovered.title[:60]}")
            continue
        paper = Paper(
            title=discovered.title,
            authors=discovered.authors,
            abstract=discovered.abstract,
            journal=discovered.journal,
            published_date=discovered.published_date,
            link=discovered.link,
            doi=discovered.doi,
            relevance="",
            reason="Pending AI screening",
            source_type="openalex",
            source_run_id=source_run_id,
            tracked_journal=_tracked_journal_name(discovered.journal, tracked_by_name),
            openalex_id=discovered.openalex_id,
            volume=discovered.volume,
            issue=discovered.issue,
            bibliography_checked_at=datetime.now().isoformat(),
            screening_status="pending",
        )
        paper_id = storage.add_paper(paper)
        if paper_id:
            saved_count += 1
            # Store OpenAlex enrichment data for hotspot analysis
            if discovered.openalex_topics or discovered.openalex_keywords:
                storage.upsert_paper_features(PaperFeatures(
                    paper_id=paper_id,
                    openalex_topics_json=discovered.openalex_topics,
                    openalex_keywords_json=discovered.openalex_keywords,
                    referenced_works_json=discovered.referenced_works,
                    cited_by_count=discovered.citation_count,
                    is_retracted=discovered.is_retracted,
                ))
    return saved_count


def repair_local_screening_queue(config: Optional[Config] = None) -> dict:
    """Classify historical unscreened rows into pending or quarantined."""
    if config is None:
        config = get_config()

    storage = PaperStorage(config.database_path)
    report = storage.repair_unscreened_queue(config.get_tracked_journals())
    print("Screening queue repair")
    print("=" * 40)
    print(f"Pending red-list papers: {report['pending']}")
    print(f"Quarantined non-red-list papers: {report['quarantined']}")
    return report


def backfill_openalex_bibliography(config: Optional[Config] = None, limit: int = 10000) -> dict:
    """Fill missing volume and issue fields from the OpenAlex work record."""
    if config is None:
        config = get_config()

    storage = PaperStorage(config.database_path)
    discovery = OpenAlexDiscovery()
    papers = storage.get_papers_missing_issue(limit=limit)
    report = {"requested": len(papers), "updated": 0, "without_issue": 0, "failed": 0}
    print(f"OpenAlex bibliography backfill: {len(papers)} papers")

    for index, paper in enumerate(papers):
        try:
            bibliography = discovery.get_bibliography(paper.openalex_id, paper.doi)
        except Exception as error:
            report["failed"] += 1
            safe_print(f"Backfill failed [{paper.id}]: {paper.title[:60]} | {error}")
            continue

        storage.update_paper_bibliography(
            paper.id,
            bibliography["volume"],
            bibliography["issue"],
            bibliography["openalex_id"],
        )
        if bibliography["issue"]:
            report["updated"] += 1
        else:
            report["without_issue"] += 1

        if index < len(papers) - 1:
            time.sleep(OpenAlexDiscovery.SEARCH_PAUSE_SECONDS)

    print(
        "Backfill complete: "
        f"{report['updated']} with issue, {report['without_issue']} still unassigned, "
        f"{report['failed']} failed"
    )
    return report


def backfill_openalex_features(config: Optional[Config] = None, limit: int = 10000) -> dict:
    """Fill missing paper_features (topics, keywords, references, citations) from OpenAlex."""
    if config is None:
        config = get_config()

    storage = PaperStorage(config.database_path)
    discovery = OpenAlexDiscovery()
    paper_ids = storage.get_papers_missing_features(limit=limit)
    report = {"requested": len(paper_ids), "enriched": 0, "empty": 0, "failed": 0}
    print(f"OpenAlex features backfill: {len(paper_ids)} papers missing features")

    for index, paper_id in enumerate(paper_ids):
        paper = storage.get_paper_by_id(paper_id)
        if not paper:
            report["failed"] += 1
            continue
        try:
            enrichment = discovery.get_work_enrichment(paper.openalex_id, paper.doi)
        except Exception as error:
            report["failed"] += 1
            safe_print(f"Features backfill failed [{paper_id}]: {paper.title[:60]} | {error}")
            continue

        has_data = (
            enrichment["openalex_topics"] != "[]"
            or enrichment["openalex_keywords"] != "[]"
            or enrichment["referenced_works"] != "[]"
        )
        storage.upsert_paper_features(PaperFeatures(
            paper_id=paper_id,
            openalex_topics_json=enrichment["openalex_topics"],
            openalex_keywords_json=enrichment["openalex_keywords"],
            referenced_works_json=enrichment["referenced_works"],
            cited_by_count=enrichment["cited_by_count"],
            is_retracted=enrichment["is_retracted"],
        ))
        if enrichment["openalex_id"] and not paper.openalex_id:
            storage.update_paper_bibliography(paper_id, paper.volume, paper.issue, enrichment["openalex_id"])

        if has_data:
            report["enriched"] += 1
        else:
            report["empty"] += 1

        if index < len(paper_ids) - 1:
            time.sleep(OpenAlexDiscovery.SEARCH_PAUSE_SECONDS)

    print(
        "Features backfill complete: "
        f"{report['enriched']} enriched, {report['empty']} still empty, "
        f"{report['failed']} failed"
    )
    return report


def backfill_method_labels(config: Optional[Config] = None, limit: int = 200) -> dict:
    """Label already-screened papers with a single AI research-method tag."""
    if config is None:
        config = get_config()

    storage = PaperStorage(config.database_path)
    papers = storage.get_papers_missing_method(limit=limit)
    report = {"requested": len(papers), "labeled": 0, "uncertain": 0, "failed": 0}
    print(f"Method-label backfill: {len(papers)} papers")
    if not papers:
        print("Backfill complete: 0 papers missing method labels")
        return report

    paper_filter = PaperFilter()
    for paper in papers:
        try:
            method = paper_filter.label_method(
                title=paper.title,
                abstract=paper.abstract,
                authors=paper.authors,
                journal=paper.journal,
            )
        except Exception as exc:
            report["failed"] += 1
            safe_print(f"Method label failed [{paper.id}]: {paper.title[:60]} | {exc}")
            continue
        storage.update_paper_method(paper.id, method)
        if method:
            report["labeled"] += 1
        else:
            report["uncertain"] += 1
        safe_print(f"Labeled [{paper.id}] {method or '(uncertain)'} | {paper.title[:60]}")

    print(
        "Backfill complete: "
        f"{report['labeled']} labeled, {report['uncertain']} uncertain, "
        f"{report['failed']} failed"
    )
    return report


def screen_pending_papers(config: Optional[Config] = None, limit: int = 20) -> int:
    """Run AI screening for papers currently waiting in the local queue."""
    if config is None:
        config = get_config()

    storage = PaperStorage(config.database_path)
    papers = storage.get_pending_screening_papers(limit=limit)
    print("Pending paper screening")
    print("=" * 40)
    print(f"Pending papers loaded: {len(papers)}")
    if not papers:
        print("Screened pending papers: 0")
        return 0

    paper_filter = PaperFilter()
    screened_count = 0
    error_count = 0
    for paper in papers:
        try:
            result = paper_filter.filter_paper(
                title=paper.title,
                abstract=paper.abstract,
                authors=paper.authors,
                journal=paper.journal,
            )
        except Exception as exc:
            error_count += 1
            storage.mark_filter_error(paper.id, str(exc))
            safe_print(f"Screening error [{paper.id}] | {paper.title} | {exc}")
            continue
        tags = result.get("tags", [])
        tags_text = ",".join(tags) if isinstance(tags, list) else str(tags or "")
        if storage.update_filter_result(
            paper_id=paper.id,
            relevance=result.get("relevance", "Low"),
            reason=result.get("reason", ""),
            tags=tags_text,
            summary=result.get("summary", ""),
            method=result.get("method", ""),
        ):
            screened_count += 1
            safe_print(
                f"Screened [{paper.id}] {result.get('relevance', 'Low')} | {paper.title}"
            )

    print(f"Screened pending papers: {screened_count}")
    print(f"Screening errors: {error_count}")
    return 0


def verify_coverage(config: Optional[Config] = None) -> int:
    """Verify local OpenAlex journal coverage against Crossref DOI coverage."""
    if config is None:
        config = get_config()

    config.database_path.parent.mkdir(parents=True, exist_ok=True)
    storage = PaperStorage(config.database_path)
    reports_dir = config.data_dir / "reports"
    dated_path = reports_dir / f"coverage_{datetime.now().strftime('%Y%m%d')}.json"
    latest_path = reports_dir / "coverage_latest.json"
    verifier = CoverageVerifier(storage)
    report = verifier.verify(config.get_tracked_journals(), output_path=dated_path)
    if not dated_path.exists():
        dated_path.parent.mkdir(parents=True, exist_ok=True)
        import json
        dated_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_path.write_text(dated_path.read_text(encoding="utf-8"), encoding="utf-8")
    summary = report["summary"]

    print("Coverage report")
    print("=" * 40)
    print(f"Journals checked: {summary.get('journals_checked', 0)}")
    print(f"OpenAlex DOI total: {summary.get('total_openalex_dois', 0)}")
    print(f"Crossref DOI total: {summary.get('total_crossref_dois', 0)}")
    print(f"Matched DOI total: {summary.get('total_matched', 0)}")
    print(f"Missing in OpenAlex: {summary.get('total_missing_in_openalex', 0)}")
    print(f"Missing in Crossref: {summary.get('total_missing_in_crossref', 0)}")
    print(f"Report: {dated_path}")
    if summary.get("errors"):
        print("Errors:")
        for error in summary["errors"][:5]:
            safe_print(f"- {error}")
    return 0


def _normalize_journal_name(name: str) -> str:
    import re

    normalized = (name or "").lower().replace("&", " and ")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return " ".join(normalized.split())


def _tracked_journal_name(journal_name: str, tracked_by_name: dict) -> str:
    journal = tracked_by_name.get(_normalize_journal_name(journal_name))
    if journal:
        return journal.get("name", "")
    return journal_name


def show_stats(config: Optional[Config] = None):
    """显示统计信息"""
    if config is None:
        config = get_config()

    storage = PaperStorage(config.database_path)
    stats = storage.get_statistics()

    print("\n论文追踪统计")
    print("=" * 40)
    print(f"总计论文: {stats['total']}")
    print(f"本周新增: {stats['this_week']}")
    print(f"\n按相关性:")
    print(f"  High:   {stats['relevance'].get('High', 0)}")
    print(f"  Medium: {stats['relevance'].get('Medium', 0)}")
    print(f"  Low:    {stats['relevance'].get('Low', 0)}")
    print(f"\n按状态:")
    for status, count in stats['status'].items():
        print(f"  {status}: {count}")


def export_csv(config: Optional[Config] = None, relevance: Optional[str] = None):
    """导出CSV"""
    if config is None:
        config = get_config()

    storage = PaperStorage(config.database_path)
    export_path = config.data_dir / f"papers_export_{relevance or 'all'}.csv"
    storage.export_to_csv(export_path, relevance=relevance)
    print(f"已导出到: {export_path}")


def export_public_data(config: Optional[Config] = None):
    """导出公开站数据 JSON"""
    if config is None:
        config = get_config()

    storage = PaperStorage(config.database_path)
    export_path = config.public_data_dir / "papers.json"
    PublicPaperExporter(storage).export_json(export_path)
    all_export_path = config.public_data_dir / "all_papers.json"
    PublicPaperExporter(storage).export_all_journal_updates_json(all_export_path)
    print(f"已导出公开数据到: {export_path}")


def sanitize_stored_titles(config: Optional[Config] = None) -> int:
    """清理数据库中已有论文标题的 HTML 标签。"""
    if config is None:
        config = get_config()

    storage = PaperStorage(config.database_path)
    changed = storage.sanitize_paper_titles()
    print(f"已清理论文标题: {changed} 篇")
    return 0


def translate_paper_library(config: Optional[Config] = None, limit: int = 100) -> int:
    """Translate missing or stale paper titles and abstracts into Simplified Chinese."""
    if config is None:
        config = get_config()
    if not config.siliconflow_api_key:
        print("Missing SILICONFLOW_API_KEY")
        return 2
    settings = config.translation_config
    translator = SiliconFlowTranslator(
        api_key=config.siliconflow_api_key,
        base_url=settings.get("base_url", "https://api.siliconflow.cn/v1"),
        model=settings.get("model", "tencent/Hunyuan-MT-7B"),
        token_budget_per_minute=int(settings.get("token_budget_per_minute", 60000)),
        max_retries=int(settings.get("max_retries", 6)),
    )
    report = translate_pending_papers(PaperStorage(config.database_path), translator, limit)
    print(
        "Translation batch: "
        f"selected={report['selected']} translated={report['translated']} failed={report['failed']}"
    )
    return 0


def publish_paper(config: Optional[Config], paper_id: int, is_public: bool):
    """设置论文公开状态"""
    if config is None:
        config = get_config()

    storage = PaperStorage(config.database_path)
    success = storage.set_paper_publication(paper_id, is_public)
    if not success:
        print(f"未找到论文 ID: {paper_id}")
        return 1

    paper = storage.get_paper_by_id(paper_id)
    action = "已设为公开发布" if is_public else "已取消公开发布"
    title = paper.title if paper else str(paper_id)
    safe_print(f"{action}: [{paper_id}] {title}")
    export_path = config.public_data_dir / "papers.json"
    PublicPaperExporter(storage).export_json(export_path)
    all_export_path = config.public_data_dir / "all_papers.json"
    PublicPaperExporter(storage).export_all_journal_updates_json(all_export_path)
    print(f"已刷新公开站数据: {export_path}")
    return 0


def publish_high_papers(config: Optional[Config] = None) -> int:
    """公开所有 High 论文，并刷新公开站数据"""
    if config is None:
        config = get_config()

    storage = PaperStorage(config.database_path)
    high_papers = storage.get_papers(relevance="High", limit=10000)
    published_count = 0
    for paper in high_papers:
        if paper.title.strip().lower() == "test paper":
            continue
        if not paper.is_public and storage.set_paper_publication(paper.id, True):
            published_count += 1

    export_path = config.public_data_dir / "papers.json"
    PublicPaperExporter(storage).export_json(export_path)
    all_export_path = config.public_data_dir / "all_papers.json"
    PublicPaperExporter(storage).export_all_journal_updates_json(all_export_path)
    print(f"已公开 High 论文: {published_count}")
    print(f"已刷新公开站数据: {export_path}")
    return 0


def update_public_workflow(config: Optional[Config] = None, refilter_limit: int = 20) -> int:
    """重筛错误论文，公开 High 论文，并刷新公开站数据。"""
    if config is None:
        config = get_config()

    print("Paper HOT 公开数据刷新")
    print("=" * 40)
    refilter_error_papers(config, limit=refilter_limit)
    publish_high_papers(config)
    print("公开刷新完成")
    return 0


def run_weekly_journal_workflow(
    config: Optional[Config] = None,
    limit_per_journal: int = 100,
    screen_limit: int = 50,
    max_screen_batches: int = 10,
    refilter_limit: int = 10,
    verify: bool = True,
) -> int:
    """Run the journal-first weekly workflow and persist a machine-readable report."""
    if config is None:
        config = get_config()

    started_at = datetime.now()
    storage = PaperStorage(config.database_path)
    before_stats = storage.get_statistics()
    report = {
        "started_at": started_at.isoformat(),
        "finished_at": "",
        "steps": {},
        "before": before_stats,
        "after": {},
    }

    print("Paper HOT weekly journal workflow")
    print("=" * 40)

    saved_count = ingest_journal_updates(config, limit_per_journal)
    report["steps"]["fetch_journals"] = {
        "limit_per_journal": limit_per_journal,
        "saved_new_papers": saved_count,
    }

    repair_report = repair_local_screening_queue(config)
    report["steps"]["repair_queue"] = repair_report

    screening_batches = []
    for batch_index in range(max_screen_batches):
        stats = storage.get_statistics()
        pending_count = stats.get("screening_status", {}).get("pending", 0)
        if pending_count <= 0:
            break
        before_batch = storage.get_statistics()
        screen_pending_papers(config, limit=screen_limit)
        after_batch = storage.get_statistics()
        before_screening = before_batch.get("screening_status", {})
        after_screening = after_batch.get("screening_status", {})
        screening_batches.append(
            {
                "batch": batch_index + 1,
                "requested_limit": screen_limit,
                "pending_before": pending_count,
                "screened_delta": after_screening.get("screened", 0)
                - before_screening.get("screened", 0),
                "error_delta": after_screening.get("error", 0)
                - before_screening.get("error", 0),
                "pending_after": after_screening.get("pending", 0),
            }
        )
    report["steps"]["screen_pending"] = {
        "screen_limit": screen_limit,
        "max_screen_batches": max_screen_batches,
        "batches": screening_batches,
    }

    features_report = backfill_openalex_features(config, limit=500)
    report["steps"]["backfill_features"] = features_report

    update_public_workflow(config, refilter_limit=refilter_limit)
    public_count = len(storage.get_public_papers(limit=10000))
    report["steps"]["update_public"] = {
        "refilter_limit": refilter_limit,
        "public_papers": public_count,
    }

    if config.siliconflow_api_key:
        translate_paper_library(config, limit=100)
        export_public_data(config)
        report["steps"]["translate_papers"] = {"limit": 100}
    else:
        report["steps"]["translate_papers"] = {"skipped": "missing SILICONFLOW_API_KEY"}

    hotspots_path = generate_monthly_hotspots(config)
    report["steps"]["generate_hotspots"] = {"output": str(hotspots_path)}

    if verify:
        verify_coverage(config)
        latest_coverage = config.data_dir / "reports" / "coverage_latest.json"
        if latest_coverage.exists():
            coverage_report = json.loads(latest_coverage.read_text(encoding="utf-8"))
            report["steps"]["verify_coverage"] = coverage_report.get("summary", {})
    else:
        report["steps"]["verify_coverage"] = {"skipped": True}

    report["after"] = storage.get_statistics()
    report["finished_at"] = datetime.now().isoformat()
    report_path = _write_weekly_run_report(config, report)
    print(f"Weekly report: {report_path}")
    return 0


def run_backfill_workflow(
    config: Optional[Config] = None,
    from_year: int = 2025,
    to_year: int = 2026,
    limit_per_journal: int = 1000,
    screen_limit: int = 50,
    max_screen_batches: int = 20,
    refilter_limit: int = 10,
    label_methods_limit: int = 1000,
    verify: bool = True,
) -> int:
    """Backfill a year range of journal works, screen, method-label, and refresh public data.

    Mirrors run_weekly_journal_workflow but (a) fetches the full [from_year, to_year]
    window instead of each journal's ``track_from_year`` and (b) runs the one-time
    ``label-methods`` backfill so papers screened before the method feature also get
    method badges. Order matters: backfill -> screen -> method-label -> public refresh.
    """
    if config is None:
        config = get_config()

    started_at = datetime.now()
    storage = PaperStorage(config.database_path)
    before_stats = storage.get_statistics()
    report = {
        "started_at": started_at.isoformat(),
        "finished_at": "",
        "steps": {},
        "before": before_stats,
        "after": {},
    }

    print("Paper HOT backfill workflow")
    print("=" * 40)

    saved_count = ingest_journal_backfill(
        config,
        from_year=from_year,
        to_year=to_year,
        max_per_journal=limit_per_journal,
    )
    report["steps"]["backfill_journals"] = {
        "from_year": from_year,
        "to_year": to_year,
        "limit_per_journal": limit_per_journal,
        "saved_new_papers": saved_count,
    }

    repair_report = repair_local_screening_queue(config)
    report["steps"]["repair_queue"] = repair_report

    screening_batches = []
    for batch_index in range(max_screen_batches):
        stats = storage.get_statistics()
        pending_count = stats.get("screening_status", {}).get("pending", 0)
        if pending_count <= 0:
            break
        before_batch = storage.get_statistics()
        screen_pending_papers(config, limit=screen_limit)
        after_batch = storage.get_statistics()
        before_screening = before_batch.get("screening_status", {})
        after_screening = after_batch.get("screening_status", {})
        screening_batches.append(
            {
                "batch": batch_index + 1,
                "requested_limit": screen_limit,
                "pending_before": pending_count,
                "screened_delta": after_screening.get("screened", 0)
                - before_screening.get("screened", 0),
                "error_delta": after_screening.get("error", 0)
                - before_screening.get("error", 0),
                "pending_after": after_screening.get("pending", 0),
            }
        )
    report["steps"]["screen_pending"] = {
        "screen_limit": screen_limit,
        "max_screen_batches": max_screen_batches,
        "batches": screening_batches,
    }

    # One-time method-label backfill for papers screened before the method feature.
    label_report = backfill_method_labels(config, limit=label_methods_limit)
    report["steps"]["label_methods"] = label_report

    update_public_workflow(config, refilter_limit=refilter_limit)
    public_count = len(storage.get_public_papers(limit=10000))
    report["steps"]["update_public"] = {
        "refilter_limit": refilter_limit,
        "public_papers": public_count,
    }

    hotspots_path = generate_monthly_hotspots(config)
    report["steps"]["generate_hotspots"] = {"output": str(hotspots_path)}

    if verify:
        verify_coverage(config)
        latest_coverage = config.data_dir / "reports" / "coverage_latest.json"
        if latest_coverage.exists():
            coverage_report = json.loads(latest_coverage.read_text(encoding="utf-8"))
            report["steps"]["verify_coverage"] = coverage_report.get("summary", {})
    else:
        report["steps"]["verify_coverage"] = {"skipped": True}

    report["after"] = storage.get_statistics()
    report["finished_at"] = datetime.now().isoformat()
    report_path = _write_backfill_run_report(config, report)
    print(f"Backfill report: {report_path}")
    return 0


def _write_backfill_run_report(config: Config, report: dict) -> Path:
    reports_dir = config.data_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dated_path = reports_dir / f"backfill_run_{timestamp}.json"
    latest_path = reports_dir / "backfill_run_latest.json"
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    dated_path.write_text(payload, encoding="utf-8")
    latest_path.write_text(payload, encoding="utf-8")
    return dated_path


def _write_weekly_run_report(config: Config, report: dict) -> Path:
    reports_dir = config.data_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dated_path = reports_dir / f"weekly_run_{timestamp}.json"
    latest_path = reports_dir / "weekly_run_latest.json"
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    dated_path.write_text(payload, encoding="utf-8")
    latest_path.write_text(payload, encoding="utf-8")
    return dated_path


def show_workflow_status(config: Optional[Config] = None) -> None:
    """显示采集、筛选、公开发布相关的工作流状态。"""
    if config is None:
        config = get_config()

    storage = PaperStorage(config.database_path)
    stats = storage.get_statistics()
    public_count = len(storage.get_public_papers(limit=10000))
    filter_error_count = len(storage.get_filter_error_papers(limit=10000))
    screening_stats = stats.get("screening_status", {})
    pending_count = screening_stats.get("pending", 0)
    screened_count = screening_stats.get("screened", 0)
    quarantined_count = screening_stats.get("quarantined", 0)

    print("Paper HOT 工作流状态")
    print("=" * 40)
    print(f"总计论文: {stats['total']}")
    print(f"High: {stats['relevance'].get('High', 0)}")
    print(f"Medium: {stats['relevance'].get('Medium', 0)}")
    print(f"Low: {stats['relevance'].get('Low', 0)}")
    print(f"Pending screening: {pending_count}")
    print(f"Screened: {screened_count}")
    print(f"Quarantined: {quarantined_count}")
    print(f"已公开论文: {public_count}")
    print(f"筛选错误: {filter_error_count}")

    method_stats = stats.get("method", {})
    labeled_methods = sum(method_stats.values())
    print(f"方法标签已标注: {labeled_methods}")
    for method, count in sorted(method_stats.items(), key=lambda item: -item[1]):
        print(f"  {method}: {count}")


def list_public_papers(config: Optional[Config] = None):
    """列出已公开论文"""
    if config is None:
        config = get_config()

    storage = PaperStorage(config.database_path)
    papers = storage.get_public_papers()
    print(f"已公开论文: {len(papers)}")
    for paper in papers:
        safe_print(f"- [{paper.id}] {paper.title} | {paper.relevance} | {paper.journal}")


def list_all_papers(config: Optional[Config] = None, limit: int = 100):
    """列出数据库中的论文，便于人工发布管理"""
    if config is None:
        config = get_config()

    storage = PaperStorage(config.database_path)
    papers = storage.get_papers(limit=limit)
    print(f"全部论文: {len(papers)}")
    for paper in papers:
        public_flag = int(paper.is_public)
        safe_print(
            f"- [{paper.id}] {paper.relevance or paper.screening_status} | "
            f"source={paper.source_type or 'unknown'} | public={public_flag} | "
            f"{paper.journal} | {paper.title}"
        )


def refilter_error_papers(config: Optional[Config] = None, limit: int = 20) -> int:
    """重筛之前 AI 筛选失败的论文"""
    if config is None:
        config = get_config()

    storage = PaperStorage(config.database_path)
    papers = storage.get_filter_error_papers(limit=limit)
    if not papers:
        print("没有需要重筛的错误论文")
        return 0

    paper_filter = PaperFilter()
    updated_count = 0
    error_count = 0
    for paper in papers:
        try:
            result = paper_filter.filter_paper(
                title=paper.title,
                abstract=paper.abstract,
                authors=paper.authors,
                journal=paper.journal,
            )
        except Exception as exc:
            error_count += 1
            storage.mark_filter_error(paper.id, str(exc))
            safe_print(f"重筛失败: [{paper.id}] {paper.title} | {exc}")
            continue
        tags = result.get("tags", [])
        tags_text = ",".join(tags) if isinstance(tags, list) else str(tags or "")
        if storage.update_filter_result(
            paper_id=paper.id,
            relevance=result.get("relevance", "Low"),
            reason=result.get("reason", ""),
            tags=tags_text,
            summary=result.get("summary", ""),
            method=result.get("method", ""),
        ):
            updated_count += 1
            print(f"已重筛: [{paper.id}] {paper.title} -> {result.get('relevance', 'Low')}")

    print(f"已重筛 {updated_count} 篇")
    print(f"重筛仍失败 {error_count} 篇")
    return 0


def run_doctor(config: Optional[Config] = None) -> int:
    """运行真实采集前的本地环境预检"""
    if config is None:
        config = get_config()

    config.database_path.parent.mkdir(parents=True, exist_ok=True)
    storage = PaperStorage(config.database_path)
    stats = storage.get_statistics()
    public_json = config.public_data_dir / "papers.json"
    keywords = config.get_discovery_keywords()

    checks = [
        ("Anthropic API Key", bool(config.anthropic_api_key), "ANTHROPIC_API_KEY 或 .env/key.env/.local/key.env", True),
        (
            "Semantic Scholar API Key",
            bool(config.semantic_scholar_api_key),
            "SEMANTIC_SCHOLAR_API_KEY 或 .env/key.env/.local/key.env",
            False,
        ),
        ("Database", config.database_path.exists(), str(config.database_path), True),
        ("Public JSON", public_json.exists(), str(public_json), False),
        ("Discovery keywords", bool(keywords), f"{len(keywords)} keywords", True),
    ]

    print("Paper HOT 环境预检")
    print("=" * 40)
    failed = 0
    for name, ok, detail, required in checks:
        status = "OK" if ok else "MISSING"
        print(f"{name}: {status} ({detail})")
        if required and not ok:
            failed += 1

    print("\n当前数据")
    print(f"- AI Base URL: {config.anthropic_base_url or 'Anthropic default'}")
    print(f"- AI Model: {config.claude_model}")
    print(f"- 数据库: {config.database_path}")
    print(f"- 论文总数: {stats['total']}")
    print(f"- 公开 JSON: {public_json}")
    print(f"- 发现关键词: {len(keywords)}")

    return 0 if failed == 0 else 1


def main():
    if "fetch-journals" in sys.argv[1:]:
        pre_parser = argparse.ArgumentParser(description="Fetch red-list journal updates")
        pre_parser.add_argument("--config", type=str, help="Config directory")
        pre_parser.add_argument("command", choices=["fetch-journals"])
        pre_parser.add_argument("--limit-per-journal", type=int, default=10)
        pre_args = pre_parser.parse_args()
        config = Config(Path(pre_args.config)) if pre_args.config else get_config()
        ingest_journal_updates(config, pre_args.limit_per_journal)
        return

    if "backfill-journals" in sys.argv[1:]:
        pre_parser = argparse.ArgumentParser(description="Backfill journal works for a year range")
        pre_parser.add_argument("--config", type=str, help="Config directory")
        pre_parser.add_argument("command", choices=["backfill-journals"])
        pre_parser.add_argument("--from-year", type=int, default=2025)
        pre_parser.add_argument("--to-year", type=int, default=2026)
        pre_parser.add_argument("--limit-per-journal", type=int, default=1000)
        pre_args = pre_parser.parse_args()
        config = Config(Path(pre_args.config)) if pre_args.config else get_config()
        ingest_journal_backfill(
            config,
            from_year=pre_args.from_year,
            to_year=pre_args.to_year,
            max_per_journal=pre_args.limit_per_journal,
        )
        return

    if "repair-queue" in sys.argv[1:]:
        pre_parser = argparse.ArgumentParser(description="Repair local screening queue")
        pre_parser.add_argument("--config", type=str, help="Config directory")
        pre_parser.add_argument("command", choices=["repair-queue"])
        pre_args = pre_parser.parse_args()
        config = Config(Path(pre_args.config)) if pre_args.config else get_config()
        repair_local_screening_queue(config)
        return

    if "screen-pending" in sys.argv[1:]:
        pre_parser = argparse.ArgumentParser(description="Screen papers waiting in the local queue")
        pre_parser.add_argument("--config", type=str, help="Config directory")
        pre_parser.add_argument("command", choices=["screen-pending"])
        pre_parser.add_argument("--limit", type=int, default=20)
        pre_args = pre_parser.parse_args()
        config = Config(Path(pre_args.config)) if pre_args.config else get_config()
        sys.exit(screen_pending_papers(config, pre_args.limit))

    if "verify-coverage" in sys.argv[1:]:
        pre_parser = argparse.ArgumentParser(description="Verify OpenAlex coverage against Crossref")
        pre_parser.add_argument("--config", type=str, help="Config directory")
        pre_parser.add_argument("command", choices=["verify-coverage"])
        pre_args = pre_parser.parse_args()
        config = Config(Path(pre_args.config)) if pre_args.config else get_config()
        sys.exit(verify_coverage(config))

    parser = argparse.ArgumentParser(description="计算传播论文追踪系统")
    parser.add_argument("--config", type=str, help="配置文件目录")
    parser.add_argument("--max-papers", type=int, default=20, help="最大处理论文数")

    subparsers = parser.add_subparsers(dest="command", help="子命令")
    subparsers.add_parser("search", help="仅搜索论文")
    subparsers.add_parser("stats", help="显示统计")
    subparsers.add_parser("export", help="导出CSV")
    subparsers.add_parser("export-public", help="导出公开站 JSON 数据")
    subparsers.add_parser("sanitize-titles", help="清理数据库中论文标题的 HTML 标签")
    translate_parser = subparsers.add_parser("translate-papers", help="用 SiliconFlow 翻译论文标题和摘要")
    translate_parser.add_argument("--limit", type=int, default=100, help="本批最多翻译论文数")
    subparsers.add_parser("generate-hotspots", help="从近一个月公开论文生成当期热点 JSON")
    bibliography_parser = subparsers.add_parser("backfill-bibliography", help="用 OpenAlex 回填卷号和期号")
    bibliography_parser.add_argument("--limit", type=int, default=10000, help="最多回填论文数")
    features_parser = subparsers.add_parser("backfill-features", help="用 OpenAlex 回填 topics/keywords/references/citations")
    features_parser.add_argument("--limit", type=int, default=10000, help="最多回填论文数")
    label_methods_parser = subparsers.add_parser("label-methods", help="为已筛选论文回填 AI 研究方法标签")
    label_methods_parser.add_argument("--limit", type=int, default=200, help="最多回填论文数")
    subparsers.add_parser("doctor", help="检查 API key、数据库、公开 JSON 和关键词配置")
    list_parser = subparsers.add_parser("list", help="列出数据库中的论文")
    list_parser.add_argument("--limit", type=int, default=100, help="最多列出论文数")
    refilter_parser = subparsers.add_parser("refilter-errors", help="重筛之前 AI 筛选失败的论文")
    refilter_parser.add_argument("--limit", type=int, default=20, help="最多重筛论文数")
    publish_parser = subparsers.add_parser("publish", help="将论文设为公开发布")
    publish_parser.add_argument("paper_id", type=int, help="论文 ID")
    unpublish_parser = subparsers.add_parser("unpublish", help="取消论文公开发布")
    unpublish_parser.add_argument("paper_id", type=int, help="论文 ID")
    subparsers.add_parser("publish-high", help="公开所有 High 论文并刷新公开站 JSON")
    subparsers.add_parser("list-public", help="列出已公开论文")
    update_public_parser = subparsers.add_parser("update-public", help="重筛错误论文、公开 High 论文并刷新公开站 JSON")
    update_public_parser.add_argument("--refilter-limit", type=int, default=20, help="最多重筛错误论文数")
    subparsers.add_parser("workflow-status", help="显示采集、筛选、公开发布工作流状态")
    weekly_parser = subparsers.add_parser("weekly-run", help="运行期刊优先的每周采集、筛选、发布和覆盖验证")
    weekly_parser.add_argument("--limit-per-journal", type=int, default=100, help="每本期刊最多抓取论文数")
    weekly_parser.add_argument("--screen-limit", type=int, default=50, help="每批最多筛选 pending 论文数")
    weekly_parser.add_argument("--max-screen-batches", type=int, default=10, help="本次最多筛选批次数")
    weekly_parser.add_argument("--refilter-limit", type=int, default=10, help="最多重筛错误论文数")
    weekly_parser.add_argument("--skip-coverage", action="store_true", help="跳过 Crossref 覆盖验证")
    backfill_parser = subparsers.add_parser("backfill-run", help="按年份范围补抓期刊论文并完成筛选、方法标签、发布（一次性追赶）")
    backfill_parser.add_argument("--from-year", type=int, default=2025, help="补抓起始年份（含），默认 2025")
    backfill_parser.add_argument("--to-year", type=int, default=2026, help="补抓结束年份（含），默认 2026")
    backfill_parser.add_argument("--limit-per-journal", type=int, default=1000, help="每本期刊最多抓取论文数")
    backfill_parser.add_argument("--screen-limit", type=int, default=50, help="每批最多筛选 pending 论文数")
    backfill_parser.add_argument("--max-screen-batches", type=int, default=20, help="本次最多筛选批次数")
    backfill_parser.add_argument("--refilter-limit", type=int, default=10, help="最多重筛错误论文数")
    backfill_parser.add_argument("--label-methods-limit", type=int, default=1000, help="为已筛选旧论文回填方法标签的数量")
    backfill_parser.add_argument("--skip-coverage", action="store_true", help="跳过 Crossref 覆盖验证")

    network_parser = subparsers.add_parser("build-hotspot-network", help="构建热点网络图谱静态数据")
    network_parser.add_argument("--analysis-days", type=int, default=180, help="分析时间窗口（天）")
    network_parser.add_argument("--recent-days", type=int, default=30, help="近期窗口（天）")
    network_parser.add_argument("--baseline-days", type=int, default=150, help="基线窗口（天）")
    network_parser.add_argument("--max-topics", type=int, default=40, help="最多展示主题数")

    subparsers.add_parser("validate-hotspot-data", help="校验已生成的热点静态数据")

    args = parser.parse_args()

    # 初始化配置
    if args.config:
        config = Config(Path(args.config))
    else:
        config = get_config()

    # 执行命令
    if args.command == "search":
        search_only(config)
    elif args.command == "stats":
        show_stats(config)
    elif args.command == "export":
        export_csv(config)
    elif args.command == "export-public":
        export_public_data(config)
    elif args.command == "sanitize-titles":
        sys.exit(sanitize_stored_titles(config))
    elif args.command == "translate-papers":
        sys.exit(translate_paper_library(config, args.limit))
    elif args.command == "generate-hotspots":
        print(f"已生成当期热点数据: {generate_monthly_hotspots(config)}")
    elif args.command == "backfill-bibliography":
        backfill_openalex_bibliography(config, args.limit)
    elif args.command == "backfill-features":
        backfill_openalex_features(config, args.limit)
    elif args.command == "label-methods":
        backfill_method_labels(config, args.limit)
    elif args.command == "doctor":
        sys.exit(run_doctor(config))
    elif args.command == "list":
        list_all_papers(config, args.limit)
    elif args.command == "refilter-errors":
        sys.exit(refilter_error_papers(config, args.limit))
    elif args.command == "publish":
        sys.exit(publish_paper(config, args.paper_id, True))
    elif args.command == "unpublish":
        sys.exit(publish_paper(config, args.paper_id, False))
    elif args.command == "publish-high":
        sys.exit(publish_high_papers(config))
    elif args.command == "list-public":
        list_public_papers(config)
    elif args.command == "update-public":
        sys.exit(update_public_workflow(config, args.refilter_limit))
    elif args.command == "workflow-status":
        show_workflow_status(config)
    elif args.command == "weekly-run":
        sys.exit(
            run_weekly_journal_workflow(
                config,
                limit_per_journal=args.limit_per_journal,
                screen_limit=args.screen_limit,
                max_screen_batches=args.max_screen_batches,
                refilter_limit=args.refilter_limit,
                verify=not args.skip_coverage,
            )
        )
    elif args.command == "backfill-run":
        sys.exit(
            run_backfill_workflow(
                config,
                from_year=args.from_year,
                to_year=args.to_year,
                limit_per_journal=args.limit_per_journal,
                screen_limit=args.screen_limit,
                max_screen_batches=args.max_screen_batches,
                refilter_limit=args.refilter_limit,
                label_methods_limit=args.label_methods_limit,
                verify=not args.skip_coverage,
            )
        )
    elif args.command == "build-hotspot-network":
        from .hotspot_network import NoHotspotCandidatesError, build_hotspot_network
        try:
            build_hotspot_network(
                config,
                analysis_days=args.analysis_days,
                recent_days=args.recent_days,
                baseline_days=args.baseline_days,
                max_topics=args.max_topics,
            )
        except NoHotspotCandidatesError as exc:
            safe_print(f"No hotspot candidates: {exc}")
            safe_print("Skipping hotspot network generation for this run.")
            sys.exit(0)
        except ValueError as exc:
            safe_print(f"Hotspot network build failed: {exc}")
            sys.exit(1)
    elif args.command == "validate-hotspot-data":
        from .hotspot_validation import validate_and_report
        data_dir = config.public_data_dir / "hotspots"
        required = ["manifest.json", "graph.json", "trends.json"]
        if not data_dir.is_dir() or not any((data_dir / name).is_file() for name in required):
            safe_print("No hotspot data generated yet; nothing to validate.")
            sys.exit(0)
        ok = validate_and_report(data_dir)
        sys.exit(0 if ok else 1)
    else:
        # 默认运行完整流程
        run_full_pipeline(config, args.max_papers)


if __name__ == "__main__":
    main()
