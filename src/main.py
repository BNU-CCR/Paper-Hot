"""
计算传播论文追踪系统 - 主入口

用法:
    python -m src.main                    # 运行完整流程
    python -m src.main --search            # 仅搜索论文
    python -m src.main --filter            # 仅筛选
    python -m src.main --stats             # 查看统计
    python -m src.main --export            # 导出CSV
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from .config import Config, get_config
from .storage import PaperStorage, Paper
from .discovery import PaperDiscovery
from .filter import PaperFilter
from .notification import NotificationSender
from .publication import PublicPaperExporter


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

    print("\n" + "=" * 50)
    print(f"完成! 处理了 {saved_count} 篇新论文")
    print("=" * 50)

    return saved_count


def search_only(config: Optional[Config] = None):
    """仅搜索并显示论文"""
    if config is None:
        config = get_config()

    discovery = PaperDiscovery(config.semantic_scholar_api_key)
    print("搜索最近论文...")
    papers = discovery.search_recent_papers(limit=20)

    print(f"\n发现 {len(papers)} 篇论文:\n")
    for i, p in enumerate(papers, 1):
        print(f"{i}. {p.title}")
        print(f"   Authors: {p.authors}")
        print(f"   Journal: {p.journal} ({p.published_date})")
        print(f"   DOI: {p.doi}")
        print()


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
    print(f"已导出公开数据到: {export_path}")


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
    print(f"{action}: [{paper_id}] {title}")
    export_path = config.public_data_dir / "papers.json"
    PublicPaperExporter(storage).export_json(export_path)
    print(f"已刷新公开站数据: {export_path}")
    return 0


def list_public_papers(config: Optional[Config] = None):
    """列出已公开论文"""
    if config is None:
        config = get_config()

    storage = PaperStorage(config.database_path)
    papers = storage.get_public_papers()
    print(f"已公开论文: {len(papers)}")
    for paper in papers:
        print(f"- [{paper.id}] {paper.title} | {paper.relevance} | {paper.journal}")


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
    for paper in papers:
        result = paper_filter.filter_paper(
            title=paper.title,
            abstract=paper.abstract,
            authors=paper.authors,
            journal=paper.journal,
        )
        tags = result.get("tags", [])
        tags_text = ",".join(tags) if isinstance(tags, list) else str(tags or "")
        if storage.update_filter_result(
            paper_id=paper.id,
            relevance=result.get("relevance", "Low"),
            reason=result.get("reason", ""),
            tags=tags_text,
            summary=result.get("summary", ""),
        ):
            updated_count += 1
            print(f"已重筛: [{paper.id}] {paper.title} -> {result.get('relevance', 'Low')}")

    print(f"已重筛 {updated_count} 篇")
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
        ("Anthropic API Key", bool(config.anthropic_api_key), "ANTHROPIC_API_KEY 或 .env/key.env", True),
        (
            "Semantic Scholar API Key",
            bool(config.semantic_scholar_api_key),
            "SEMANTIC_SCHOLAR_API_KEY 或 .env/key.env",
            True,
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
    parser = argparse.ArgumentParser(description="计算传播论文追踪系统")
    parser.add_argument("--config", type=str, help="配置文件目录")
    parser.add_argument("--max-papers", type=int, default=20, help="最大处理论文数")

    subparsers = parser.add_subparsers(dest="command", help="子命令")
    subparsers.add_parser("search", help="仅搜索论文")
    subparsers.add_parser("stats", help="显示统计")
    subparsers.add_parser("export", help="导出CSV")
    subparsers.add_parser("export-public", help="导出公开站 JSON 数据")
    subparsers.add_parser("doctor", help="检查 API key、数据库、公开 JSON 和关键词配置")
    refilter_parser = subparsers.add_parser("refilter-errors", help="重筛之前 AI 筛选失败的论文")
    refilter_parser.add_argument("--limit", type=int, default=20, help="最多重筛论文数")
    publish_parser = subparsers.add_parser("publish", help="将论文设为公开发布")
    publish_parser.add_argument("paper_id", type=int, help="论文 ID")
    unpublish_parser = subparsers.add_parser("unpublish", help="取消论文公开发布")
    unpublish_parser.add_argument("paper_id", type=int, help="论文 ID")
    subparsers.add_parser("list-public", help="列出已公开论文")

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
    elif args.command == "doctor":
        sys.exit(run_doctor(config))
    elif args.command == "refilter-errors":
        sys.exit(refilter_error_papers(config, args.limit))
    elif args.command == "publish":
        sys.exit(publish_paper(config, args.paper_id, True))
    elif args.command == "unpublish":
        sys.exit(publish_paper(config, args.paper_id, False))
    elif args.command == "list-public":
        list_public_papers(config)
    else:
        # 默认运行完整流程
        run_full_pipeline(config, args.max_papers)


if __name__ == "__main__":
    main()
