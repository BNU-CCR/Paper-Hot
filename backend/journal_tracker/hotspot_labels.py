"""
LLM topic labeling with fingerprint caching.

Generates Chinese labels, descriptions, and "why hot" explanations for
each topic cluster.  Uses the same Anthropic-compatible API as the
existing screening pipeline.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

import anthropic

from .config import Config


DEFAULT_LABEL_SYSTEM_PROMPT = """你是计算传播研究的中文编辑。请为一组算法发现的论文主题生成中文名称和说明。

要求：
- 每个主题的 label_zh 必须简洁（不超过 20 字），准确概括该主题的研究议题。
- description 用 1-2 句话说明该主题的核心关注点（不超过 80 字）。
- why_hot 用一句话解释近期的研究活动变化（不超过 60 字）。
- keywords 列出 3-6 个该主题的核心英文关键词。
- 不要编造未在输入中给出的论文标题、作者或数据。
- 优先使用中文传播学领域的学术术语。

严格只输出 JSON 数组：
[
  {
    "topic_index": 0,
    "label_zh": "算法中介的政治信息环境",
    "description": "研究推荐系统与搜索引擎如何影响政治信息接触与态度形成。",
    "why_hot": "近30天论文份额较前期增长74%，研究分布扩展至4本期刊。",
    "keywords": ["recommender systems", "search engines", "political efficacy"]
  }
]"""


class TopicLabeler:
    """Label topic clusters via the Anthropic-compatible API."""

    def __init__(self, config: Config):
        if not config.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for topic labeling")
        self.config = config
        kwargs: Dict[str, Any] = {"api_key": config.anthropic_api_key}
        if config.anthropic_base_url:
            kwargs["base_url"] = config.anthropic_base_url
        self.client = anthropic.Anthropic(**kwargs)
        self.model = config.claude_model
        self.system_prompt = config.hotspot_system_prompt or DEFAULT_LABEL_SYSTEM_PROMPT

    def label_topics(
        self,
        topics: List[Dict[str, Any]],
        candidates: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate Chinese labels for a batch of topics.

        Topics are updated in-place with label_zh, description, why_hot, and
        keywords fields.  Topics whose fingerprint matches a previous run are
        skipped.
        """
        # Separate topics that need labeling from those with cached fingerprints
        needs_label: List[int] = []  # indices into topics
        for idx, topic in enumerate(topics):
            fingerprint = _topic_fingerprint(topic, candidates)
            topic["_fingerprint"] = fingerprint

            # Skip if already has a valid label from cache
            if topic.get("label_zh") and topic.get("_label_fingerprint") == fingerprint:
                continue
            needs_label.append(idx)

        if not needs_label:
            return topics

        # Build one batch prompt for all topics needing labels
        prompt_parts: List[str] = []
        for batch_idx, topic_idx in enumerate(needs_label):
            topic = topics[topic_idx]
            prompt_parts.append(_topic_prompt_block(batch_idx, topic, candidates))

        batch_text = "\n---\n".join(prompt_parts)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                system=self.system_prompt,
                messages=[{
                    "role": "user",
                    "content": (
                        f"请为以下 {len(needs_label)} 个研究主题生成中文名称和说明。\n\n"
                        f"{batch_text}\n\n"
                        "严格只输出 JSON 数组，每个元素包含 topic_index, label_zh, "
                        "description, why_hot, keywords。"
                    ),
                }],
            )
            text = self._response_text(response)
            labels = self._parse_label_response(text, len(needs_label))
        except Exception as exc:
            print(f"  LLM labeling failed: {exc}")
            labels = []

        # Apply labels to topics
        label_by_index: Dict[int, Dict[str, Any]] = {}
        for item in labels:
            label_by_index[item.get("topic_index", -1)] = item

        for batch_idx, topic_idx in enumerate(needs_label):
            label = label_by_index.get(batch_idx)
            topic = topics[topic_idx]
            if label:
                topic["label_zh"] = str(label.get("label_zh") or "")[:40]
                topic["description"] = str(label.get("description") or "")[:160]
                topic["why_hot"] = str(label.get("why_hot") or "")[:120]
                topic["keywords"] = label.get("keywords", [])[:8]
            else:
                # Fallback: use OpenAlex topic names
                topic["label_zh"] = topic.get("label_en", topic.get("topic_id", ""))
                topic["description"] = ""
                topic["why_hot"] = ""
                topic["keywords"] = []
            topic["_label_fingerprint"] = topic.get("_fingerprint", "")

        # Apply manual overrides from topic_overrides.yaml
        self._apply_overrides(topics)

        return topics

    def _apply_overrides(self, topics: List[Dict[str, Any]]) -> None:
        """Apply manual rename/merge rules from topic_overrides.yaml."""
        overrides = self.config.topic_overrides

        # Rename
        rename_map = overrides.get("rename", {})
        if rename_map:
            for topic in topics:
                oa_id = topic.get("openalex_topic_id", "")
                if oa_id and oa_id in rename_map:
                    zh = rename_map[oa_id].get("zh", "")
                    if zh:
                        topic["label_zh"] = zh

    @staticmethod
    def _response_text(response: Any) -> str:
        for block in getattr(response, "content", []):
            value = getattr(block, "text", None)
            if value:
                return value.strip()
        raise ValueError("LLM labeling response had no text content")

    @staticmethod
    def _parse_label_response(
        text: str, expected_count: int,
    ) -> List[Dict[str, Any]]:
        try:
            result = json.loads(text)
            if isinstance(result, list):
                return result
            if isinstance(result, dict) and "topics" in result:
                return result["topics"]
            return []
        except json.JSONDecodeError:
            # Try to extract JSON array from markdown
            start = text.find("[")
            end = text.rfind("]") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            return []


def _topic_fingerprint(
    topic: Dict[str, Any],
    candidates: List[Dict[str, Any]],
) -> str:
    """Deterministic hash for a topic's content — used for label caching."""
    paper_ids = sorted(topic.get("paper_ids", [])[:10])
    titles = []
    for pid in paper_ids:
        for c in candidates:
            if int(c.get("id", 0)) == pid:
                titles.append(str(c.get("title", ""))[:120])
                break

    data = json.dumps({
        "paper_count": topic.get("size", 0),
        "recent_count": topic.get("recent_count", 0),
        "journal_count": topic.get("journal_count", 0),
        "paper_titles": titles,
    }, sort_keys=True, ensure_ascii=False)

    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]


def _topic_prompt_block(
    batch_index: int,
    topic: Dict[str, Any],
    candidates: List[Dict[str, Any]],
) -> str:
    """Build a structured prompt block for one topic."""
    paper_ids = topic.get("paper_ids", [])[:6]
    papers_text = ""
    for pid in paper_ids:
        for c in candidates:
            if int(c.get("id", 0)) == pid:
                title = str(c.get("title", ""))[:150]
                papers_text += f"  - {title}\n"
                break

    openalex_topics = topic.get("openalex_topics", [])
    topic_names = ", ".join(
        t.get("name", "") for t in (openalex_topics if isinstance(openalex_topics, list) else [])
        if t.get("name")
    )[:200]

    return (
        f"topic_index: {batch_index}\n"
        f"OpenAlex 主题: {topic_names or '未知'}\n"
        f"论文数量: {topic.get('size', 0)} 篇 "
        f"(近30天 {topic.get('recent_count', 0)} 篇, "
        f"覆盖 {topic.get('journal_count', 0)} 本期刊)\n"
        f"代表性论文:\n{papers_text}"
    ).strip()
