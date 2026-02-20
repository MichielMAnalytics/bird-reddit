"""Formatted and JSON output for raw Reddit API dicts. ANSI colors, no external libs."""

import json
from datetime import datetime, timezone

# ANSI escape codes
BOLD = "\033[1m"
RESET = "\033[0m"
CYAN = "\033[36m"
BLUE = "\033[34m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
DIM = "\033[2m"


def _ts(utc_ts):
    if not utc_ts:
        return "?"
    dt = datetime.fromtimestamp(utc_ts, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M UTC")


# ── JSON-mode formatters (return dicts) ─────────────────────────────────────

def format_submission(data):
    """Format a submission dict from Reddit's JSON API."""
    d = data.get("data", data) if isinstance(data, dict) else data
    return {
        "id": d.get("id", ""),
        "subreddit": d.get("subreddit", ""),
        "title": d.get("title", ""),
        "author": d.get("author", "[deleted]"),
        "score": d.get("score", 0),
        "upvote_ratio": d.get("upvote_ratio", 0),
        "num_comments": d.get("num_comments", 0),
        "created": _ts(d.get("created_utc")),
        "url": f"https://reddit.com{d.get('permalink', '')}",
        "selftext": d.get("selftext", ""),
        "link_url": d.get("url") if not d.get("is_self") else None,
        "flair": d.get("link_flair_text"),
    }


def format_comment(data):
    """Format a comment dict from Reddit's JSON API."""
    d = data.get("data", data) if isinstance(data, dict) else data
    return {
        "id": d.get("id", ""),
        "author": d.get("author", "[deleted]"),
        "score": d.get("score", 0),
        "created": _ts(d.get("created_utc")),
        "body": d.get("body", ""),
        "parent_id": d.get("parent_id", ""),
        "is_submitter": d.get("is_submitter", False),
    }


# ── Text-mode printers (write to stdout) ────────────────────────────────────

def print_submission_text(data):
    d = format_submission(data)
    print(f"{BOLD}{d['title']}{RESET}")
    print(f"  r/{d['subreddit']} | {d['author']} | {d['score']} pts | {d['num_comments']} comments | {d['created']}")
    if d["selftext"]:
        body = d["selftext"][:500]
        if len(d["selftext"]) > 500:
            body += "..."
        print(f"  {body}")
    if d["link_url"]:
        print(f"  {CYAN}{d['link_url']}{RESET}")
    print(f"  {BLUE}{d['url']}{RESET}")
    print(f"  id: {d['id']}")
    print()


def print_comment_text(data):
    d = format_comment(data)
    op_tag = " [OP]" if d["is_submitter"] else ""
    print(f"  {BOLD}{d['author']}{op_tag}{RESET} | {d['score']} pts | {d['created']}")
    body = d["body"][:400]
    if len(d["body"]) > 400:
        body += "..."
    for line in body.split("\n"):
        print(f"    {line}")
    print(f"    id: {d['id']}")
    print()


# ── Utility printers ────────────────────────────────────────────────────────

def print_json(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))


def print_success(msg):
    print(f"{GREEN}{msg}{RESET}")


def print_error(msg):
    import sys
    print(f"{RED}{msg}{RESET}", file=sys.stderr)


def print_info(msg):
    print(f"{DIM}{msg}{RESET}")
