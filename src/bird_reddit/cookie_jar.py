"""Collect and persist browser cookies from reddit.com for anti-detection."""

import json
import time
from pathlib import Path

from curl_cffi.requests import Session

COOKIE_PATH = Path.home() / ".config" / "bird-reddit" / "cookies.json"
MAX_AGE_S = 24 * 60 * 60  # 24 hours

_jar = None
_collected_at = 0


def _read_jar():
    try:
        data = json.loads(COOKIE_PATH.read_text())
        if isinstance(data.get("cookies"), dict):
            return data
    except Exception:
        pass
    return None


def _write_jar(data):
    try:
        COOKIE_PATH.parent.mkdir(parents=True, exist_ok=True)
        COOKIE_PATH.write_text(json.dumps(data, indent=2) + "\n")
    except Exception:
        pass


def update_jar_from_response(response):
    """Merge Set-Cookie values from any API response into the jar."""
    global _jar
    if not response.cookies:
        return
    if _jar is None:
        _jar = {}
    for name, value in response.cookies.items():
        _jar[name] = value
    _write_jar({"cookies": _jar, "collected_at": time.time()})


def collect_browser_cookies():
    """GET reddit.com homepage with browser headers to collect cookies."""
    global _jar, _collected_at
    now = time.time()

    if _jar and (now - _collected_at) < MAX_AGE_S:
        return

    # Try loading from disk
    if not _jar:
        from_disk = _read_jar()
        if from_disk:
            disk_age = now - from_disk.get("collected_at", 0)
            if disk_age < MAX_AGE_S:
                _jar = from_disk["cookies"]
                _collected_at = now - disk_age
                return

    try:
        s = Session(impersonate="chrome")
        resp = s.get(
            "https://www.reddit.com/",
            headers={
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "accept-language": "en-US,en;q=0.9",
                "dnt": "1",
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "none",
                "sec-fetch-user": "?1",
                "upgrade-insecure-requests": "1",
            },
            timeout=15,
            allow_redirects=True,
        )
        if _jar is None:
            _jar = {}
        for name, value in resp.cookies.items():
            _jar[name] = value
        _collected_at = time.time()
        _write_jar({"cookies": _jar, "collected_at": _collected_at})
    except Exception:
        if _jar is None:
            _jar = {}
        _collected_at = time.time()


def get_cookie(name):
    """Get a specific cookie value from the jar."""
    if _jar:
        return _jar.get(name)
    return None


def build_cookie_header(reddit_session):
    """Merge jar cookies + user session cookie into one header string."""
    parts = []
    if _jar:
        for name, value in _jar.items():
            if name == "reddit_session":
                continue
            parts.append(f"{name}={value}")
    parts.append(f"reddit_session={reddit_session}")
    return "; ".join(parts)
