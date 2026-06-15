"""SQLite storage — schema for apps, rating history, reviews, and credit card activity mentions."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS apps (
    app_id       TEXT PRIMARY KEY,
    name         TEXT,
    developer    TEXT,
    category     TEXT DEFAULT '',
    bundle_id    TEXT,
    current_ver  TEXT,
    price        REAL DEFAULT 0,
    app_url      TEXT,
    description  TEXT,
    bank         TEXT DEFAULT '',
    first_seen   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rating_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id       TEXT NOT NULL,
    avg_rating   REAL NOT NULL,
    rating_count INTEGER NOT NULL,
    version      TEXT DEFAULT '',
    recorded_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (app_id) REFERENCES apps(app_id)
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id    TEXT PRIMARY KEY,
    app_id       TEXT NOT NULL,
    title        TEXT,
    content      TEXT,
    rating       INTEGER DEFAULT 0,
    author       TEXT,
    version      TEXT,
    sentiment    TEXT DEFAULT '',
    review_date  TEXT,
    fetched_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (app_id) REFERENCES apps(app_id)
);

-- 信用卡活动/关键词提及记录
CREATE TABLE IF NOT EXISTS activity_mentions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id       TEXT NOT NULL,
    review_id    TEXT NOT NULL,
    category     TEXT NOT NULL,      -- 活动类别: 新户礼/分期优惠/...
    keyword      TEXT NOT NULL,      -- 匹配到的具体关键词
    sentiment    TEXT DEFAULT '',    -- positive/negative/neutral
    review_date  TEXT,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (app_id) REFERENCES apps(app_id),
    FOREIGN KEY (review_id) REFERENCES reviews(review_id)
);

CREATE TABLE IF NOT EXISTS risk_alerts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id       TEXT NOT NULL,
    category     TEXT NOT NULL,      -- 风险类别: 发卡问题/权益缩水/...
    mention_count INTEGER DEFAULT 0,
    alert_level  TEXT DEFAULT 'info', -- info/warning/critical
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_read      INTEGER DEFAULT 0,
    FOREIGN KEY (app_id) REFERENCES apps(app_id)
);

CREATE INDEX IF NOT EXISTS idx_rating_app ON rating_history(app_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_review_app ON reviews(app_id, fetched_at);
CREATE INDEX IF NOT EXISTS idx_activity_app ON activity_mentions(app_id, category);
CREATE INDEX IF NOT EXISTS idx_risk_app ON risk_alerts(app_id, created_at);
"""


