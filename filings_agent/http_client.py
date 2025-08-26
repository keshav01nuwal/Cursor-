import threading
import time
import hashlib
from typing import Dict, Optional
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .robots import RobotsCache


class RateLimiter:
    def __init__(self, min_interval_seconds: float = 0.3):
        self.min_interval_seconds = min_interval_seconds
        self._lock = threading.Lock()
        self._host_last_request_at: Dict[str, float] = {}

    def wait(self, host: str) -> None:
        with self._lock:
            now = time.monotonic()
            last = self._host_last_request_at.get(host, 0.0)
            elapsed = now - last
            if elapsed < self.min_interval_seconds:
                time.sleep(self.min_interval_seconds - elapsed)
            self._host_last_request_at[host] = time.monotonic()


class HttpClient:
    def __init__(
        self,
        *,
        user_agent: str,
        max_retries: int = 3,
        backoff_factor: float = 0.8,
        min_interval_seconds: float = 0.3,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.session = requests.Session()
        retry = Retry(
            total=max_retries,
            read=max_retries,
            connect=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=16, pool_maxsize=64)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept": "*/*",
        })
        self.timeout_seconds = timeout_seconds
        self.robots = RobotsCache(self.session)
        self.rate_limiter = RateLimiter(min_interval_seconds=min_interval_seconds)

    def is_allowed(self, url: str, user_agent: Optional[str] = None) -> bool:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        return self.robots.is_allowed(base, parsed.path or "/", user_agent or self.session.headers.get("User-Agent", "*"))

    def get(self, url: str, *, allow_redirects: bool = True, stream: bool = False) -> requests.Response:
        parsed = urlparse(url)
        host = parsed.netloc
        # Robots.txt check
        if not self.is_allowed(url):
            raise PermissionError(f"Blocked by robots.txt: {url}")
        # Rate limit per host
        self.rate_limiter.wait(host)
        resp = self.session.get(url, allow_redirects=allow_redirects, timeout=self.timeout_seconds, stream=stream)
        return resp


def compute_sha256(data: bytes) -> str:
    sha = hashlib.sha256()
    sha.update(data)
    return sha.hexdigest()