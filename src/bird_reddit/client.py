"""Core HTTP client for Reddit's JSON API with anti-detection infrastructure."""

import random
import sys
import time

from curl_cffi.requests import Session, Response

from bird_reddit.session_store import get_device_id
from bird_reddit.cookie_jar import (
    collect_browser_cookies,
    build_cookie_header,
    update_jar_from_response,
)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
BASE = "https://www.reddit.com"


class RateLimitState:
    def __init__(self):
        self.remaining = None
        self.used = None
        self.reset = None  # seconds until reset

    def update(self, headers):
        if "x-ratelimit-remaining" in headers:
            try:
                self.remaining = float(headers["x-ratelimit-remaining"])
            except ValueError:
                pass
        if "x-ratelimit-used" in headers:
            try:
                self.used = int(headers["x-ratelimit-used"])
            except ValueError:
                pass
        if "x-ratelimit-reset" in headers:
            try:
                self.reset = int(headers["x-ratelimit-reset"])
            except ValueError:
                pass

    def should_pause(self):
        if self.remaining is not None and self.remaining < 5:
            return True
        return False

    def pause_seconds(self):
        if self.reset:
            return min(self.reset + 1, 120)
        return 30


class RedditClient:
    def __init__(self, reddit_session, no_jitter=False, timeout=30):
        self.reddit_session = reddit_session
        self.no_jitter = no_jitter
        self.timeout = timeout
        self.device_id = None
        self.modhash = None
        self.cookie_header = None
        self._initialized = False
        self._rate = RateLimitState()
        self._session = Session(impersonate="chrome")

    def _ensure_init(self):
        if not self._initialized:
            self._init()

    def _init(self):
        # 1. Load stable device ID
        try:
            self.device_id = get_device_id()
        except Exception:
            import uuid
            self.device_id = str(uuid.uuid4())

        # 2. Collect browser cookies
        try:
            collect_browser_cookies()
        except Exception:
            pass

        # 3. Build cookie header
        self.cookie_header = build_cookie_header(self.reddit_session)

        # 4. Fetch modhash from /api/me.json
        try:
            data = self._raw_get("/api/me.json")
            if isinstance(data, dict) and "data" in data:
                self.modhash = data["data"].get("modhash", "")
            elif isinstance(data, dict):
                self.modhash = data.get("modhash", "")
        except Exception:
            self.modhash = ""

        self._initialized = True

    def _build_headers(self, is_post=False):
        headers = {
            "accept": "application/json, text/html,*/*;q=0.9",
            "accept-language": "en-US,en;q=0.9",
            "user-agent": UA,
            "origin": "https://www.reddit.com",
            "referer": "https://www.reddit.com/",
            "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "cookie": self.cookie_header or f"reddit_session={self.reddit_session}",
        }
        if is_post:
            headers["content-type"] = "application/x-www-form-urlencoded"
            if self.modhash:
                headers["x-modhash"] = self.modhash
        return headers

    def _raw_get(self, path):
        """Low-level GET used during init (no init check)."""
        url = f"{BASE}{path}"
        headers = {
            "accept": "application/json",
            "accept-language": "en-US,en;q=0.9",
            "user-agent": UA,
            "cookie": self.cookie_header or f"reddit_session={self.reddit_session}",
        }
        resp = self._session.get(url, headers=headers, timeout=self.timeout)
        update_jar_from_response(resp)
        self.cookie_header = build_cookie_header(self.reddit_session)
        resp.raise_for_status()
        return resp.json()

    def _get(self, path, params=None):
        """GET with init check and rate limit awareness."""
        self._ensure_init()
        if self._rate.should_pause():
            wait = self._rate.pause_seconds()
            print(f"[rate limit] pausing {wait}s...", file=sys.stderr)
            time.sleep(wait)

        url = f"{BASE}{path}"
        resp = self._session.get(
            url, headers=self._build_headers(), params=params, timeout=self.timeout
        )
        update_jar_from_response(resp)
        self.cookie_header = build_cookie_header(self.reddit_session)
        self._rate.update(resp.headers)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path, data=None):
        """POST with init, modhash injection, jitter, and rate limit."""
        self._ensure_init()
        if self._rate.should_pause():
            wait = self._rate.pause_seconds()
            print(f"[rate limit] pausing {wait}s...", file=sys.stderr)
            time.sleep(wait)

        if not self.no_jitter:
            jitter = random.uniform(10, 30)
            time.sleep(jitter)

        if data is None:
            data = {}
        if self.modhash:
            data["uh"] = self.modhash

        url = f"{BASE}{path}"
        resp = self._session.post(
            url, headers=self._build_headers(is_post=True), data=data, timeout=self.timeout
        )
        update_jar_from_response(resp)
        self.cookie_header = build_cookie_header(self.reddit_session)
        self._rate.update(resp.headers)
        resp.raise_for_status()
        return resp.json()

    # ── Public API ───────────────────────────────────────────────────────────

    def search(self, query, subreddit=None, count=25, sort="new", time_filter="week"):
        sub = subreddit or "all"
        return self._get(f"/r/{sub}/search.json", params={
            "q": query,
            "sort": sort,
            "t": time_filter,
            "limit": count,
            "restrict_sr": "on" if subreddit else "off",
            "type": "link",
            "raw_json": 1,
        })

    def subreddit_posts(self, name, count=25, sort="hot", time_filter="week"):
        params = {"limit": count, "raw_json": 1}
        if sort == "top":
            params["t"] = time_filter
        return self._get(f"/r/{name}/{sort}.json", params=params)

    def read_post(self, post_id, comment_count=20):
        # Strip prefix if provided
        post_id = post_id.removeprefix("t3_")
        data = self._get(f"/comments/{post_id}.json", params={
            "limit": comment_count,
            "sort": "confidence",
            "raw_json": 1,
        })
        # Reddit returns [post_listing, comment_listing]
        post = None
        comments = []
        if isinstance(data, list) and len(data) >= 1:
            children = data[0].get("data", {}).get("children", [])
            if children:
                post = children[0].get("data", {})
        if isinstance(data, list) and len(data) >= 2:
            comments = [
                c.get("data", {})
                for c in data[1].get("data", {}).get("children", [])
                if c.get("kind") == "t1"
            ]
        return {"post": post, "comments": comments}

    def reply(self, thing_id, text):
        """Reply to a post (t3_) or comment (t1_)."""
        # Ensure proper prefix
        if not thing_id.startswith(("t1_", "t3_")):
            thing_id = f"t3_{thing_id}"
        return self._post("/api/comment", data={
            "thing_id": thing_id,
            "text": text,
            "api_type": "json",
        })

    def submit_post(self, subreddit, title, body=None, url=None):
        data = {
            "sr": subreddit,
            "title": title,
            "api_type": "json",
            "resubmit": "true",
        }
        if url:
            data["kind"] = "link"
            data["url"] = url
        else:
            data["kind"] = "self"
            data["text"] = body or ""
        return self._post("/api/submit", data=data)

    def me(self):
        return self._get("/api/me.json")

    def user_about(self, username):
        return self._get(f"/user/{username}/about.json")

    def mentions(self, count=25):
        return self._get("/message/mentions.json", params={
            "limit": count,
            "raw_json": 1,
        })
