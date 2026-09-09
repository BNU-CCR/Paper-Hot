"""
LLM topic labeling with fingerprint caching.

Generates Chinese labels, descriptions, and "why hot" explanations for
each topic cluster.  Uses the same Anthropic-compatible API as the
existing screening pipeline.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Any, Dict, List, Optional

import anthropic

from .config import Config


DEFAULT_LABEL_SYSTEM_PROMPT = """你是计算传播研究的中文编辑。请为一组算法发现的论文主题生成中文名称和说明。

要求：
- label_zh 必须简洁（不超过 20 字），准确概括该主题当前的研究议题。
- 优先根据输入中最新的论文（近 30 天发表的论文优先）命名当前议题；更早的论文只用来辅助确认主题边界，不能让旧内容主导命名。
- description 用 1-2 句话说明该主题的核心关注点（不超过 80 字）。
- why_hot 用一句话基于输入给出的"近30天论文数 vs 此前150天论文数"及日均发表速度解释近期研究活动是升温、持平还是降温（不超过 60 字）。
- keywords 列出 3-6 个该主题的核心英文关键词。
- 不要编造未在输入中给出的论文标题、作者或数据。
- 不得在 label_zh、description、why_hot 或 keywords 中使用任何具体国家或地区名称。即使论文来自多个国家，也必须按共同研究问题、对象或机制命名。
- 优先使用中文传播学领域的学术术语。

