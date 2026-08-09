"""DOI-scoped author identity and affiliation enrichment.

Crossref supplies publisher-deposited author order, ORCID, and affiliation text.
Semantic Scholar supplies stable author IDs, aliases, and normalized affiliation
strings. Matching is deliberately paper-scoped so a common name is never merged
across unrelated papers without supporting identifiers.
"""

from __future__ import annotations

import re
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote

import requests

from .coverage import normalize_doi
from .storage import Paper, PaperStorage


def normalize_person_name(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).casefold()
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "", text)


def normalize_orcid(value: object) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"^https?://orcid\.org/", "", text)
    return text.upper()


def _unique_strings(values: Iterable[object]) -> List[str]:
    result: List[str] = []
    seen = set()
    for value in values:
        item = str(value or "").strip()
        key = item.casefold()
        if item and key not in seen:
            seen.add(key)
            result.append(item)
    return result


class _RetryingJsonClient:
    MAX_RETRIES = 5

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()

    def _request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        for attempt in range(self.MAX_RETRIES + 1):
            response = self.session.request(method, url, timeout=45, **kwargs)
            if response.status_code == 429 or response.status_code >= 500:
                if attempt >= self.MAX_RETRIES:
                    response.raise_for_status()
                retry_after = response.headers.get("Retry-After", "")
                try:
                    delay = float(retry_after)
                except ValueError:
                    delay = min(60.0, 2.0 ** attempt)
                time.sleep(max(0.5, delay))
                continue
            response.raise_for_status()
            return response.json()
        raise requests.RequestException("retry budget exhausted")


class CrossrefAuthorClient(_RetryingJsonClient):
    API = "https://api.crossref.org"

    def __init__(self, session: Optional[requests.Session] = None):
        super().__init__(session)
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "PaperHOT/0.1 (mailto:paper-hot@example.invalid)",
        })

    def fetch_authors(self, doi: str) -> List[Dict[str, Any]]:
        data = self._request("GET", f"{self.API}/works/{quote(normalize_doi(doi), safe='')}")
        message = data.get("message") or {}
        result = []
        for order, author in enumerate(message.get("author") or []):
            given = str(author.get("given") or "").strip()
            family = str(author.get("family") or "").strip()
            name = " ".join(part for part in (given, family) if part)
            result.append({
                "order": order,
                "name": name,
                "orcid": normalize_orcid(author.get("ORCID")),
                "affiliations": _unique_strings(
                    item.get("name") for item in (author.get("affiliation") or []) if isinstance(item, dict)
                ),
            })
        return result


class SemanticScholarAuthorClient(_RetryingJsonClient):
    API = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, api_key: str = "", session: Optional[requests.Session] = None):
        super().__init__(session)
        self.session.headers.update({"Accept": "application/json"})
        if api_key:
            self.session.headers["x-api-key"] = api_key

    def fetch_paper_authors(self, doi: str) -> List[Dict[str, Any]]:
        paper_id = quote(f"DOI:{normalize_doi(doi)}", safe=":")
        data = self._request(
            "GET",
            f"{self.API}/paper/{paper_id}",
            params={"fields": "authors"},
        )
        basic = data.get("authors") or []
        ids = [str(item.get("authorId")) for item in basic if item.get("authorId")]
        details: Dict[str, Dict[str, Any]] = {}
        if ids:
            rows = self._request(
                "POST",
                f"{self.API}/author/batch",
                # The Graph Author endpoint exposes stable IDs, aliases, and
                # affiliations but does not accept Paper-only externalIds.
                params={"fields": "name,aliases,affiliations"},
                json={"ids": ids},
            )
            if isinstance(rows, list):
                details = {str(row.get("authorId")): row for row in rows if row}

        result = []
        for order, item in enumerate(basic):
            author_id = str(item.get("authorId") or "")
            detail = details.get(author_id, {})
            result.append({
                "order": order,
                "author_id": author_id,
                "name": str(detail.get("name") or item.get("name") or "").strip(),
                "orcid": "",
                "aliases": _unique_strings(detail.get("aliases") or []),
                "affiliations": _unique_strings(detail.get("affiliations") or []),
            })
        return result


