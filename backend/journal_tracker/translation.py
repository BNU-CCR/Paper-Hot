"""Rate-limited SiliconFlow client for academic Chinese translation."""

import math
import random
import time
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

import requests

from .storage import Paper, PaperStorage


class TranslationAuthError(RuntimeError):
    """Raised when the configured SiliconFlow key is invalid or unauthorized."""


@dataclass
class _Usage:
    timestamp: float
    tokens: int


class SiliconFlowTranslator:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.siliconflow.cn/v1",
        model: str = "tencent/Hunyuan-MT-7B",
        token_budget_per_minute: int = 60000,
        max_retries: int = 6,
        session: Optional[requests.Session] = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.token_budget = token_budget_per_minute
        self.max_retries = max_retries
        self.session = session or requests.Session()
        self.clock = clock
        self.sleep = sleep
        self.usage: List[_Usage] = []

    @staticmethod
    def estimate_tokens(text: str) -> int:
        return max(1, math.ceil(len(text) / 3))

    def _reserve(self, tokens: int) -> None:
        tokens = min(tokens, self.token_budget)
        while True:
            now = self.clock()
            self.usage = [entry for entry in self.usage if now - entry.timestamp < 60]
            used = sum(entry.tokens for entry in self.usage)
            if used + tokens <= self.token_budget:
                self.usage.append(_Usage(now, tokens))
                return
            wait_for = max(0.1, 60.1 - (now - self.usage[0].timestamp))
            self.sleep(wait_for)

    def translate_text(self, text: str, field: str) -> str:
        source = text.strip()
        if not source:
            return ""
        source_tokens = self.estimate_tokens(source)
        # Keep input + output comfortably inside the model's 32K context.
        if source_tokens > 16000:
            chunks = [source[index:index + 45000] for index in range(0, len(source), 45000)]
            return "\n\n".join(self.translate_text(chunk, field) for chunk in chunks)
        max_tokens = min(8192, max(256, source_tokens * 2))
        self._reserve(source_tokens + max_tokens)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是学术翻译器。把输入准确翻译为简体中文，保留专有名词、缩写、数字和引文；只输出译文，不解释。",
                },
                {"role": "user", "content": f"请翻译这篇论文的{field}：\n\n{source}"},
            ],
            "temperature": 0.1,
            "max_tokens": max_tokens,
            "stream": False,
        }
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json=payload,
                    timeout=120,
                )
            except requests.RequestException as exc:
                if attempt >= self.max_retries:
                    raise RuntimeError(f"SiliconFlow request failed: {exc}") from exc
                self.sleep(min(160.0, 5.0 * (2 ** attempt)) + random.uniform(0, 1))
                continue
            if response.status_code in {401, 403}:
                raise TranslationAuthError("SILICONFLOW_API_KEY is invalid or unauthorized")
            if response.status_code == 429 or response.status_code >= 500:
                if attempt >= self.max_retries:
                    raise RuntimeError(f"SiliconFlow HTTP {response.status_code}: {response.text[:300]}")
                retry_after = response.headers.get("Retry-After", "")
                try:
                    delay = float(retry_after)
                except ValueError:
                    delay = min(160.0, 5.0 * (2 ** attempt)) + random.uniform(0, 1)
                self.sleep(min(300.0, max(1.0, delay)))
                continue
            response.raise_for_status()
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            translated = str(content or "").strip()
            if not translated:
                raise RuntimeError("SiliconFlow returned an empty translation")
            return translated
        raise RuntimeError("SiliconFlow retry budget exhausted")

    def translate_paper(self, paper: Paper) -> Tuple[str, str]:
        return (
            self.translate_text(paper.title, "标题"),
            self.translate_text(paper.abstract, "摘要") if paper.abstract else "",
        )


def translate_pending_papers(storage: PaperStorage, translator: SiliconFlowTranslator, limit: int) -> dict:
    papers = storage.get_papers_needing_translation(limit)
    translated = 0
    failed = 0
    for paper in papers:
        try:
            title_zh, abstract_zh = translator.translate_paper(paper)
            source_hash = storage.translation_source_hash(paper.title, paper.abstract)
            storage.update_paper_translation(paper.id, title_zh, abstract_zh, translator.model, source_hash)
            translated += 1
        except TranslationAuthError:
            raise
        except Exception as exc:
            storage.mark_translation_error(paper.id, str(exc))
            failed += 1
    return {"selected": len(papers), "translated": translated, "failed": failed}
