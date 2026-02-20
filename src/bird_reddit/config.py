"""Credential resolution: load reddit_session from env or .env file."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def _find_env():
    cwd = Path.cwd()
    for d in [cwd, *cwd.parents]:
        candidate = d / ".env"
        if candidate.exists():
            return candidate
    pkg_env = Path(__file__).resolve().parent.parent.parent / ".env"
    if pkg_env.exists():
        return pkg_env
    return None


def resolve_credentials():
    """Return the reddit_session cookie value, or exit with instructions."""
    env_path = _find_env()
    if env_path:
        load_dotenv(env_path)

    reddit_session = os.getenv("REDDIT_SESSION")
    if not reddit_session:
        print(
            "Missing REDDIT_SESSION cookie.\n\n"
            "To get your cookie:\n"
            "1. Open reddit.com in your browser and log in\n"
            "2. Open DevTools (F12) > Application > Cookies > https://www.reddit.com\n"
            "3. Find the cookie named 'reddit_session' and copy its value\n"
            "4. Set it in .env:  REDDIT_SESSION=your_value_here\n"
            "   Or as env var:  export REDDIT_SESSION=your_value_here",
            file=sys.stderr,
        )
        sys.exit(1)

    return reddit_session
