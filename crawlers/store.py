"""Apple App Store crawler — real-time app data via iTunes Search API + RSS feeds.

Endpoints:
  - Search:  https://itunes.apple.com/search?term=X&country=cn&entity=software
  - Lookup:  https://itunes.apple.com/cn/lookup?id={app_id}
  - Reviews: https://itunes.apple.com/cn/rss/customerreviews/id={app_id}/sortBy=mostRecent/json
"""

from __future__ import annotations

import logging

from crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

_ITUNES_SEARCH = "https://itunes.apple.com/search"
_ITUNES_LOOKUP = "https://itunes.apple.com/{country}/lookup"
_ITUNES_REVIEWS = "https://itunes.apple.com/{country}/rss/customerreviews/id={app_id}/sortBy=mostRecent/json"


class AppStoreCrawler(BaseCrawler):
    """Fetch App Store metadata, ratings, and reviews via public iTunes API."""

    def __init__(self, country: str = "cn", **kwargs) -> None:
        super().__init__(**kwargs)
        self.country = country

    def get_app_info(self, app_id: str) -> dict | None:
        """Lookup app by ID — returns metadata + ratings."""
        url = _ITUNES_LOOKUP.format(country=self.country)
        data = self.get_json(url, params={"id": app_id})
        if not data or not data.get("results"):
            return None

        a = data["results"][0]
        return {
            "app_id": str(app_id),
            "name": a.get("trackName", ""),
            "developer": a.get("artistName", ""),
            "category": a.get("primaryGenreName", ""),
            "current_version": a.get("version", ""),
            "avg_rating": float(a.get("averageUserRating", 0)),
            "rating_count": int(a.get("userRatingCount", 0)),
            "price": float(a.get("price", 0)),
            "formatted_price": a.get("formattedPrice", "免费"),
            "bundle_id": a.get("bundleId", ""),
            "release_date": a.get("releaseDate", ""),
            "last_updated": a.get("currentVersionReleaseDate", ""),
            "description": (a.get("description", "") or "")[:500],
            "seller_url": a.get("sellerUrl", ""),
            "app_url": a.get("trackViewUrl", ""),
        }

    def get_reviews(self, app_id: str, max_count: int = 50) -> list[dict]:
        """Fetch recent reviews via RSS. Tries country store first, then US as fallback."""
        # Try configured country first
        url = _ITUNES_REVIEWS.format(country=self.country, app_id=app_id)
        data = self.get_json(url)
        if data:
            entries = data.get("feed", {}).get("entry", [])
            if len(entries) > 1:
                return self._parse_review_entries(entries[1:max_count + 1], app_id)

        # Fallback: try US store
        if self.country != "us":
            logger.debug("No reviews in %s store, trying US fallback", self.country)
            url = _ITUNES_REVIEWS.format(country="us", app_id=app_id)
            data = self.get_json(url)
            if data:
                entries = data.get("feed", {}).get("entry", [])
                if len(entries) > 1:
                    return self._parse_review_entries(entries[1:max_count + 1], app_id)

        return []

    def _parse_review_entries(self, entries: list, app_id: str) -> list[dict]:
        results = []
        for e in entries:
            try:
                results.append({
                    "review_id": e.get("id", {}).get("label", ""),
                    "app_id": app_id,
                    "title": e.get("title", {}).get("label", ""),
                    "content": e.get("content", {}).get("label", ""),
                    "rating": int(e.get("im:rating", {}).get("label", 0)),
                    "author": e.get("author", {}).get("name", {}).get("label", ""),
                    "version": e.get("im:version", {}).get("label", ""),
                    "review_date": e.get("updated", {}).get("label", ""),
                })
            except (KeyError, ValueError, AttributeError):
                continue
        return results

    def search_apps(self, keyword: str, limit: int = 20) -> list[dict]:
        """Search App Store for apps by keyword."""
        params = {
            "term": keyword,
            "country": self.country,
            "entity": "software",
            "limit": limit,
        }
        data = self.get_json(_ITUNES_SEARCH, params=params)
        if not data:
            return []

        results = []
        for a in data.get("results", []):
            results.append({
                "app_id": str(a.get("trackId", "")),
                "name": a.get("trackName", ""),
                "developer": a.get("artistName", ""),
                "category": a.get("primaryGenreName", ""),
                "avg_rating": float(a.get("averageUserRating", 0)),
                "rating_count": int(a.get("userRatingCount", 0)),
                "formatted_price": a.get("formattedPrice", "免费"),
                "version": a.get("version", ""),
            })
        return results

    def get_category_ranking(self, genre_id: str = "6014", limit: int = 20) -> list[dict]:
        """Get top free apps by category. genre_id reference: 6014=Business, 6024=Shopping..."""
        # iTunes RSS top charts
        url = f"https://itunes.apple.com/{self.country}/rss/topfreeapplications/limit={limit}/genre={genre_id}/json"
        data = self.get_json(url)
        if not data:
            return []

        results = []
        for e in data.get("feed", {}).get("entry", []):
            try:
                aid = e.get("id", {}).get("attributes", {}).get("im:id", "")
                results.append({
                    "app_id": aid,
                    "name": e.get("im:name", {}).get("label", ""),
                    "developer": e.get("im:artist", {}).get("label", ""),
                    "category": e.get("category", {}).get("attributes", {}).get("label", ""),
                })
            except (KeyError, AttributeError):
                continue
        return results
