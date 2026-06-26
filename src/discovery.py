"""论文发现模块

支持两种方式：
1. asta-skill (MCP) - Claude Code中直接使用
2. Semantic Scholar API - Python脚本直接调用
"""

import requests
import time
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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "abstract": self.abstract,
            "authors": self.authors,
            "journal": self.journal,
            "published_date": self.published_date,
            "link": self.link,
            "doi": self.doi,
            "citation_count": self.citation_count
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
        query = f"venue:{journal}"
        return self.search_papers(query, year, limit)

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
        for index, keyword in enumerate(selected_keywords):
            papers = self.search_papers(keyword, limit=request_limits[index])
            all_papers.extend(papers)
            if index < len(selected_keywords) - 1:
                time.sleep(self.SEARCH_PAUSE_SECONDS)

        # 去重（按DOI）
        seen_dois = set()
        unique_papers = []
        for paper in all_papers:
            if paper.doi and paper.doi not in seen_dois:
                seen_dois.add(paper.doi)
                unique_papers.append(paper)
            elif not paper.doi:
                unique_papers.append(paper)

        return unique_papers[:limit]

    def _allocate_limits(self, total_limit: int, query_count: int) -> List[int]:
        """把总数量分配到有限关键词请求中，避免大量 limit=1 请求。"""
        base = total_limit // query_count
        remainder = total_limit % query_count
        return [
            max(1, base + (1 if index < remainder else 0))
            for index in range(query_count)
        ]

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
                if not self._is_rate_limited(error) or attempt == self.MAX_RETRIES - 1:
                    raise
                time.sleep(self.RETRY_BACKOFF_SECONDS * (2 ** attempt))
            except requests.RequestException as error:
                last_error = error
                raise

        if last_error:
            raise last_error
        raise requests.RequestException("未知的请求失败")

    def _is_rate_limited(self, error: requests.HTTPError) -> bool:
        """判断错误是否为 429 限流"""
        response = getattr(error, "response", None)
        if response is not None and getattr(response, "status_code", None) == 429:
            return True
        return "429" in str(error)
