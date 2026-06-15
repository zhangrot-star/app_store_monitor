"""App competitive comparison matrix — multi-app ranking across dimensions.

Credit card edition: includes bank name in matrix rows.
"""

from __future__ import annotations

from typing import Any


def build_comparison_matrix(storage: Any) -> dict:
    """Build multi-dimensional comparison across all monitored bank apps."""
    apps = storage.get_all_apps()
    if len(apps) < 2:
        return {"products": apps, "rankings": {}, "matrix": []}

    rows = []
    for app in apps:
        dist = storage.get_rating_distribution(app["app_id"])
        rows.append({
            **app,
            "rating_dist": dist,
        })

    matrix = []
    for r in rows:
        matrix.append({
            "name": r["name"],
            "app_id": r["app_id"],
            "bank": r.get("bank", ""),
            "developer": r.get("developer", ""),
            "category": r.get("category", ""),
            "rating": r["latest_rating"],
            "rating_count": r["rating_count"],
            "current_ver": r.get("current_ver", ""),
            "rating_time": r.get("rating_time", ""),
            "review_total": r["rating_dist"].get("total", 0),
        })

    return {
        "products": rows,
        "rankings": _compute_rankings(rows),
        "matrix": sorted(matrix, key=lambda x: x.get("rating", 0) or 0, reverse=True),
    }


def _compute_rankings(rows: list[dict]) -> dict:
    if not rows:
        return {}

    def rank(key, reverse=False):
        valid = [r for r in rows if r.get(key)]
        return [(r["name"], r.get("bank", "")) for r in sorted(valid, key=lambda x: x.get(key, 0), reverse=reverse)[:5]]

    return {
        "rating_high_to_low": rank("latest_rating", reverse=True),
        "most_ratings": rank("rating_count", reverse=True),
        "most_reviews_collected": rank("rating_dist.total", reverse=True),
    }