def match_paper_authors(
    crossref: List[Dict[str, Any]], semantic: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], int]:
    """Match two author lists without using global-name-only identity joins."""
    used_semantic = set()
    output: List[Dict[str, Any]] = []
    ambiguous = 0

    for order, crossref_author in enumerate(crossref):
        crossref_name = str(crossref_author.get("name") or "")
        normalized = normalize_person_name(crossref_name)
        orcid = normalize_orcid(crossref_author.get("orcid"))
        candidates: List[Tuple[Dict[str, Any], str, float]] = []

        if orcid:
            candidates = [
                (author, "orcid", 1.0)
                for author in semantic
                if author.get("order") not in used_semantic
                and normalize_orcid(author.get("orcid")) == orcid
            ]
        if not candidates and normalized:
            candidates = [
                (author, "exact_name", 0.9)
                for author in semantic
                if author.get("order") not in used_semantic
                and normalized in {
                    normalize_person_name(author.get("name")),
                    *(normalize_person_name(alias) for alias in author.get("aliases", [])),
                }
            ]
        if len(candidates) > 1:
            same_position = [item for item in candidates if item[0].get("order") == order]
            candidates = [(same_position[0][0], "exact_name_and_position", 0.97)] if len(same_position) == 1 else []
            if not candidates:
                ambiguous += 1
        if not candidates and order < len(semantic) and order not in used_semantic:
            positional = semantic[order]
            left = re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKD", crossref_name).casefold())
            right = re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKD", str(positional.get("name") or "")).casefold())
            if left and right and left[-1] == right[-1]:
                candidates = [(positional, "surname_and_position", 0.75)]

        matched = candidates[0] if len(candidates) == 1 else None
        semantic_author = matched[0] if matched else {}
        if matched:
            used_semantic.add(int(semantic_author.get("order", order)))
        output.append({
            "author_order": order,
            "display_name": crossref_name or str(semantic_author.get("name") or ""),
            "normalized_name": normalized or normalize_person_name(semantic_author.get("name")),
            "orcid": orcid or normalize_orcid(semantic_author.get("orcid")),
            "semantic_scholar_author_id": str(semantic_author.get("author_id") or ""),
            "aliases": semantic_author.get("aliases", []),
            "affiliations": _unique_strings([
                *crossref_author.get("affiliations", []),
                *semantic_author.get("affiliations", []),
            ]),
            "match_method": matched[1] if matched else "crossref_only",
            "match_confidence": matched[2] if matched else 0.4,
        })

    for author in semantic:
        if author.get("order") in used_semantic:
            continue
        output.append({
            "author_order": len(output),
            "display_name": str(author.get("name") or ""),
            "normalized_name": normalize_person_name(author.get("name")),
            "orcid": normalize_orcid(author.get("orcid")),
            "semantic_scholar_author_id": str(author.get("author_id") or ""),
            "aliases": author.get("aliases", []),
            "affiliations": author.get("affiliations", []),
            "match_method": "semantic_scholar_only",
            "match_confidence": 0.4,
        })
    return output, ambiguous


def enrich_paper_authors(
    storage: PaperStorage,
    crossref_client: CrossrefAuthorClient,
    semantic_client: SemanticScholarAuthorClient,
    limit: int = 25,
    force: bool = False,
) -> Dict[str, int]:
    papers = storage.get_papers_missing_author_enrichment(limit=limit, force=force)
    report = {
        "selected_papers": len(papers),
        "enriched_papers": 0,
        "failed_papers": 0,
        "authors": 0,
        "matched_s2_authors": 0,
        "authors_with_orcid": 0,
        "authors_with_affiliations": 0,
        "ambiguous_matches": 0,
        "crossref_unavailable": 0,
        "semantic_scholar_unavailable": 0,
    }
    for paper in papers:
        try:
            try:
                crossref = crossref_client.fetch_authors(paper.doi)
            except Exception as exc:
                print(f"  Crossref unavailable for paper {paper.id}: {exc}")
                crossref = []
                report["crossref_unavailable"] += 1
            try:
                semantic = semantic_client.fetch_paper_authors(paper.doi)
            except Exception as exc:
                print(f"  Semantic Scholar unavailable for paper {paper.id}: {exc}")
                semantic = []
                report["semantic_scholar_unavailable"] += 1
            authors, ambiguous = match_paper_authors(crossref, semantic)
            if not authors:
                raise ValueError("no author metadata returned")
            storage.replace_paper_author_enrichment(int(paper.id or 0), authors)
            report["enriched_papers"] += 1
            report["authors"] += len(authors)
            report["matched_s2_authors"] += sum(bool(a["semantic_scholar_author_id"]) for a in authors)
            report["authors_with_orcid"] += sum(bool(a["orcid"]) for a in authors)
            report["authors_with_affiliations"] += sum(bool(a["affiliations"]) for a in authors)
            report["ambiguous_matches"] += ambiguous
        except Exception as exc:
            print(f"  author enrichment failed for paper {paper.id}: {exc}")
            report["failed_papers"] += 1
    return report


def write_author_enrichment_report(report: Dict[str, int], path: Path) -> None:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
