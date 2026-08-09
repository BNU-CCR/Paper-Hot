"""本地存储模块 - SQLite"""

import hashlib
import json
import sqlite3
import re
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from contextlib import contextmanager

from .text import clean_paper_title, clean_translated_abstract, clean_translated_title


@dataclass
class Paper:
    """论文数据结构"""
    id: Optional[int] = None
    title: str = ""
    authors: str = ""
    abstract: str = ""
    journal: str = ""
    published_date: str = ""
    link: str = ""
    doi: str = ""
    relevance: str = ""  # High/Medium/Low
    reason: str = ""
    tags: str = ""  # JSON string of tags list
    summary: str = ""
    method: str = ""  # 研究方法标签（质性分析/量化分析/理论分析/综述/计算传播学/空）
    score: Optional[int] = None
    status: str = "To Read"  # To Read/Reading/Read
    is_public: bool = False
    source_type: str = ""  # openalex/semantic_scholar/legacy/manual
    source_run_id: str = ""
    tracked_journal: str = ""
    openalex_id: str = ""
    screening_status: str = ""  # pending/screened/error/quarantined
    volume: str = ""
    issue: str = ""
    bibliography_checked_at: str = ""
    discovered_at: str = ""
    created_at: str = ""
    updated_at: str = ""
    is_retracted: bool = False
    title_zh: str = ""
    abstract_zh: str = ""
    translation_model: str = ""
    translation_source_hash: str = ""
    translation_status: str = ""
    translation_error: str = ""
    translated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PaperFeatures:
    """Per-paper embeddings and OpenAlex enrichment."""
    paper_id: int
    text_hash: str = ""
    embedding_model: str = ""
    embedding_dim: int = 0
    embedding_bytes: Optional[bytes] = None
    openalex_topics_json: str = "[]"
    openalex_keywords_json: str = "[]"
    referenced_works_json: str = "[]"
    cited_by_count: int = 0
    is_retracted: bool = False
    updated_at: str = ""


