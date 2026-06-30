"""论文发现模块

支持两种方式：
1. asta-skill (MCP) - Claude Code中直接使用
2. Semantic Scholar API - Python脚本直接调用
"""

import requests
import time
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .config import get_config


@dataclass
class DiscoveredPaper:
    """发现的论文"""
    title: str
    abstract: str
    authors: str
    journal: str
    published_date: str
    link: str
    doi: str
    citation_count: int = 0
    openalex_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "abstract": self.abstract,
            "authors": self.authors,
            "journal": self.journal,
            "published_date": self.published_date,
            "link": self.link,
            "doi": self.doi,
            "citation_count": self.citation_count,
            "openalex_id": self.openalex_id,
        }


class PaperDiscovery:
    """
    论文发现模块

    优先级：
    1. 如果在Claude Code环境中，直接使用 asta-skill MCP工具
    2. 否则使用Semantic Scholar API
    """

    SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"

    # 计算传播相关关键词
    DEFAULT_KEYWORDS = [
        "computational communication",
        "social media computation",
        "digital communication",
        "network analysis communication",
        "natural language processing social media",
        "machine learning communication",
        "AI social communication",
        "algorithm media",
        "social network analysis",
        "big data communication",
    ]

    # 目标期刊
    TARGET_JOURNALS = [
        "Human Communication Research",
        "Communication Research",
        "Information, Communication & Society",
        "New Media & Society",
        "Journal of Computer-Mediated Communication",
        "Political Communication",
        "Science Communication",
    ]

    MAX_RETRIES = 3
    RETRY_BACKOFF_SECONDS = 1.0
    SEARCH_PAUSE_SECONDS = 0.8
    MAX_RECENT_SEARCH_QUERIES = 3

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化论文发现模块

        Args:
            api_key: Semantic Scholar API Key (可选，用于提高请求限制)
        """
        config = get_config()
        self.api_key = api_key or config.semantic_scholar_api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json"
        })
        if self.api_key:
            self.session.headers["x-api-key"] = self.api_key
        self.last_run_report: Dict[str, Any] = self._empty_run_report()
        self.last_query_error: Optional[str] = None

    def search_papers(
        self,
        query: str,
        year: Optional[int] = None,
        limit: int = 10
    ) -> List[DiscoveredPaper]:
        """
        搜索论文

        Args:
            query: 搜索关键词
            year: 发表年份 (可选)
            limit: 返回数量限制

        Returns:
            List[DiscoveredPaper]: 发现的论文列表
        """
        search_query = query
        if year:
            search_query = f"{query} {year}"

        params = {
            "query": search_query,
            "limit": limit,
            "fields": "title,abstract,authors,year,journal,venue,externalIds,url,citationCount"
        }

        self.last_query_error = None
        try:
            data = self._get_json("/paper/search", params)

            papers = []
            for item in data.get("data", []):
                # 提取期刊名
                journal = ""
                if item.get("journal"):
                    journal = item["journal"].get("name", "")
                elif item.get("venue"):
                    journal = item.get("venue", "")

                # 提取DOI
                doi = ""
                external_ids = item.get("externalIds", {})
                if external_ids:
                    doi = external_ids.get("DOI", "")

                # 提取作者
                authors = ""
                authors_list = item.get("authors", [])
                if authors_list:
                    authors = ", ".join([a.get("name", "") for a in authors_list[:5]])
                    if len(authors_list) > 5:
                        authors += " et al."

                # 构建链接
                link = item.get("url", "")
                if doi and not link:
                    link = f"https://doi.org/{doi}"

                papers.append(DiscoveredPaper(
                    title=item.get("title", ""),
                    abstract=item.get("abstract", "") or "",
                    authors=authors,
                    journal=journal,
                    published_date=str(item.get("year", "")),
                    link=link,
                    doi=doi,
                    citation_count=item.get("citationCount", 0)
                ))

            return papers

        except requests.RequestException as e:
            self.last_query_error = str(e)
            print(f"搜索论文时出错: {e}")
            return []

    def search_by_journal(
        self,
        journal: str,
        year: Optional[int] = None,
        limit: int = 10
    ) -> List[DiscoveredPaper]:
        """
        按期刊搜索论文

        Args:
            journal: 期刊名称
            year: 发表年份
            limit: 返回数量限制

        Returns:
            List[DiscoveredPaper]: 发现的论文列表
        """
        papers = self.search_papers(journal, year, limit)
        expected_journal = self._normalize_journal_name(journal)
        return [
            paper for paper in papers
            if self._normalize_journal_name(paper.journal) == expected_journal
        ]

    def search_journal_updates(
        self,
        journals: Optional[List[Dict[str, Any]]] = None,
        from_year: int = 2026,
        limit_per_journal: int = 10,
    ) -> List[DiscoveredPaper]:
        """按红榜期刊逐个抓取更新，并记录期刊覆盖报告。"""
        if journals is None:
            journals = get_config().get_tracked_journals()
        if not journals or limit_per_journal <= 0:
            self.last_run_report = self._empty_run_report()
            return []

        all_papers = []
        report = self._empty_run_report()
        report["requested_queries"] = len(journals)

        for index, journal_config in enumerate(journals):
            journal_name = journal_config.get("name", "")
            if not journal_name:
                continue
            year = int(journal_config.get("track_from_year", from_year) or from_year)
            report["query_limits"][journal_name] = limit_per_journal
            self.last_query_error = None
            query_error: Optional[str] = None
            try:
                papers = self.search_by_journal(
                    journal_name,
                    year=year,
                    limit=limit_per_journal,
                )
            except requests.RequestException as error:
                query_error = str(error)
                papers = []

            query_error = query_error or getattr(self, "last_query_error", None)
            if query_error:
                report["failed_queries"] += 1
                report["errors"].append(f"{journal_name}: {query_error}")
            elif papers:
                report["successful_queries"] += 1
            else:
                report["empty_queries"] += 1

            all_papers.extend(papers)
            if index < len(journals) - 1:
                time.sleep(self.SEARCH_PAUSE_SECONDS)

        unique_papers = self._dedupe_papers(all_papers)
        report["raw_papers"] = len(all_papers)
        report["returned_papers"] = len(unique_papers)
        report["duplicate_papers"] = max(0, len(all_papers) - len(unique_papers))
        self.last_run_report = report
        return unique_papers

    def search_recent_papers(
        self,
        keywords: Optional[List[str]] = None,
        days: int = 7,
        limit: int = 20
    ) -> List[DiscoveredPaper]:
        """
        搜索最近发表的论文

        Args:
            keywords: 关键词列表 (默认使用DEFAULT_KEYWORDS)
            days: 最近天数
            limit: 返回数量限制

        Returns:
            List[DiscoveredPaper]: 发现的论文列表
        """
        if keywords is None:
            keywords = get_config().get_discovery_keywords() or self.DEFAULT_KEYWORDS
        if not keywords or limit <= 0:
            return []

        query_count = min(len(keywords), limit, self.MAX_RECENT_SEARCH_QUERIES)
        selected_keywords = keywords[:query_count]
        request_limits = self._allocate_limits(limit, query_count)

        all_papers = []
        report = self._empty_run_report()
        report["requested_queries"] = len(selected_keywords)
        report["query_limits"] = dict(zip(selected_keywords, request_limits))
        for index, keyword in enumerate(selected_keywords):
            self.last_query_error = None
            query_error: Optional[str] = None
            try:
                papers = self.search_papers(keyword, limit=request_limits[index])
            except requests.RequestException as error:
                query_error = str(error)
                papers = []
            query_error = query_error or getattr(self, "last_query_error", None)
            if query_error:
                report["failed_queries"] += 1
                report["errors"].append(f"{keyword}: {query_error}")
            elif papers:
                report["successful_queries"] += 1
            else:
                report["empty_queries"] += 1
            all_papers.extend(papers)
            if index < len(selected_keywords) - 1:
                time.sleep(self.SEARCH_PAUSE_SECONDS)

        unique_papers = self._dedupe_papers(all_papers)

        result = unique_papers[:limit]
        report["raw_papers"] = len(all_papers)
        report["returned_papers"] = len(result)
        report["duplicate_papers"] = max(0, len(all_papers) - len(unique_papers))
        self.last_run_report = report
        return result

    def _dedupe_papers(self, papers: List[DiscoveredPaper]) -> List[DiscoveredPaper]:
        """按 DOI 去重；没有 DOI 的记录保留，避免误删新论文。"""
        seen_dois = set()
        unique_papers = []
        for paper in papers:
            if paper.doi and paper.doi not in seen_dois:
                seen_dois.add(paper.doi)
                unique_papers.append(paper)
            elif not paper.doi:
                unique_papers.append(paper)
        return unique_papers

    def _normalize_journal_name(self, name: str) -> str:
        """Normalize journal names for exact venue matching."""
        normalized = name.lower().replace("&", " and ")
        normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
        return " ".join(normalized.split())

    def _allocate_limits(self, total_limit: int, query_count: int) -> List[int]:
        """把总数量分配到有限关键词请求中，避免大量 limit=1 请求。"""
        base = total_limit // query_count
        remainder = total_limit % query_count
        return [
            max(1, base + (1 if index < remainder else 0))
            for index in range(query_count)
        ]

    def _empty_run_report(self) -> Dict[str, Any]:
        """构造最近一次发现运行的轻量报告。"""
        return {
            "requested_queries": 0,
            "successful_queries": 0,
            "empty_queries": 0,
            "failed_queries": 0,
            "raw_papers": 0,
            "duplicate_papers": 0,
            "returned_papers": 0,
            "query_limits": {},
            "errors": [],
        }

    def get_paper_by_doi(self, doi: str) -> Optional[DiscoveredPaper]:
        """
        通过DOI获取论文详情

        Args:
            doi: DOI标识符

        Returns:
            DiscoveredPaper 或 None
        """
        params = {
            "fields": "title,abstract,authors,year,journal,venue,externalIds,url,citationCount"
        }

        try:
            item = self._get_json(f"/paper/DOI:{doi}", params)

            journal = ""
            if item.get("journal"):
                journal = item["journal"].get("name", "")
            elif item.get("venue"):
                journal = item.get("venue", "")

            doi = ""
            external_ids = item.get("externalIds", {})
            if external_ids:
                doi = external_ids.get("DOI", "")

            authors = ""
            authors_list = item.get("authors", [])
            if authors_list:
                authors = ", ".join([a.get("name", "") for a in authors_list[:5]])

            link = item.get("url", "")
            if doi and not link:
                link = f"https://doi.org/{doi}"

            return DiscoveredPaper(
                title=item.get("title", ""),
                abstract=item.get("abstract", "") or "",
                authors=authors,
                journal=journal,
                published_date=str(item.get("year", "")),
                link=link,
                doi=doi,
                citation_count=item.get("citationCount", 0)
            )

        except requests.RequestException as e:
            print(f"获取论文详情时出错: {e}")
            return None

    def get_paper_citations(self, paper_id: str, limit: int = 20) -> List[DiscoveredPaper]:
        """
        获取论文的引用列表

        Args:
            paper_id: 论文ID (DOI或Semantic Scholar ID)
            limit: 返回数量限制

        Returns:
            List[DiscoveredPaper]: 引用论文列表
        """
        params = {
            "limit": limit,
            "fields": "title,abstract,authors,year,journal,venue,externalIds,url"
        }

        try:
            # 自动添加前缀
            if not paper_id.startswith("DOI:"):
                paper_id = f"DOI:{paper_id}"

            data = self._get_json(f"/paper/{paper_id}/citations", params)

            papers = []
            for item in data.get("data", []):
                citing_paper = item.get("citingPaper", {})
                if not citing_paper:
                    continue

                journal = citing_paper.get("journal", {})
                if isinstance(journal, dict):
                    journal = journal.get("name", "")

                papers.append(DiscoveredPaper(
                    title=citing_paper.get("title", ""),
                    abstract=citing_paper.get("abstract", "") or "",
                    authors="",
                    journal=journal,
                    published_date=str(citing_paper.get("year", "")),
                    link=citing_paper.get("url", ""),
                    doi=""
                ))

            return papers

        except requests.RequestException as e:
            print(f"获取引用列表时出错: {e}")
            return []

    def _get_json(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行带有限流重试的 JSON 请求"""
        last_error: Optional[requests.RequestException] = None

        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.session.get(
                    f"{self.SEMANTIC_SCHOLAR_API}{path}",
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
        raise requests.RequestException("未知的请求失败")

    def _is_retryable_http_error(self, error: requests.HTTPError) -> bool:
        """判断错误是否适合短暂退避后重试。"""
        response = getattr(error, "response", None)
        status_code = getattr(response, "status_code", None)
        if status_code in {429, 500, 502, 503, 504}:
            return True
        error_text = str(error)
        return any(code in error_text for code in ("429", "500", "502", "503", "504"))

    def _retry_delay_seconds(self, error: requests.HTTPError, attempt: int) -> float:
        """优先使用 Retry-After；否则使用指数退避。"""
        response = getattr(error, "response", None)
        headers = getattr(response, "headers", {}) if response is not None else {}
        retry_after = headers.get("Retry-After") if headers else None
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                pass
        return self.RETRY_BACKOFF_SECONDS * (2 ** attempt)


class OpenAlexDiscovery:
    """OpenAlex source/ISSN based journal discovery."""

    OPENALEX_API = "https://api.openalex.org"
    MAX_RETRIES = 3
    RETRY_BACKOFF_SECONDS = 1.0
    SEARCH_PAUSE_SECONDS = 0.2

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "PaperHOT/0.1",
        })
        self.last_run_report: Dict[str, Any] = self._empty_run_report()
        self.last_query_error: Optional[str] = None

    def search_journal_updates(
        self,
        journals: Optional[List[Dict[str, Any]]] = None,
        from_year: int = 2026,
        limit_per_journal: int = 10,
    ) -> List[DiscoveredPaper]:
        """Fetch journal updates by OpenAlex source id or ISSN."""
        if journals is None:
            journals = get_config().get_tracked_journals()
        if not journals or limit_per_journal <= 0:
            self.last_run_report = self._empty_run_report()
            return []

        all_papers = []
        report = self._empty_run_report()
        report["requested_queries"] = len(journals)

        for index, journal_config in enumerate(journals):
            journal_name = journal_config.get("name", "")
            report["query_limits"][journal_name] = limit_per_journal
            self.last_query_error = None
            try:
                papers = self.search_by_journal_config(
                    journal_config,
                    from_year=from_year,
                    limit=limit_per_journal,
                )
                query_error = None
            except requests.RequestException as error:
                papers = []
                query_error = str(error)
            except ValueError as error:
                papers = []
                query_error = str(error)

            if query_error:
                report["failed_queries"] += 1
                report["errors"].append(f"{journal_name}: {query_error}")
            elif papers:
                report["successful_queries"] += 1
            else:
                report["empty_queries"] += 1

            all_papers.extend(papers)
            if index < len(journals) - 1:
                time.sleep(self.SEARCH_PAUSE_SECONDS)

        unique_papers = self._dedupe_papers(all_papers)
        report["raw_papers"] = len(all_papers)
        report["returned_papers"] = len(unique_papers)
        report["duplicate_papers"] = max(0, len(all_papers) - len(unique_papers))
        self.last_run_report = report
        return unique_papers

    def search_by_journal_config(
        self,
        journal_config: Dict[str, Any],
        from_year: int = 2026,
        limit: int = 10,
    ) -> List[DiscoveredPaper]:
        """Fetch works for one configured journal."""
        journal_name = journal_config.get("name", "")
        source_filter = self._source_filter(journal_config)
        if not source_filter:
            raise ValueError("missing openalex_source_id or ISSN")

        track_from_year = int(journal_config.get("track_from_year", from_year) or from_year)
        filters = [
            source_filter,
            f"from_publication_date:{track_from_year}-01-01",
            "type:article",
        ]
        params = {
            "filter": ",".join(filters),
            "sort": "publication_date:desc",
            "per-page": min(max(1, limit), 100),
            "select": ",".join([
                "id",
                "title",
                "doi",
                "publication_date",
                "authorships",
                "primary_location",
                "abstract_inverted_index",
                "cited_by_count",
            ]),
        }
        data = self._get_json("/works", params)
        return [
            self._work_to_paper(item, fallback_journal=journal_name)
            for item in data.get("results", [])
        ]

    def _source_filter(self, journal_config: Dict[str, Any]) -> str:
        source_id = str(journal_config.get("openalex_source_id", "")).strip()
        if source_id:
            source_id = source_id.rsplit("/", 1)[-1]
            return f"primary_location.source.id:{source_id}"

        issn = str(journal_config.get("issn_l", "")).strip()
        if not issn:
            issns = journal_config.get("issn") or []
            if issns:
                issn = str(issns[0]).strip()
        if issn:
            return f"primary_location.source.issn:{issn}"
        return ""

    def _work_to_paper(self, item: Dict[str, Any], fallback_journal: str = "") -> DiscoveredPaper:
        location = item.get("primary_location") or {}
        source = location.get("source") or {}
        doi = self._normalize_doi(item.get("doi", ""))
        link = location.get("landing_page_url") or item.get("id", "")
        if doi and not link:
            link = f"https://doi.org/{doi}"
        return DiscoveredPaper(
            title=item.get("title", "") or "",
            abstract=self._abstract_from_inverted_index(item.get("abstract_inverted_index")),
            authors=self._authors_from_authorships(item.get("authorships", [])),
            journal=source.get("display_name") or fallback_journal,
            published_date=item.get("publication_date", "") or "",
            link=link,
            doi=doi,
            citation_count=item.get("cited_by_count", 0) or 0,
            openalex_id=(item.get("id", "") or "").rsplit("/", 1)[-1],
        )

    def _abstract_from_inverted_index(self, inverted_index: Optional[Dict[str, List[int]]]) -> str:
        if not inverted_index:
            return ""
        positioned_words = []
        for word, positions in inverted_index.items():
            for position in positions:
                positioned_words.append((position, word))
        return " ".join(word for _, word in sorted(positioned_words))

    def _authors_from_authorships(self, authorships: List[Dict[str, Any]]) -> str:
        names = [
            (authorship.get("author") or {}).get("display_name", "")
            for authorship in authorships[:5]
        ]
        names = [name for name in names if name]
        authors = ", ".join(names)
        if len(authorships) > 5:
            authors += " et al."
        return authors

    def _normalize_doi(self, doi: str) -> str:
        doi = (doi or "").strip()
        return re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)

    def _dedupe_papers(self, papers: List[DiscoveredPaper]) -> List[DiscoveredPaper]:
        seen_dois = set()
        unique_papers = []
        for paper in papers:
            if paper.doi and paper.doi not in seen_dois:
                seen_dois.add(paper.doi)
                unique_papers.append(paper)
            elif not paper.doi:
                unique_papers.append(paper)
        return unique_papers

    def _empty_run_report(self) -> Dict[str, Any]:
        return {
            "requested_queries": 0,
            "successful_queries": 0,
            "empty_queries": 0,
            "failed_queries": 0,
            "raw_papers": 0,
            "duplicate_papers": 0,
            "returned_papers": 0,
            "query_limits": {},
            "errors": [],
            "source": "openalex",
        }

    def _get_json(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        last_error: Optional[requests.RequestException] = None
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.session.get(
                    f"{self.OPENALEX_API}{path}",
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
        raise requests.RequestException("unknown OpenAlex request failure")

    def _is_retryable_http_error(self, error: requests.HTTPError) -> bool:
        response = getattr(error, "response", None)
        status_code = getattr(response, "status_code", None)
        if status_code in {429, 500, 502, 503, 504}:
            return True
        return any(code in str(error) for code in ("429", "500", "502", "503", "504"))

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
