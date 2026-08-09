"""Text normalization shared by ingestion, storage, and export."""

import html
import re


_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_HTML_TAG_RE = re.compile(r"</?[A-Za-z][^>]*>")
_WHITESPACE_RE = re.compile(r"\s+")
_TRANSLATED_TITLE_PREFIX_RE = re.compile(
    r"^(?:\*\*\s*)?(?:"
    r"论文标题|标题|"
    r"这篇论文的标题是|这个论文的标题是|"
    r"将这篇论文的标题翻译为(?:中文如下)?|"
    r"翻译这篇论文的标题(?:为)?|"
    r"中文翻译"
    r")\s*[：:]\s*(?:\*\*\s*)?",
    re.IGNORECASE,
)
_TRANSLATED_ABSTRACT_PREFIX_RE = re.compile(
    r"^(?:\*\*\s*)?(?:"
    r"论文摘要|摘要|"
    r"这篇论文的摘要如下|该论文的摘要如下|"
    r"本文的?摘要(?:如下)?|"
    r"请翻译这篇论文的摘要|"
    r"这篇论文的摘要是|"
    r"中文摘要|摘要翻译"
    r")\s*[：:]\s*(?:\*\*\s*)?",
    re.IGNORECASE,
)
_MARKDOWN_FENCE_RE = re.compile(r"^```(?:text|markdown)?\s*|\s*```$", re.IGNORECASE)
_TITLE_WRAPPERS = (("《", "》"), ("“", "”"), ("‘", "’"), ('"', '"'), ("'", "'"))


def clean_paper_title(value: object) -> str:
    """Return a plain-text paper title without publisher formatting markup."""
    title = html.unescape(str(value or ""))
    title = _HTML_COMMENT_RE.sub("", title)
    title = _HTML_TAG_RE.sub("", title)
    return _WHITESPACE_RE.sub(" ", title).strip()


def clean_translated_title(value: object) -> str:
    """Remove model-added labels and outer punctuation from a translated title."""
    title = clean_paper_title(value)
    title = _TRANSLATED_TITLE_PREFIX_RE.sub("", title).strip()

    if title.startswith("**") and title.endswith("**") and len(title) > 4:
        title = title[2:-2].strip()

    # Models frequently wrap the entire translation in book-title marks or
    # quotation marks. Only remove a balanced outer pair, preserving punctuation
    # that is meaningful inside the title.
    changed = True
    while changed and len(title) >= 2:
        changed = False
        for opening, closing in _TITLE_WRAPPERS:
            if title.startswith(opening) and title.endswith(closing):
                title = title[len(opening):-len(closing)].strip()
                changed = True
                break
    return title


def clean_translated_abstract(value: object) -> str:
    """Remove model-added response labels while preserving abstract paragraphs."""
    abstract = html.unescape(str(value or "")).strip()
    abstract = _HTML_COMMENT_RE.sub("", abstract)
    abstract = _HTML_TAG_RE.sub("", abstract)
    abstract = _MARKDOWN_FENCE_RE.sub("", abstract).strip()
    abstract = _TRANSLATED_ABSTRACT_PREFIX_RE.sub("", abstract).strip()
    return abstract