class PaperStorage:
    """论文存储管理（SQLite）"""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    @contextmanager
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_database(self):
        """初始化数据库表"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    authors TEXT,
                    abstract TEXT,
                    journal TEXT,
                    published_date TEXT,
                    link TEXT UNIQUE,
                    doi TEXT,
                    relevance TEXT,
                    reason TEXT,
                    tags TEXT,
                    summary TEXT,
                    method TEXT,
                    score INTEGER,
                    status TEXT DEFAULT 'To Read',
                    is_public INTEGER DEFAULT 0,
                    source_type TEXT,
                    source_run_id TEXT,
                    tracked_journal TEXT,
                    openalex_id TEXT,
                    screening_status TEXT,
                    volume TEXT,
                    issue TEXT,
                    bibliography_checked_at TEXT,
                    discovered_at TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            self._ensure_columns(cursor)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paper_features (
                    paper_id INTEGER PRIMARY KEY,
                    text_hash TEXT NOT NULL DEFAULT '',
                    embedding_model TEXT NOT NULL DEFAULT '',
                    embedding_dim INTEGER NOT NULL DEFAULT 0,
                    embedding BLOB,
                    openalex_topics_json TEXT NOT NULL DEFAULT '[]',
                    openalex_keywords_json TEXT NOT NULL DEFAULT '[]',
                    referenced_works_json TEXT NOT NULL DEFAULT '[]',
                    cited_by_count INTEGER NOT NULL DEFAULT 0,
                    is_retracted INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY (paper_id) REFERENCES papers(id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paper_author_enrichment (
                    paper_id INTEGER NOT NULL,
                    author_order INTEGER NOT NULL,
                    display_name TEXT NOT NULL DEFAULT '',
                    normalized_name TEXT NOT NULL DEFAULT '',
                    orcid TEXT NOT NULL DEFAULT '',
                    semantic_scholar_author_id TEXT NOT NULL DEFAULT '',
                    aliases_json TEXT NOT NULL DEFAULT '[]',
                    affiliations_json TEXT NOT NULL DEFAULT '[]',
                    match_method TEXT NOT NULL DEFAULT '',
                    match_confidence REAL NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (paper_id, author_order),
                    FOREIGN KEY (paper_id) REFERENCES papers(id)
                )
            """)
            # 创建索引加速查询
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_papers_link ON papers(link)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_papers_relevance ON papers(relevance)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_papers_is_public ON papers(is_public)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_papers_screening_status ON papers(screening_status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_papers_source_type ON papers(source_type)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_author_enrichment_s2_id
                ON paper_author_enrichment(semantic_scholar_author_id)
            """)
            conn.commit()

    def _ensure_columns(self, cursor: sqlite3.Cursor):
        """为旧数据库补齐缺失字段"""
        cursor.execute("PRAGMA table_info(papers)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        if "score" not in existing_columns:
            cursor.execute("ALTER TABLE papers ADD COLUMN score INTEGER")
        if "is_public" not in existing_columns:
            cursor.execute("ALTER TABLE papers ADD COLUMN is_public INTEGER DEFAULT 0")
        new_columns = {
            "source_type": "TEXT",
            "source_run_id": "TEXT",
            "tracked_journal": "TEXT",
            "openalex_id": "TEXT",
            "screening_status": "TEXT",
            "discovered_at": "TEXT",
            "volume": "TEXT",
            "issue": "TEXT",
            "bibliography_checked_at": "TEXT",
            "method": "TEXT",
            "title_zh": "TEXT",
            "abstract_zh": "TEXT",
            "translation_model": "TEXT",
            "translation_source_hash": "TEXT",
            "translation_status": "TEXT",
            "translation_error": "TEXT",
            "translated_at": "TEXT",
        }
        for column, column_type in new_columns.items():
            if column not in existing_columns:
                cursor.execute(f"ALTER TABLE papers ADD COLUMN {column} {column_type}")
        cursor.execute("""
            UPDATE papers
            SET screening_status = CASE
                WHEN relevance IN ('High', 'Medium', 'Low') THEN 'screened'
                WHEN relevance = 'Unscreened' THEN 'pending'
                ELSE 'pending'
            END
            WHERE screening_status IS NULL OR screening_status = ''
        """)
        cursor.execute("""
            UPDATE papers
            SET source_type = 'legacy'
            WHERE source_type IS NULL OR source_type = ''
        """)
        cursor.execute("""
            UPDATE papers
            SET discovered_at = COALESCE(NULLIF(created_at, ''), datetime('now'))
            WHERE discovered_at IS NULL OR discovered_at = ''
        """)

    def add_paper(self, paper: Paper) -> int:
        """添加论文，返回ID"""
        now = datetime.now().isoformat()
        paper.title = clean_paper_title(paper.title)
        if not paper.discovered_at:
            paper.discovered_at = now
        if not paper.screening_status:
            paper.screening_status = "screened" if paper.relevance in {"High", "Medium", "Low"} else "pending"
        if not paper.source_type:
            paper.source_type = "legacy"
        paper.created_at = now
        paper.updated_at = now

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO papers (
                    title, authors, abstract, journal, published_date,
                    link, doi, relevance, reason, tags, summary, method, score, status,
                    is_public, source_type, source_run_id, tracked_journal, openalex_id,
                    screening_status, volume, issue, bibliography_checked_at, discovered_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                paper.title, paper.authors, paper.abstract, paper.journal,
                paper.published_date, paper.link, paper.doi, paper.relevance,
                paper.reason, paper.tags, paper.summary, paper.method, paper.score, paper.status,
                int(paper.is_public), paper.source_type, paper.source_run_id,
                paper.tracked_journal, paper.openalex_id, paper.screening_status,
                paper.volume, paper.issue, paper.bibliography_checked_at,
                paper.discovered_at, paper.created_at, paper.updated_at
            ))
            conn.commit()
            return cursor.lastrowid or 0

    def sanitize_paper_titles(self) -> int:
        """Remove publisher HTML markup from titles already stored in the database."""
        now = datetime.now().isoformat()
        changed = 0
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title FROM papers")
            for row in cursor.fetchall():
                cleaned = clean_paper_title(row["title"])
                if cleaned == row["title"]:
                    continue
                cursor.execute(
                    "UPDATE papers SET title = ?, updated_at = ? WHERE id = ?",
                    (cleaned, now, row["id"]),
                )
                changed += 1
            conn.commit()
        return changed

    def sanitize_translated_titles(self) -> int:
        """Remove model response wrappers from existing Chinese title translations."""
        now = datetime.now().isoformat()
        changed = 0
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title_zh FROM papers WHERE title_zh IS NOT NULL AND title_zh != ''")
            for row in cursor.fetchall():
                cleaned = clean_translated_title(row["title_zh"])
                if not cleaned or cleaned == row["title_zh"]:
                    continue
                cursor.execute(
                    "UPDATE papers SET title_zh = ?, updated_at = ? WHERE id = ?",
                    (cleaned, now, row["id"]),
                )
                changed += 1
            conn.commit()
        return changed

    def sanitize_translated_abstracts(self) -> int:
        """Remove model response labels from existing Chinese abstract translations."""
        now = datetime.now().isoformat()
        changed = 0
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, abstract_zh FROM papers WHERE abstract_zh IS NOT NULL AND abstract_zh != ''")
            for row in cursor.fetchall():
                cleaned = clean_translated_abstract(row["abstract_zh"])
                if not cleaned or cleaned == row["abstract_zh"]:
                    continue
                cursor.execute(
                    "UPDATE papers SET abstract_zh = ?, updated_at = ? WHERE id = ?",
                    (cleaned, now, row["id"]),
                )
                changed += 1
            conn.commit()
        return changed

    @staticmethod
    def translation_source_hash(title: str, abstract: str) -> str:
        content = f"{title.strip()}\n{abstract.strip()}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def get_papers_needing_translation(self, limit: int = 100) -> List[Paper]:
        """Return public-library papers with missing or stale Chinese translations."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM papers
                WHERE source_type = 'openalex'
                  AND screening_status != 'quarantined'
                ORDER BY published_date DESC, id DESC
            """)
            pending = []
            for row in cursor.fetchall():
                paper = Paper(**self._normalize_row(dict(row)))
                source_hash = self.translation_source_hash(paper.title, paper.abstract)
                complete = bool(paper.title_zh) and (not paper.abstract or bool(paper.abstract_zh))
                if complete and paper.translation_source_hash == source_hash:
                    continue
                pending.append(paper)
                if len(pending) >= limit:
                    break
            return pending

    def update_paper_translation(
        self,
        paper_id: int,
        title_zh: str,
        abstract_zh: str,
        model: str,
        source_hash: str,
    ) -> bool:
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE papers
                SET title_zh = ?, abstract_zh = ?, translation_model = ?,
                    translation_source_hash = ?, translation_status = 'translated',
                    translation_error = '', translated_at = ?, updated_at = ?
                WHERE id = ?
            """, (title_zh, abstract_zh, model, source_hash, now, now, paper_id))
            conn.commit()
            return cursor.rowcount > 0

    def mark_translation_error(self, paper_id: int, message: str) -> bool:
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE papers
                SET translation_status = 'error', translation_error = ?, updated_at = ?
                WHERE id = ?
            """, (message[:1000], now, paper_id))
            conn.commit()
            return cursor.rowcount > 0

    def paper_exists(self, link: str = "", doi: str = "") -> bool:
        """检查论文是否已存在"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            clauses = []
            params = []
            if link:
                clauses.append("link = ?")
                params.append(link)
            if doi:
                clauses.append("doi = ?")
                params.append(doi)
            if not clauses:
                return False
            cursor.execute(f"SELECT 1 FROM papers WHERE {' OR '.join(clauses)}", params)
            return cursor.fetchone() is not None

    def get_paper_by_link(self, link: str) -> Optional[Paper]:
        """通过链接获取论文"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM papers WHERE link = ?", (link,))
            row = cursor.fetchone()
            if row:
                return Paper(**self._normalize_row(dict(row)))
            return None

    def get_paper_by_id(self, paper_id: int) -> Optional[Paper]:
        """通过 ID 获取论文"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM papers WHERE id = ?", (paper_id,))
            row = cursor.fetchone()
            if row:
                return Paper(**self._normalize_row(dict(row)))
            return None

    def get_papers(
        self,
        relevance: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Paper]:
        """获取论文列表"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM papers WHERE 1=1"
            params = []

            if relevance:
                query += " AND relevance = ?"
                params.append(relevance)
            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [Paper(**self._normalize_row(dict(row))) for row in rows]

    def update_paper_status(self, paper_id: int, status: str):
        """更新论文状态"""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE papers SET status = ?, updated_at = ?
                WHERE id = ?
            """, (status, now, paper_id))
            conn.commit()

    def update_filter_result(
        self,
        paper_id: int,
        relevance: str,
        reason: str,
        tags: str,
        summary: str,
        method: str = "",
    ) -> bool:
        """更新论文 AI 筛选结果"""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE papers
                SET relevance = ?, reason = ?, tags = ?, summary = ?, method = ?,
                    screening_status = 'screened', updated_at = ?
                WHERE id = ?
            """, (relevance, reason, tags, summary, method, now, paper_id))
            conn.commit()
            return cursor.rowcount > 0

    def mark_filter_error(self, paper_id: int, error_message: str) -> bool:
        """Mark one paper as failed during AI screening without blocking the batch."""
        now = datetime.now().isoformat()
        reason = f"筛选出错: {error_message[:500]}"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE papers
                SET relevance = 'Low',
                    reason = ?,
                    screening_status = 'error',
                    updated_at = ?
                WHERE id = ?
            """, (reason, now, paper_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_pending_screening_papers(
        self,
        limit: int = 100,
        source_type: Optional[str] = "openalex",
    ) -> List[Paper]:
        """获取待 AI 筛选的论文队列。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM papers WHERE screening_status = 'pending'"
            params = []
            if source_type:
                query += " AND source_type = ?"
                params.append(source_type)
            query += " ORDER BY discovered_at DESC, created_at DESC LIMIT ?"
            params.append(limit)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [Paper(**self._normalize_row(dict(row))) for row in rows]

    def repair_unscreened_queue(self, tracked_journals: List[Dict[str, Any]]) -> Dict[str, int]:
        """把历史 Unscreened 数据分流为红榜 pending 或非红榜 quarantined。"""
        tracked_by_normalized = {}
        for journal in tracked_journals:
            names = [
                journal.get("name", ""),
                journal.get("abbr", ""),
                *(journal.get("aliases", []) or []),
                *(journal.get("openalex_aliases", []) or []),
            ]
            for name in names:
                normalized = self._normalize_name(name)
                if normalized:
                    tracked_by_normalized[normalized] = journal

        pending = 0
        quarantined = 0
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, journal FROM papers
                WHERE relevance = 'Unscreened'
                   OR screening_status = 'pending'
                   OR screening_status IS NULL
                   OR screening_status = ''
            """)
            rows = cursor.fetchall()
            for row in rows:
                journal = tracked_by_normalized.get(self._normalize_name(row["journal"]))
                if journal:
                    cursor.execute("""
                        UPDATE papers
                        SET screening_status = 'pending',
                            relevance = CASE
                                WHEN relevance = 'Unscreened' THEN ''
                                ELSE relevance
                            END,
                            source_type = 'openalex',
                            tracked_journal = ?,
                            updated_at = ?
                        WHERE id = ?
                    """, (journal.get("name", ""), now, row["id"]))
                    pending += 1
                else:
                    cursor.execute("""
                        UPDATE papers
                        SET screening_status = 'quarantined',
                            relevance = CASE
                                WHEN relevance = 'Unscreened' THEN ''
                                ELSE relevance
                            END,
                            source_type = CASE
                                WHEN source_type IS NULL OR source_type = '' THEN 'legacy'
                                ELSE source_type
                            END,
                            updated_at = ?
                        WHERE id = ?
                    """, (now, row["id"]))
                    quarantined += 1
            conn.commit()
        return {"pending": pending, "quarantined": quarantined}

    def get_filter_error_papers(self, limit: int = 20) -> List[Paper]:
        """获取筛选失败后需要重筛的论文"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM papers
                WHERE screening_status = 'error'
                   OR reason LIKE '筛选出错%'
                ORDER BY updated_at DESC, created_at DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [Paper(**self._normalize_row(dict(row))) for row in rows]

    def set_paper_publication(self, paper_id: int, is_public: bool):
        """设置论文公开发布状态"""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE papers SET is_public = ?, updated_at = ?
                WHERE id = ?
            """, (int(is_public), now, paper_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_public_papers(self, limit: int = 1000) -> List[Paper]:
        """获取已发布的公开论文"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM papers
                WHERE is_public = 1
                ORDER BY published_date DESC, created_at DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [Paper(**self._normalize_row(dict(row))) for row in rows]

    def get_all_journal_update_papers(self, limit: int = 10000) -> List[Paper]:
        """Get all red-list journal update papers, excluding quarantined legacy rows."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM papers
                WHERE source_type = 'openalex'
                  AND screening_status != 'quarantined'
                ORDER BY published_date DESC, discovered_at DESC, created_at DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [Paper(**self._normalize_row(dict(row))) for row in rows]

    def get_papers_missing_issue(self, limit: int = 10000) -> List[Paper]:
        """Return OpenAlex-backed papers that still need volume/issue enrichment."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM papers
                WHERE source_type = 'openalex'
                  AND screening_status != 'quarantined'
                  AND (issue IS NULL OR issue = '' OR volume IS NULL OR volume = '')
                  AND (bibliography_checked_at IS NULL OR bibliography_checked_at = '')
                  AND (openalex_id IS NOT NULL AND openalex_id != '' OR doi IS NOT NULL AND doi != '')
                ORDER BY published_date DESC, id DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [Paper(**self._normalize_row(dict(row))) for row in rows]

    def update_paper_method(self, paper_id: int, method: str) -> bool:
        """Persist an AI-generated single research-method label (backfill only)."""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE papers SET method = ?, updated_at = ? WHERE id = ?",
                (method, now, paper_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_papers_missing_method(self, limit: int = 200) -> List[Paper]:
        """Return screened papers that still lack a research-method label."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM papers
                WHERE screening_status = 'screened'
                  AND (method IS NULL OR method = '')
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [Paper(**self._normalize_row(dict(row))) for row in rows]

    def get_papers_missing_author_enrichment(
        self, limit: int = 50, force: bool = False
    ) -> List[Paper]:
        """Return DOI-bearing papers not yet covered by author enrichment."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            condition = "" if force else "AND NOT EXISTS (SELECT 1 FROM paper_author_enrichment pae WHERE pae.paper_id = p.id)"
            cursor.execute(f"""
                SELECT p.* FROM papers p
                WHERE p.doi IS NOT NULL AND p.doi != ''
                  AND p.screening_status != 'quarantined'
                  {condition}
                ORDER BY p.published_date DESC, p.id DESC
                LIMIT ?
            """, (limit,))
            return [Paper(**self._normalize_row(dict(row))) for row in cursor.fetchall()]

    def replace_paper_author_enrichment(
        self, paper_id: int, authors: List[Dict[str, Any]]
    ) -> None:
        """Atomically replace paper-scoped author identity and affiliation rows."""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM paper_author_enrichment WHERE paper_id = ?", (paper_id,))
            for author in authors:
                cursor.execute("""
                    INSERT INTO paper_author_enrichment (
                        paper_id, author_order, display_name, normalized_name, orcid,
                        semantic_scholar_author_id, aliases_json, affiliations_json,
                        match_method, match_confidence, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    paper_id,
                    int(author.get("author_order", 0)),
                    str(author.get("display_name", "")),
                    str(author.get("normalized_name", "")),
                    str(author.get("orcid", "")),
                    str(author.get("semantic_scholar_author_id", "")),
                    json.dumps(author.get("aliases", []), ensure_ascii=False),
                    json.dumps(author.get("affiliations", []), ensure_ascii=False),
                    str(author.get("match_method", "")),
                    float(author.get("match_confidence", 0)),
                    now,
                ))
            conn.commit()

    def update_paper_bibliography(self, paper_id: int, volume: str, issue: str, openalex_id: str = "") -> bool:
        """Persist volume and issue metadata returned by OpenAlex."""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE papers
                SET volume = ?, issue = ?, openalex_id = COALESCE(NULLIF(?, ''), openalex_id),
                    bibliography_checked_at = ?, updated_at = ?
                WHERE id = ?
            """, (volume, issue, openalex_id, now, now, paper_id))
            conn.commit()
            return cursor.rowcount > 0

    def _normalize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """标准化 SQLite 返回数据"""
        row["is_public"] = bool(row.get("is_public", 0))
        row["is_retracted"] = bool(row.get("is_retracted", 0))
        return row

    # ── paper_features ─────────────────────────────────────────────

    def upsert_paper_features(self, features: PaperFeatures) -> bool:
        """Insert or update embedding and enrichment data for one paper."""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO paper_features (
                    paper_id, text_hash, embedding_model, embedding_dim, embedding,
                    openalex_topics_json, openalex_keywords_json, referenced_works_json,
                    cited_by_count, is_retracted, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(paper_id) DO UPDATE SET
                    text_hash = excluded.text_hash,
                    embedding_model = excluded.embedding_model,
                    embedding_dim = excluded.embedding_dim,
                    embedding = excluded.embedding,
                    openalex_topics_json = excluded.openalex_topics_json,
                    openalex_keywords_json = excluded.openalex_keywords_json,
                    referenced_works_json = excluded.referenced_works_json,
                    cited_by_count = excluded.cited_by_count,
                    is_retracted = excluded.is_retracted,
                    updated_at = excluded.updated_at
            """, (
                features.paper_id, features.text_hash, features.embedding_model,
                features.embedding_dim, features.embedding_bytes,
                features.openalex_topics_json, features.openalex_keywords_json,
                features.referenced_works_json, features.cited_by_count,
                int(features.is_retracted), now,
            ))
            conn.commit()
            return cursor.rowcount > 0

    def get_paper_features(self, paper_id: int) -> Optional[PaperFeatures]:
        """Get enrichment data for a single paper."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM paper_features WHERE paper_id = ?", (paper_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return PaperFeatures(
                paper_id=row["paper_id"],
                text_hash=row["text_hash"] or "",
                embedding_model=row["embedding_model"] or "",
                embedding_dim=row["embedding_dim"] or 0,
                embedding_bytes=row["embedding"],
                openalex_topics_json=row["openalex_topics_json"] or "[]",
                openalex_keywords_json=row["openalex_keywords_json"] or "[]",
                referenced_works_json=row["referenced_works_json"] or "[]",
                cited_by_count=row["cited_by_count"] or 0,
                is_retracted=bool(row["is_retracted"]),
                updated_at=row["updated_at"] or "",
            )

    def get_analysis_candidates(
        self,
        min_date: str = "",
        relevance_filter: Tuple[str, ...] = ("High", "Medium"),
    ) -> List[Dict[str, Any]]:
        """Return papers suitable for hotspot analysis with their features."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT
                    p.id, p.title, p.abstract, p.summary, p.published_date,
                    p.journal, p.relevance, p.tags,
                    pf.openalex_topics_json, pf.openalex_keywords_json,
                    pf.referenced_works_json, pf.cited_by_count,
                    pf.text_hash, pf.embedding_model, pf.embedding_dim,
                    pf.embedding, pf.is_retracted
                FROM papers p
                LEFT JOIN paper_features pf ON p.id = pf.paper_id
                WHERE p.screening_status = 'screened'
                  AND p.relevance IN ({seq})
                  AND (pf.is_retracted IS NULL OR pf.is_retracted = 0)
                  {date_clause}
                ORDER BY p.published_date DESC
            """.format(
                seq=",".join("?" for _ in relevance_filter),
                date_clause="AND p.published_date >= ?" if min_date else "",
            )
            params: List[Any] = list(relevance_filter)
            if min_date:
                params.append(min_date)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_papers_missing_features(self, limit: int = 1000) -> List[int]:
        """Return paper IDs missing from paper_features."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.id FROM papers p
                LEFT JOIN paper_features pf ON p.id = pf.paper_id
                WHERE p.source_type = 'openalex'
                  AND p.screening_status != 'quarantined'
                  AND pf.paper_id IS NULL
                ORDER BY p.id DESC
                LIMIT ?
            """, (limit,))
            return [row[0] for row in cursor.fetchall()]

    def compute_text_hash(
        self, title: str, abstract: str, embedding_model: str
    ) -> str:
        """Deterministic hash for the text that feeds an embedding."""
        content = f"{title}|{abstract}|{embedding_model}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _normalize_name(self, name: str) -> str:
        normalized = (name or "").lower().replace("&", " and ")
        normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
        return " ".join(normalized.split())

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 总数
            cursor.execute("SELECT COUNT(*) as total FROM papers")
            total = cursor.fetchone()["total"]

            # 按相关性统计
            cursor.execute("""
                SELECT relevance, COUNT(*) as count
                FROM papers
                WHERE relevance IN ('High', 'Medium', 'Low')
                GROUP BY relevance
            """)
            relevance_stats = {row["relevance"]: row["count"] for row in cursor.fetchall()}

            # 按状态统计
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM papers
                GROUP BY status
            """)
            status_stats = {row["status"]: row["count"] for row in cursor.fetchall()}

            cursor.execute("""
                SELECT screening_status, COUNT(*) as count
                FROM papers
                GROUP BY screening_status
            """)
            screening_stats = {
                row["screening_status"] or "unknown": row["count"]
                for row in cursor.fetchall()
            }

            # 按研究方法标签统计（用于展示回填进度）
            cursor.execute("""
                SELECT method, COUNT(*) as count
                FROM papers
                WHERE method IS NOT NULL AND method != ''
                GROUP BY method
            """)
            method_stats = {
                row["method"]: row["count"]
                for row in cursor.fetchall()
            }

            # 本周新增
            cursor.execute("""
                SELECT COUNT(*) as count FROM papers
                WHERE created_at >= date('now', '-7 days')
            """)
            this_week = cursor.fetchone()["count"]

            return {
                "total": total,
                "relevance": relevance_stats,
                "status": status_stats,
                "screening_status": screening_stats,
                "method": method_stats,
                "this_week": this_week
            }

    def export_to_csv(self, filepath: Path, relevance: Optional[str] = None):
        """导出到CSV"""
        import csv

        papers = self.get_papers(relevance=relevance, limit=10000)

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            if not papers:
                return

            fieldnames = [
                "title", "authors", "journal", "published_date",
                "relevance", "reason", "tags", "method", "summary", "link", "status",
                "source_type", "source_run_id", "tracked_journal", "openalex_id",
                "screening_status", "discovered_at"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for paper in papers:
                row = paper.to_dict()
                # 只写我们需要的字段
                writer.writerow({k: row[k] for k in fieldnames})
