"""Coverage verification between local OpenAlex records and Crossref metadata."""

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from .storage import PaperStorage, Paper


def normalize_doi(doi: str) -> str:
    value = (doi or "").strip().lower()
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", value, flags=re.IGNORECASE)


class CrossrefClient:
    """Small Crossref Works API client for journal/year coverage checks."""

    CROSSREF_API = "https://api.crossref.org"
    MAX_RETRIES = 3
    RETRY_BACKOFF_SECONDS = 1.0

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "PaperHOT/0.1 (mailto:paper-hot@example.invalid)",
        })

    def fetch_journal_works(
        self,
        issns: List[str],
        from_year: int = 2026,
        until_date: Optional[str] = None,
        rows: int = 100,
    ) -> List[Dict[str, Any]]:
        records_by_doi: Dict[str, Dict[str, Any]] = {}
        filters = [
            f"from-pub-date:{from_year}-01-01",
            f"until-pub-date:{until_date or datetime.now().date().isoformat()}",
            "type:journal-article",
        ]
        for issn in issns:
            if not issn:
                continue
            data = self._get_json(
                f"/journals/{issn}/works",
                {
                    "filter": ",".join(filters),
                    "select": "DOI,title,container-title,published-print,published-online",
                    "rows": rows,
                    "sort": "published",
                    "order": "desc",
                },
            )
            for item in (data.get("message") or {}).get("items", []):
                record = self._item_to_record(item)
                if record["doi"]:
                    records_by_doi[record["doi"]] = record
        return list(records_by_doi.values())

    def _item_to_record(self, item: Dict[str, Any]) -> Dict[str, Any]:
        title = item.get("title") or []
        container = item.get("container-title") or []
        return {
            "doi": normalize_doi(item.get("DOI", "")),
            "title": title[0] if title else "",
            "journal": container[0] if container else "",
            "published_date": self._published_date(item),
        }

    def _published_date(self, item: Dict[str, Any]) -> str:
        date_parts = (
            (item.get("published-print") or {}).get("date-parts")
            or (item.get("published-online") or {}).get("date-parts")
            or []
        )
        if not date_parts:
            return ""
        parts = date_parts[0]
        if not parts:
            return ""
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 1
        day = int(parts[2]) if len(parts) > 2 else 1
        return f"{year:04d}-{month:02d}-{day:02d}"

    def _get_json(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        last_error: Optional[requests.RequestException] = None
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.session.get(
                    f"{self.CROSSREF_API}{path}",
                    params=params,
                    timeout=30,
                )
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as error:
                last_error = error
                if not self._is_retryable_http_error(error) or attempt == self.MAX_RETRIES - 1:
                    raise
                time.sleep(self._retry_delay_seconds(error, attempt))
            except requests.RequestException as error:
                last_error = error
                raise

        if last_error:
            raise last_error
        raise requests.RequestException("unknown Crossref request failure")

    def _is_retryable_http_error(self, error: requests.HTTPError) -> bool:
        response = getattr(error, "response", None)
        status_code = getattr(response, "status_code", None)
        return status_code in {429, 500, 502, 503, 504}

    def _retry_delay_seconds(self, error: requests.HTTPError, attempt: int) -> float:
        response = getattr(error, "response", None)
        headers = getattr(response, "headers", {}) if response is not None else {}
        retry_after = headers.get("Retry-After") if headers else None
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                pass
        return self.RETRY_BACKOFF_SECONDS * (2 ** attempt)


class CoverageVerifier:
    """Compare local OpenAlex red-list coverage with Crossref DOI coverage."""

    def __init__(self, storage: PaperStorage, crossref_client: Optional[CrossrefClient] = None):
        self.storage = storage
        self.crossref_client = crossref_client or CrossrefClient()

    def verify(
        self,
        journals: List[Dict[str, Any]],
        output_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        local_papers = self.storage.get_all_journal_update_papers(limit=10000)
        report_journals = []
        errors = []

        for journal in journals:
            journal_name = journal.get("name", "")
            issns = self._journal_issns(journal)
            from_year = int(journal.get("track_from_year", 2026) or 2026)
            local_records = self._local_records_for_journal(local_papers, journal)
            crossref_records: List[Dict[str, Any]] = []
            error = ""
            if issns:
                try:
                    crossref_records = self.crossref_client.fetch_journal_works(
                        issns,
                        from_year=from_year,
                    )
                except requests.RequestException as exc:
                    error = str(exc)
                    errors.append(f"{journal_name}: {error}")
            else:
                error = "missing ISSN"
                errors.append(f"{journal_name}: {error}")

            report_journals.append(
                self._compare_journal(journal_name, issns, local_records, crossref_records, error)
            )

        summary = {
            "generated_at": datetime.now().isoformat(),
            "journals_checked": len(report_journals),
            "total_openalex_dois": sum(item["openalex_count"] for item in report_journals),
            "total_crossref_dois": sum(item["crossref_count"] for item in report_journals),
            "total_matched": sum(item["matched_count"] for item in report_journals),
            "total_missing_in_openalex": sum(len(item["missing_in_openalex"]) for item in report_journals),
            "total_missing_in_crossref": sum(len(item["missing_in_crossref"]) for item in report_journals),
            "errors": errors,
        }
        report = {"summary": summary, "journals": report_journals}
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report

    def _compare_journal(
        self,
        journal_name: str,
        issns: List[str],
        local_records: List[Paper],
        crossref_records: List[Dict[str, Any]],
        error: str = "",
    ) -> Dict[str, Any]:
        openalex_by_doi = {
            normalize_doi(paper.doi): paper
            for paper in local_records
            if normalize_doi(paper.doi)
        }
        crossref_by_doi = {
            normalize_doi(record.get("doi", "")): record
            for record in crossref_records
            if normalize_doi(record.get("doi", ""))
        }
        openalex_dois = set(openalex_by_doi)
        crossref_dois = set(crossref_by_doi)
        matched = sorted(openalex_dois & crossref_dois)
        missing_in_openalex = sorted(crossref_dois - openalex_dois)
        missing_in_crossref = sorted(openalex_dois - crossref_dois)
        return {
            "journal": journal_name,
            "issn": issns,
            "openalex_count": len(openalex_dois),
            "crossref_count": len(crossref_dois),
            "matched_count": len(matched),
            "missing_in_openalex": missing_in_openalex,
            "missing_in_crossref": missing_in_crossref,
            "openalex_without_doi": [
                paper.title for paper in local_records if not normalize_doi(paper.doi)
            ],
            "crossref_error": error,
        }

    def _local_records_for_journal(
        self,
        local_papers: List[Paper],
        journal: Dict[str, Any],
    ) -> List[Paper]:
        names = {
            self._normalize_name(journal.get("name", "")),
            self._normalize_name(journal.get("abbr", "")),
        }
        for key in ("aliases", "openalex_aliases"):
            for alias in journal.get(key, []) or []:
                names.add(self._normalize_name(alias))
        names.discard("")
        return [
            paper for paper in local_papers
            if self._normalize_name(paper.tracked_journal or paper.journal) in names
        ]

    def _journal_issns(self, journal: Dict[str, Any]) -> List[str]:
        issns = []
        if journal.get("issn_l"):
            issns.append(str(journal["issn_l"]))
        issns.extend(str(issn) for issn in (journal.get("issn") or []))
        deduped = []
        seen = set()
        for issn in issns:
            if issn and issn not in seen:
                seen.add(issn)
                deduped.append(issn)
        return deduped

    def _normalize_name(self, name: str) -> str:
        normalized = (name or "").lower().replace("&", " and ")
        normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
        return " ".join(normalized.split())