严格只输出 JSON 数组：
[
  {
    "topic_index": 0,
    "label_zh": "算法中介的政治信息环境",
    "description": "研究推荐系统与搜索引擎如何影响政治信息接触与态度形成。",
    "why_hot": "近30天日均发表速度约为前期的2倍，研究分布扩展至4本期刊。",
    "keywords": ["recommender systems", "search engines", "political efficacy"]
  }
]"""


COUNTRY_NAMES = (
    "中国", "日本", "韩国", "朝鲜", "美国", "英国", "法国", "德国", "意大利", "西班牙",
    "葡萄牙", "荷兰", "比利时", "瑞典", "挪威", "丹麦", "芬兰", "冰岛", "瑞士", "奥地利",
    "波兰", "俄罗斯", "乌克兰", "罗马尼亚", "匈牙利", "希腊", "土耳其", "以色列", "伊朗",
    "印度", "印度尼西亚", "印尼", "新加坡", "马来西亚", "菲律宾", "越南", "泰国", "澳大利亚",
    "新西兰", "加拿大", "墨西哥", "巴西", "阿根廷", "智利", "南非", "肯尼亚", "尼日利亚",
    "台湾", "香港", "澳门", "china", "japan", "korea", "united states", "usa", "united kingdom",
    "britain", "france", "germany", "italy", "spain", "netherlands", "belgium", "sweden", "norway",
    "denmark", "finland", "switzerland", "austria", "poland", "russia", "ukraine", "romania",
    "hungary", "turkey", "israel", "iran", "india", "indonesia", "singapore", "malaysia",
    "philippines", "vietnam", "thailand", "australia", "canada", "mexico", "brazil", "argentina",
    "south africa",
)


def _contains_country_name(value: Any) -> bool:
    text = " ".join(str(item) for item in value) if isinstance(value, list) else str(value or "")
    lowered = text.casefold()
    return any(name.casefold() in lowered for name in COUNTRY_NAMES)


def normalize_keywords(value: Any) -> List[str]:
    """Normalize occasionally malformed LLM keyword output to a string list."""
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()][:8]
    if isinstance(value, str):
        return [item.strip() for item in re.split(r"[,，;；]", value) if item.strip()][:8]
    return []


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
        self.system_prompt = config.hotspot_label_system_prompt or DEFAULT_LABEL_SYSTEM_PROMPT

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
            cached_text = [
                topic.get("label_zh", ""),
                topic.get("description", ""),
                topic.get("why_hot", ""),
                *(topic.get("keywords") or []),
            ]
            if (
                topic.get("label_zh")
                and topic.get("_label_fingerprint") == fingerprint
                and not _contains_country_name(cached_text)
            ):
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

        # Retry with backoff: DeepSeek's compatible endpoint occasionally returns
        # only thinking blocks (no usable text) or a truncated reply under load.
        labels: List[Dict[str, Any]] = []
        last_error: Optional[Exception] = None
        for attempt in range(3):
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
                if labels:
                    break
                last_error = ValueError("LLM labeling response could not be parsed as JSON")
            except Exception as exc:
                last_error = exc
            if attempt < 2:
                time.sleep(2.0 * (2 ** attempt))
        if not labels:
            print(f"  LLM labeling failed: {last_error}")

        # Apply labels to topics
        label_by_index: Dict[int, Dict[str, Any]] = {}
        for item in labels:
            label_by_index[item.get("topic_index", -1)] = item

        for batch_idx, topic_idx in enumerate(needs_label):
            label = label_by_index.get(batch_idx)
            topic = topics[topic_idx]
            if label and _contains_country_name([
                label.get("label_zh", ""),
                label.get("description", ""),
                label.get("why_hot", ""),
                *normalize_keywords(label.get("keywords", [])),
            ]):
                print(f"  Rejected country-specific label for topic {topic.get('topic_id', batch_idx)}")
                label = None
            if label:
                topic["label_zh"] = str(label.get("label_zh") or "")[:40]
                topic["description"] = str(label.get("description") or "")[:160]
                topic["why_hot"] = str(label.get("why_hot") or "")[:120]
                topic["keywords"] = normalize_keywords(label.get("keywords", []))
                topic["_label_fingerprint"] = topic.get("_fingerprint", "")
            else:
                # A transient API/parse failure must not erase a stable label
                # inherited from the previous run. Keep its old fingerprint so
                # the next run retries the refresh instead of caching failure.
                existing_label = str(topic.get("label_zh") or "").strip()
                tid = str(topic.get("topic_id") or "").strip()
                if not existing_label or existing_label == tid:
                    fallback = _synthesize_fallback_label(topic, candidates, batch_idx)
                    topic["label_zh"] = fallback["label_zh"]
                    topic["description"] = fallback["description"]
                    topic["why_hot"] = fallback["why_hot"]
                    topic["keywords"] = fallback["keywords"]
                else:
                    topic.setdefault("description", "")
                    topic.setdefault("why_hot", "")
                    topic.setdefault("keywords", [])

        # Apply manual overrides from topic_overrides.yaml
        self._apply_overrides(topics)

        for topic_idx, topic in enumerate(topics):
            visible_text = [
                topic.get("label_zh", ""),
                topic.get("description", ""),
                topic.get("why_hot", ""),
                *(topic.get("keywords") or []),
            ]
            if _contains_country_name(visible_text):
                fallback = _synthesize_fallback_label(topic, candidates, topic_idx)
                topic.update(fallback)

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
        blocks = getattr(response, "content", [])
        # Prefer explicit text-type blocks (skips DeepSeek thinking blocks).
        for block in blocks:
            if getattr(block, "type", None) == "text":
                value = getattr(block, "text", None)
                if value:
                    return value.strip()
        # Some providers omit the block type; fall back to the first block with text.
        for block in blocks:
            value = getattr(block, "text", None)
            if value:
                return value.strip()
        raise ValueError("LLM labeling response had no text content")

    @staticmethod
    def _parse_label_response(
        text: str, expected_count: int,
    ) -> List[Dict[str, Any]]:
        cleaned = text.strip()
        # Strip DeepSeek thinking tags if returned as plain text
        cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL).strip()
        # Extract markdown json block if present
        if "```" in cleaned:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
            if match:
                cleaned = match.group(1).strip()
        try:
            result = json.loads(cleaned)
            if isinstance(result, list):
                return result
            if isinstance(result, dict):
                if isinstance(result.get("topics"), list):
                    return result["topics"]
                # A single topic object without a wrapper array.
                if "label_zh" in result:
                    return [result]
            return []
        except json.JSONDecodeError:
            # Try to extract a JSON array from the surrounding text.
            start = cleaned.find("[")
            end = cleaned.rfind("]") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(cleaned[start:end])
                except json.JSONDecodeError:
                    pass
            return []


def _synthesize_fallback_label(
    topic: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    index: int = 0,
) -> Dict[str, Any]:
    """Synthesize a human-readable topic label when LLM generation fails."""
    paper_ids = set(topic.get("recent_paper_ids") or topic.get("paper_ids", []))
    matched = [c for c in candidates if int(c.get("id", 0)) in paper_ids]

    tag_counts: Dict[str, int] = {}
    for p in matched:
        p_tags = p.get("tags", [])
        if isinstance(p_tags, str):
            p_tags = [t.strip() for t in p_tags.split(",") if t.strip()]
        for t in p_tags:
            if t and not _contains_country_name(t):
                tag_counts[t] = tag_counts.get(t, 0) + 1

    top_tags = sorted(tag_counts.keys(), key=lambda k: tag_counts[k], reverse=True)[:3]
    if top_tags:
        label = "与".join(top_tags[:2]) if len(top_tags) >= 2 else top_tags[0]
        label = f"{label}研究"
    else:
        label = f"计算传播前沿议题 {index + 1}"

    return {
        "label_zh": label[:40],
        "description": f"聚焦于{label}及相关传播学议题的学术探讨与前沿成果。",
        "why_hot": "该领域近期在多家红榜期刊中有相关论文发表。",
        "keywords": normalize_keywords(top_tags or ["计算传播", "前沿研究"]),
    }


def _topic_fingerprint(
    topic: Dict[str, Any],
    candidates: List[Dict[str, Any]],
) -> str:
    """Deterministic hash for a topic's content — used for label caching.

    The hash covers the recent-30-day paper titles plus the signed growth rate,
    so a label is regenerated whenever the topic's current activity changes.
    """
    paper_ids = sorted(topic.get("recent_paper_ids") or topic.get("paper_ids", [])[:10])
    titles = []
    for pid in paper_ids[:10]:
        for c in candidates:
            if int(c.get("id", 0)) == pid:
                titles.append(str(c.get("title", ""))[:120])
                break

    data = json.dumps({
        "paper_count": topic.get("size", 0),
        "recent_count": topic.get("recent_count", 0),
        "baseline_count": topic.get("baseline_count", 0),
        "growth_rate": topic.get("growth_rate", 0.0),
        "journal_count": topic.get("journal_count", 0),
        "recent_paper_titles": titles,
    }, sort_keys=True, ensure_ascii=False)

    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]


def _topic_prompt_block(
    batch_index: int,
    topic: Dict[str, Any],
    candidates: List[Dict[str, Any]],
) -> str:
    """Build a structured prompt block for one topic.

    Recent-30-day papers are shown first so the LLM names the current direction
    of the topic; older papers only appear when there are no recent ones.
    """
    paper_ids = (topic.get("recent_paper_ids") or topic.get("paper_ids", []))[:6]
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

    growth_rate = topic.get("growth_rate", 0.0)
    growth_pct = f"{growth_rate * 100:+.0f}%"

    return (
        f"topic_index: {batch_index}\n"
        f"OpenAlex 主题: {topic_names or '未知'}\n"
        f"论文数量: 近180天 {topic.get('size', 0)} 篇 "
        f"(近30天 {topic.get('recent_count', 0)} 篇 / "
        f"此前150天 {topic.get('baseline_count', 0)} 篇, "
        f"日均速度变化 {growth_pct}, "
        f"覆盖 {topic.get('journal_count', 0)} 本期刊)\n"
        f"代表性论文（优先近期论文）:\n{papers_text}"
    ).strip()
