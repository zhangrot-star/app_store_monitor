"""SQLite storage — schema for apps, ratings history, reviews."""

from __future__ import annotations

import logging
import sqlite3
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

CREATE INDEX IF NOT EXISTS idx_rating_app ON rating_history(app_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_review_app ON reviews(app_id, fetched_at);
"""


class Storage:
    """SQLite manager for App Store data."""

    def __init__(self, db_path: str = "data/monitor.db") -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def upsert_app(self, info: dict) -> None:
        self.conn.execute("""
            INSERT INTO apps (app_id, name, developer, category, bundle_id, current_ver, price, app_url, description, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(app_id) DO UPDATE SET
                name=excluded.name, developer=excluded.developer,
                category=excluded.category, current_ver=excluded.current_ver,
                price=excluded.price, app_url=excluded.app_url,
                description=excluded.description, last_updated=CURRENT_TIMESTAMP
        """, (info["app_id"], info["name"], info["developer"], info["category"],
              info.get("bundle_id", ""), info.get("current_version", ""),
              info.get("price", 0), info.get("app_url", ""), info.get("description", "")))
        self.conn.commit()

    def insert_rating(self, app_id: str, avg_rating: float, rating_count: int, version: str = "") -> bool:
        """Record rating snapshot. Returns True if rating changed significantly."""
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

    def get_rating_history(self, app_id: str, days: int = 30) -> list[dict]:
        rows = self.conn.execute("""
            SELECT avg_rating, rating_count, version, recorded_at FROM rating_history
            WHERE app_id=? AND recorded_at >= datetime('now', ? || ' days')
            ORDER BY recorded_at ASC
        """, (app_id, f"-{days}")).fetchall()
        return [{"avg_rating": r[0], "rating_count": r[1], "version": r[2], "time": r[3]} for r in rows]

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

    def get_all_apps(self) -> list[dict]:
        rows = self.conn.execute("""
            SELECT a.app_id, a.name, a.developer, a.category, a.current_ver, a.price,
                   (SELECT avg_rating FROM rating_history WHERE app_id=a.app_id ORDER BY recorded_at DESC LIMIT 1) as latest_rating,
                   (SELECT rating_count FROM rating_history WHERE app_id=a.app_id ORDER BY recorded_at DESC LIMIT 1) as rating_count,
                   (SELECT recorded_at FROM rating_history WHERE app_id=a.app_id ORDER BY recorded_at DESC LIMIT 1) as rating_time
            FROM apps a ORDER BY a.name
        """).fetchall()
        return [
            {"app_id": r[0], "name": r[1], "developer": r[2], "category": r[3],
             "current_ver": r[4], "price": r[5], "latest_rating": r[6],
             "rating_count": r[7], "rating_time": r[8]}
            for r in rows
        ]

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
