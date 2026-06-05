"""Rating trend analysis — change detection, anomaly alerting."""

from __future__ import annotations

import logging
from typing import Any

from config.settings import AppConfig

logger = logging.getLogger(__name__)


def analyze_rating_changes(storage: Any, config: AppConfig) -> list[dict]:
    """Analyze latest rating vs previous snapshot. Returns alerts for significant changes."""
    apps = storage.get_all_apps()
    threshold = config.analysis.rating_alert_threshold
    alerts = []

    for app in apps:
        history = storage.get_rating_history(app["app_id"], days=30)
        if len(history) < 2:
            continue

        latest = history[-1]
        previous = history[-2]

        change = round(latest["avg_rating"] - previous["avg_rating"], 3)
        count_change = latest["rating_count"] - previous["rating_count"]

        record = {
            "app_id": app["app_id"],
            "name": app["name"],
            "current_rating": latest["avg_rating"],
            "previous_rating": previous["avg_rating"],
            "change": change,
            "rating_count": latest["rating_count"],
            "count_change": count_change,
            "version": latest["version"],
            "direction": "up" if change > 0 else "down",
            "alert": abs(change) >= threshold,
        }
        if record["alert"]:
            alerts.append(record)

    alerts.sort(key=lambda x: abs(x["change"]), reverse=True)
    return alerts


def compute_rating_summary(storage: Any) -> dict:
    """Aggregate rating stats across all monitored apps."""
    apps = storage.get_all_apps()
    ratings = [a["latest_rating"] for a in apps if a["latest_rating"] is not None]
    if not ratings:
        return {}

    return {
        "app_count": len(ratings),
        "avg_rating": round(sum(ratings) / len(ratings), 2),
        "min_rating": min(ratings),
        "max_rating": max(ratings),
        "below_4": sum(1 for r in ratings if r < 4.0),
        "above_4_5": sum(1 for r in ratings if r >= 4.5),
    }
