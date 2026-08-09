"""Text normalization shared by ingestion, storage, and export."""

import html
import re


_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_HTML_TAG_RE = re.compile(r"</?[A-Za-z][^>]*>")
_WHITESPACE_RE = re.compile(r"\s+")


def clean_paper_title(value: object) -> str:
    """Return a plain-text paper title without publisher formatting markup."""
    title = html.unescape(str(value or ""))
    title = _HTML_COMMENT_RE.sub("", title)
    title = _HTML_TAG_RE.sub("", title)
    return _WHITESPACE_RE.sub(" ", title).strip()
