"""Generate public monthly research hotspots from recently published papers."""

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import anthropic

from .config import Config
from .publication import PublicPaperExporter
from .storage import PaperStorage


DEFAULT_SYSTEM_PROMPT = """你是计算传播研究的编辑。请从近一个月已公开的论文中归纳当期主要研究议题。

要求：
- 归纳 4 到 6 个互不重复、具有解释力的研究议题，而不是简单罗列关键词。
- 每个议题都必须关联 2 到 3 篇候选论文；若候选论文不足，可关联 1 篇。
- 只能使用输入中给出的论文 ID，不能编造论文、作者、研究发现或日期。
- 议题标题和说明使用简洁中文；说明不超过 50 字。
- 优先呈现计算传播、平台、AI、算法、数字方法、网络与信息环境中的可辨识趋势。

严格只输出 JSON：
{
  "topics": [
    {"title": "议题标题", "description": "为什么这是当期热点", "paper_ids": [1, 2]}
  ]
}"""


class MonthlyHotspotGenerator:
    """Anthropic-compatible LLM generator for the public monthly hotspot feed."""

    def __init__(self, config: Config):
        if not config.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")
        self.config = config
        kwargs = {"api_key": config.anthropic_api_key}
        if config.anthropic_base_url:
            kwargs["base_url"] = config.anthropic_base_url
        self.client = anthropic.Anthropic(**kwargs)
        self.model = config.claude_model
        self.system_prompt = config.hotspot_system_prompt or DEFAULT_SYSTEM_PROMPT

    def generate(self, papers: List[Dict[str, Any]], anchor_date: date) -> List[Dict[str, Any]]:
        # Keep the aggregation prompt comfortably below the context/output limits of
        # Anthropic-compatible reasoning models. Forty recent public papers are
        # sufficient to identify monthly trends without losing the final JSON block.
        candidates = papers[:40]
        if not candidates:
            return []
        lines = []
        for paper in candidates:
            lines.append(json.dumps({
                "id": paper["id"],
                "title": paper["title"],
                "journal": paper["journal"],
                "published_date": paper["published_date"],
                "summary": paper["summary"][:160],
                "tags": paper["tags"],
            }, ensure_ascii=False))
        response = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            system=self.system_prompt,
            messages=[{
                "role": "user",
                "content": "统计窗口截至 {date}。以下是候选论文（JSON Lines）：\n{papers}".format(
                    date=anchor_date.isoformat(), papers="\n".join(lines)
                ),
            }],
        )
        text = self._response_text(response)
        payload = self._parse_json(text)
        return self._validate_topics(payload.get("topics"), {paper["id"] for paper in candidates})

    @staticmethod
    def _response_text(response: Any) -> str:
        for block in getattr(response, "content", []):
            value = getattr(block, "text", None)
            if value:
                return value.strip()
        raise ValueError("热点生成响应中没有可解析文本")

    @staticmethod
    def _parse_json(text: str) -> Dict[str, Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start, end = text.find("{"), text.rfind("}") + 1
            if start < 0 or end <= start:
                raise ValueError("热点生成响应不是 JSON")
            return json.loads(text[start:end])

    @staticmethod
    def _validate_topics(raw_topics: Any, candidate_ids: Set[int]) -> List[Dict[str, Any]]:
        if not isinstance(raw_topics, list):
            raise ValueError("热点生成响应缺少 topics 数组")
        topics: List[Dict[str, Any]] = []
        used_titles = set()
        for raw in raw_topics:
            if not isinstance(raw, dict):
                continue
            title = str(raw.get("title") or "").strip()
            description = str(raw.get("description") or "").strip()
            if not title or title in used_titles:
                continue
            ids = []
            for value in raw.get("paper_ids") or []:
                try:
                    paper_id = int(value)
                except (TypeError, ValueError):
                    continue
                if paper_id in candidate_ids and paper_id not in ids:
                    ids.append(paper_id)
            if not ids:
                continue
            topics.append({"title": title[:80], "description": description[:160], "paper_ids": ids[:5]})
            used_titles.add(title)
            if len(topics) == 8:
                break
        if len(topics) < 3:
            raise ValueError("热点生成结果少于 3 个有效议题")
        return topics


def _parse_date(value: str) -> Optional[date]:
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _public_papers(storage: PaperStorage) -> List[Dict[str, Any]]:
    exporter = PublicPaperExporter(storage)
    papers = storage.get_public_papers(limit=10000)
    institutions = storage.get_paper_institutions([int(paper.id) for paper in papers if paper.id])
    return [
        exporter._serialize_paper(paper, institutions.get(int(paper.id or 0), []))
        for paper in papers
    ]


def generate_monthly_hotspots(config: Config) -> Path:
    """Write a public hotspots.json based only on the latest 30 days of published papers."""
    storage = PaperStorage(config.database_path)
    public_papers = _public_papers(storage)
    dated = [(paper, _parse_date(str(paper.get("published_date") or ""))) for paper in public_papers]
    known_dates = [value for _, value in dated if value]
    anchor_date = max(known_dates) if known_dates else date.today()
    start_date = anchor_date - timedelta(days=30)
    recent = [paper for paper, published in dated if published and start_date <= published <= anchor_date]
    recent.sort(key=lambda paper: (str(paper.get("published_date") or ""), int(paper.get("id") or 0)), reverse=True)
    topics = MonthlyHotspotGenerator(config).generate(recent, anchor_date)
    payload = {
        "period_start": start_date.isoformat(),
        "period_end": anchor_date.isoformat(),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_paper_count": len(recent),
        "topics": topics,
    }
    output_path = config.public_data_dir / "hotspots.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path
