"""Base crawler with anti-blocking: random delays, retry, cookie persistence."""

from __future__ import annotations

import logging
import random
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class BaseCrawler:
    """Common crawler with retry + rate-limit + session management."""

    def __init__(
        self,
        delay: float = 3.0,
        max_retries: int = 3,
        timeout: int = 15,
        user_agent: str | None = None,
        use_proxy: bool = False,
        proxy: str = "",
    ) -> None:
        self.delay = delay
        self.timeout = timeout
        self.proxy_url = proxy if use_proxy else None

        ua = user_agent or (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        )
        self._base_headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
        }

        self.session = requests.Session()
        self.session.headers.update(self._base_headers)

        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        if self.proxy_url:
            self.session.proxies = {"http": self.proxy_url, "https": self.proxy_url}
            # Disable SSL verification when using proxy (common in China)
            self.session.verify = False
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _jitter(self) -> None:
        """Random delay to avoid detection."""
        time.sleep(self.delay * random.uniform(0.5, 1.5))

    def get(self, url: str, params: dict | None = None, **kwargs) -> requests.Response | None:
        """GET with retry and jitter."""
        self._jitter()
        try:
            resp = self.session.get(
                url, params=params, timeout=self.timeout, **kwargs
            )
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            logger.error("GET %s failed: %s", url[:80], e)
            return None

    def get_json(self, url: str, params: dict | None = None, **kwargs) -> dict | None:
        """GET JSON API."""
        self._jitter()
        try:
            resp = self.session.get(
                url, params=params, timeout=self.timeout, **kwargs
            )
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as e:
            logger.error("GET JSON %s failed: %s", url[:80], e)
            return None
