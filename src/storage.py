"""本地存储模块 - SQLite"""

import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime


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
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PaperStorage:
    """论文存储管理（SQLite）"""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

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
            conn.commit()

    def _ensure_columns(self, cursor: sqlite3.Cursor):
        """为旧数据库补齐缺失字段"""
        cursor.execute("PRAGMA table_info(papers)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        if "score" not in existing_columns:
            cursor.execute("ALTER TABLE papers ADD COLUMN score INTEGER")
        if "is_public" not in existing_columns:
            cursor.execute("ALTER TABLE papers ADD COLUMN is_public INTEGER DEFAULT 0")

    def add_paper(self, paper: Paper) -> int:
        """添加论文，返回ID"""
        now = datetime.now().isoformat()
        paper.created_at = now
        paper.updated_at = now

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO papers (
                    title, authors, abstract, journal, published_date,
                    link, doi, relevance, reason, tags, summary, score, status,
                    is_public, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                paper.title, paper.authors, paper.abstract, paper.journal,
                paper.published_date, paper.link, paper.doi, paper.relevance,
                paper.reason, paper.tags, paper.summary, paper.score, paper.status,
                int(paper.is_public), paper.created_at, paper.updated_at
            ))
            conn.commit()
            return cursor.lastrowid or 0

    def paper_exists(self, link: str = "", doi: str = "") -> bool:
        """检查论文是否已存在"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if link:
                cursor.execute("SELECT 1 FROM papers WHERE link = ?", (link,))
            elif doi:
                cursor.execute("SELECT 1 FROM papers WHERE doi = ?", (doi,))
            else:
                return False
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

    def _normalize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """标准化 SQLite 返回数据"""
        row["is_public"] = bool(row.get("is_public", 0))
        return row

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
                "relevance", "reason", "tags", "summary", "link", "status"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for paper in papers:
                row = paper.to_dict()
                # 只写我们需要的字段
                writer.writerow({k: row[k] for k in fieldnames})
