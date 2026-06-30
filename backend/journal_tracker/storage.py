"""本地存储模块 - SQLite"""

import sqlite3
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from contextlib import contextmanager


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
    score: Optional[int] = None
    status: str = "To Read"  # To Read/Reading/Read
    is_public: bool = False
    source_type: str = ""  # openalex/semantic_scholar/legacy/manual
    source_run_id: str = ""
    tracked_journal: str = ""
    openalex_id: str = ""
    screening_status: str = ""  # pending/screened/error/quarantined
    discovered_at: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PaperStorage:
    """论文存储管理（SQLite）"""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
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
                    score INTEGER,
                    status TEXT DEFAULT 'To Read',
                    is_public INTEGER DEFAULT 0,
                    source_type TEXT,
                    source_run_id TEXT,
                    tracked_journal TEXT,
                    openalex_id TEXT,
                    screening_status TEXT,
                    discovered_at TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            self._ensure_columns(cursor)
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
                    link, doi, relevance, reason, tags, summary, score, status,
                    is_public, source_type, source_run_id, tracked_journal, openalex_id,
                    screening_status, discovered_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                paper.title, paper.authors, paper.abstract, paper.journal,
                paper.published_date, paper.link, paper.doi, paper.relevance,
                paper.reason, paper.tags, paper.summary, paper.score, paper.status,
                int(paper.is_public), paper.source_type, paper.source_run_id,
                paper.tracked_journal, paper.openalex_id, paper.screening_status,
                paper.discovered_at, paper.created_at, paper.updated_at
            ))
            conn.commit()
            return cursor.lastrowid or 0

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
    ) -> bool:
        """更新论文 AI 筛选结果"""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE papers
                SET relevance = ?, reason = ?, tags = ?, summary = ?,
                    screening_status = 'screened', updated_at = ?
                WHERE id = ?
            """, (relevance, reason, tags, summary, now, paper_id))
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

    def _normalize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """标准化 SQLite 返回数据"""
        row["is_public"] = bool(row.get("is_public", 0))
        return row

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
                "relevance", "reason", "tags", "summary", "link", "status",
                "source_type", "source_run_id", "tracked_journal", "openalex_id",
                "screening_status", "discovered_at"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for paper in papers:
                row = paper.to_dict()
                # 只写我们需要的字段
                writer.writerow({k: row[k] for k in fieldnames})
