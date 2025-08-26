from typing import Dict
from urllib.parse import urljoin
import urllib.robotparser

import requests


class RobotsCache:
    def __init__(self, session: requests.Session) -> None:
        self._session = session
        self._cache: Dict[str, urllib.robotparser.RobotFileParser] = {}

    def _load(self, base_url: str) -> urllib.robotparser.RobotFileParser:
        if base_url in self._cache:
            return self._cache[base_url]
        robots_url = urljoin(base_url, "/robots.txt")
        parser = urllib.robotparser.RobotFileParser()
        try:
            resp = self._session.get(robots_url, timeout=15)
            if resp.status_code == 200:
                parser.parse(resp.text.splitlines())
            else:
                # If robots not found or error, default-allow
                parser.parse(["User-agent: *", "Allow: /"])
        except Exception:
            parser.parse(["User-agent: *", "Allow: /"])
        self._cache[base_url] = parser
        return parser

    def is_allowed(self, base_url: str, path: str, user_agent: str) -> bool:
        parser = self._load(base_url)
        return parser.can_fetch(user_agent, urljoin(base_url, path))