class Storage:
    """SQLite manager for App Store + credit card monitoring data."""

    def __init__(self, db_path: str = "data/monitor.db") -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # ── App CRUD ──

    def upsert_app(self, info: dict) -> None:
        self.conn.execute("""
            INSERT INTO apps (app_id, name, developer, category, bundle_id, current_ver, price, app_url, description, bank, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(app_id) DO UPDATE SET
                name=excluded.name, developer=excluded.developer,
                category=excluded.category, current_ver=excluded.current_ver,
                price=excluded.price, app_url=excluded.app_url,
                description=excluded.description, bank=excluded.bank,
                last_updated=CURRENT_TIMESTAMP
        """, (
            info["app_id"], info["name"], info["developer"], info["category"],
            info.get("bundle_id", ""), info.get("current_version", ""),
            info.get("price", 0), info.get("app_url", ""),
            info.get("description", ""), info.get("bank", ""),
        ))
        self.conn.commit()

    def update_app_bank(self, app_id: str, bank: str) -> None:
        self.conn.execute("UPDATE apps SET bank=? WHERE app_id=?", (bank, app_id))
        self.conn.commit()

    # ── Rating ──

    def insert_rating(self, app_id: str, avg_rating: float, rating_count: int, version: str = "") -> bool:
        row = self.conn.execute(
            "SELECT avg_rating FROM rating_history WHERE app_id=? ORDER BY recorded_at DESC LIMIT 1",
            (app_id,),
        ).fetchone()
        if row and abs(row[0] - avg_rating) < 0.01:
            return False
        self.conn.execute(
            "INSERT INTO rating_history (app_id, avg_rating, rating_count, version) VALUES (?, ?, ?, ?)",
            (app_id, avg_rating, rating_count, version),
        )
        self.conn.commit()
        return True

    def get_rating_history(self, app_id: str, days: int = 30) -> list[dict]:
        rows = self.conn.execute("""
            SELECT avg_rating, rating_count, version, recorded_at FROM rating_history
            WHERE app_id=? AND recorded_at >= datetime('now', ? || ' days')
            ORDER BY recorded_at ASC
        """, (app_id, f"-{days}")).fetchall()
        return [{"avg_rating": r[0], "rating_count": r[1], "version": r[2], "time": r[3]} for r in rows]

    # ── Reviews ──

    def insert_reviews(self, reviews: list[dict]) -> int:
        count = 0
        for r in reviews:
            try:
                self.conn.execute("""
                    INSERT OR IGNORE INTO reviews (review_id, app_id, title, content, rating, author, version, review_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (r["review_id"], r["app_id"], r.get("title", ""), r["content"],
                      r["rating"], r.get("author", ""), r.get("version", ""), r.get("review_date", "")))
                if self.conn.execute("SELECT changes()").fetchone()[0] > 0:
                    count += 1
            except sqlite3.IntegrityError:
                pass
        self.conn.commit()
        return count

    def get_reviews(self, app_id: str, limit: int = 100) -> list[dict]:
        rows = self.conn.execute("""
            SELECT review_id, app_id, title, content, rating, sentiment, author, version, review_date
            FROM reviews WHERE app_id=?
            ORDER BY fetched_at DESC LIMIT ?
        """, (app_id, limit)).fetchall()
        return [
            {"review_id": r[0], "app_id": r[1], "title": r[2], "content": r[3],
             "rating": r[4], "sentiment": r[5], "author": r[6], "version": r[7],
             "review_date": r[8]}
            for r in rows
        ]

    def get_reviews_since(self, app_id: str, since_date: str, limit: int = 200) -> list[dict]:
        rows = self.conn.execute("""
            SELECT review_id, app_id, title, content, rating, sentiment, author, version, review_date
            FROM reviews WHERE app_id=? AND review_date >= ?
            ORDER BY review_date DESC LIMIT ?
        """, (app_id, since_date, limit)).fetchall()
        return [
            {"review_id": r[0], "app_id": r[1], "title": r[2], "content": r[3],
             "rating": r[4], "sentiment": r[5], "author": r[6], "version": r[7],
             "review_date": r[8]}
            for r in rows
        ]

    def update_review_sentiment(self, review_id: str, sentiment: str) -> None:
        self.conn.execute("UPDATE reviews SET sentiment=? WHERE review_id=?", (sentiment, review_id))
        self.conn.commit()

    # ── Activity Mentions ──

    def insert_activity_mention(self, app_id: str, review_id: str, category: str, keyword: str, sentiment: str = "", review_date: str = "") -> None:
        self.conn.execute("""
            INSERT OR IGNORE INTO activity_mentions (app_id, review_id, category, keyword, sentiment, review_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (app_id, review_id, category, keyword, sentiment, review_date))
        self.conn.commit()

    def get_activity_summary(self, days: int = 30) -> list[dict]:
        """Aggregate activity mentions per app per category."""
        rows = self.conn.execute("""
            SELECT a.name, a.bank, am.app_id, am.category, COUNT(*) as cnt
            FROM activity_mentions am
            JOIN apps a ON a.app_id = am.app_id
            WHERE am.created_at >= datetime('now', ? || ' days')
            GROUP BY am.app_id, am.category
            ORDER BY cnt DESC
        """, (f"-{days}",)).fetchall()
        return [
            {"app_name": r[0], "bank": r[1], "app_id": r[2], "category": r[3], "count": r[4]}
            for r in rows
        ]

    def get_activity_by_app(self, app_id: str, days: int = 30) -> list[dict]:
        rows = self.conn.execute("""
            SELECT am.category, am.keyword, am.sentiment, am.review_date
            FROM activity_mentions am
            WHERE am.app_id=? AND am.created_at >= datetime('now', ? || ' days')
            ORDER BY am.created_at DESC
        """, (app_id, f"-{days}")).fetchall()
        return [{"category": r[0], "keyword": r[1], "sentiment": r[2], "review_date": r[3]} for r in rows]

    # ── Risk Alerts ──

    def insert_risk_alert(self, app_id: str, category: str, mention_count: int, alert_level: str = "warning") -> None:
        self.conn.execute("""
            INSERT INTO risk_alerts (app_id, category, mention_count, alert_level)
            VALUES (?, ?, ?, ?)
        """, (app_id, category, mention_count, alert_level))
        self.conn.commit()

    def get_unread_risk_alerts(self, days: int = 7) -> list[dict]:
        rows = self.conn.execute("""
            SELECT ra.id, a.name, a.bank, ra.category, ra.mention_count, ra.alert_level, ra.created_at
            FROM risk_alerts ra
            JOIN apps a ON a.app_id = ra.app_id
            WHERE ra.is_read=0 AND ra.created_at >= datetime('now', ? || ' days')
            ORDER BY ra.alert_level DESC, ra.created_at DESC
        """, (f"-{days}",)).fetchall()
        return [
            {"id": r[0], "app_name": r[1], "bank": r[2], "category": r[3],
             "mention_count": r[4], "alert_level": r[5], "created_at": r[6]}
            for r in rows
        ]

    def mark_risk_alert_read(self, alert_id: int) -> None:
        self.conn.execute("UPDATE risk_alerts SET is_read=1 WHERE id=?", (alert_id,))
        self.conn.commit()

    # ── Query helpers ──

    def get_all_apps(self) -> list[dict]:
        rows = self.conn.execute("""
            SELECT a.app_id, a.name, a.developer, a.category, a.current_ver, a.price, a.bank,
                   (SELECT avg_rating FROM rating_history WHERE app_id=a.app_id ORDER BY recorded_at DESC LIMIT 1) as latest_rating,
                   (SELECT rating_count FROM rating_history WHERE app_id=a.app_id ORDER BY recorded_at DESC LIMIT 1) as rating_count,
                   (SELECT recorded_at FROM rating_history WHERE app_id=a.app_id ORDER BY recorded_at DESC LIMIT 1) as rating_time
            FROM apps a ORDER BY a.name
        """).fetchall()
        return [
            {"app_id": r[0], "name": r[1], "developer": r[2], "category": r[3],
             "current_ver": r[4], "price": r[5], "bank": r[6] or "",
             "latest_rating": r[7], "rating_count": r[8], "rating_time": r[9]}
            for r in rows
        ]

    def get_app_by_id(self, app_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT app_id, name, developer, category, bank FROM apps WHERE app_id=?",
            (app_id,),
        ).fetchone()
        if not row:
            return None
        return {"app_id": row[0], "name": row[1], "developer": row[2], "category": row[3], "bank": row[4] or ""}

    def get_rating_distribution(self, app_id: str) -> dict:
        rows = self.conn.execute("""
            SELECT rating, COUNT(*) as cnt FROM reviews
            WHERE app_id=? GROUP BY rating ORDER BY rating
        """, (app_id,)).fetchall()
        total = sum(r[1] for r in rows)
        distribution = {str(r[0]): r[1] for r in rows}
        avg = sum(r[0] * r[1] for r in rows) / total if total > 0 else 0
        return {"avg_rating": round(avg, 2), "total": total, "distribution": distribution}

    def close(self) -> None:
        self.conn.close()


import sqlite3
