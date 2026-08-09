"""公开发布数据导出模块"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from .storage import PaperStorage, Paper


class PublicPaperExporter:
    """导出公开论文数据给静态站或其他只读消费方"""

    def __init__(self, storage: PaperStorage):
        self.storage = storage

    def export_json(self, output_path: Path) -> None:
        papers = self.storage.get_public_papers()
        payload = [self._serialize_paper(paper) for paper in papers]
        self._write_json(output_path, payload)

    def export_all_journal_updates_json(self, output_path: Path) -> None:
        papers = self.storage.get_all_journal_update_papers()
        payload = [self._serialize_paper(paper) for paper in papers]
        self._write_json(output_path, payload)

    def _write_json(self, output_path: Path, payload: List[Dict[str, Any]]) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _serialize_paper(self, paper: Paper) -> Dict[str, Any]:
        return {
            "id": paper.id,
            "title": paper.title,
            "authors": self._split_csv_field(paper.authors),
            "journal": paper.journal,
            "published_date": paper.published_date,
            "relevance": paper.relevance,
            "score": paper.score,
            "abstract": paper.abstract,
            "summary": paper.summary,
            "reason": paper.reason,
            "tags": self._split_csv_field(paper.tags),
            "method": paper.method,
            "doi": paper.doi,
            "source_url": paper.link,
            "detail_slug": self._slugify(paper.title),
            "source_type": paper.source_type,
            "screening_status": paper.screening_status,
            "tracked_journal": paper.tracked_journal,
            "volume": paper.volume,
            "issue": paper.issue,
        }

    def _split_csv_field(self, value: str) -> List[str]:
        return [part.strip() for part in value.split(",") if part.strip()]

    def _slugify(self, title: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower())
        return slug.strip("-")
