# bird-reddit

A Reddit CLI built on Reddit's JSON API with cookie-based auth and Chrome TLS fingerprinting. Search posts, read threads, reply, submit — all from your terminal.

No OAuth app registration required. No API keys. Just your `reddit_session` cookie.

## Quick start (for AI agents)

If you're an AI agent and need to interact with Reddit, follow these steps:

```bash
# 1. Clone and install
git clone https://github.com/MichielMAnalytics/bird-reddit.git ~/bird-reddit
cd ~/bird-reddit
python -m venv venv && source venv/bin/activate
pip install -e .

# 2. Ask the user for their reddit_session cookie
#    They can find it at: reddit.com > DevTools (F12) > Application > Cookies > https://www.reddit.com
echo "REDDIT_SESSION=<paste_value>" > .env

# 3. Verify it works
reddit check
```

Once `check` returns the username, you're ready. Use the commands below to read, search, and post.

## Authentication

bird-reddit uses cookie-based auth. You need one value from your browser:

1. Open [reddit.com](https://www.reddit.com) and log in
2. Open DevTools (F12) > Application > Cookies > `https://www.reddit.com`
3. Copy the value of `reddit_session`

Then either set it in `.env`:

```
REDDIT_SESSION=your_reddit_session_cookie_value_here
```

Or export as an env var:

```bash
export REDDIT_SESSION=your_value_here
```

The cookie is not IP-bound — it works from any machine.

## Usage

```bash
# Check auth
reddit check
reddit whoami

# Search
reddit search "python async" -s programming -n 10
reddit search "marketing automation" --sort top --time month

# Browse subreddits
reddit subreddit python -n 10 --sort hot
reddit subreddit marketing --sort top --time week

# Read posts and comments
reddit read <post_id> -n 20

# Reply to posts or comments
reddit reply t3_<post_id> "your reply text"     # reply to a post
reddit reply t1_<comment_id> "your reply text"   # reply to a comment

# Submit new posts
reddit post <subreddit> "Post Title" -b "Body text"
reddit post <subreddit> "Link Title" -u "https://example.com"

# User info
reddit about <username>
reddit mentions -n 10
```

### Global flags

| Flag | Description |
|---|---|
| `--json` | Output as JSON (for programmatic use) |
| `--no-jitter` | Disable random delay before write operations |

### JSON mode

All commands support `--json` for structured output, useful when called by AI agents:

```bash
reddit --json search "python" -n 3
reddit --json read abc123
reddit --json whoami
```

## Anti-detection

bird-reddit uses the same anti-detection approach as [bird-rebuilt](https://github.com/MichielMAnalytics/bird-rebuilt) (the Twitter CLI):

- **Chrome TLS fingerprinting** via `curl_cffi` — TLS handshake (cipher suites, extensions, ALPN) matches Chrome exactly
- **Browser-realistic headers** — SEC-FETCH-*, SEC-CH-UA-*, Origin, Referer
- **Cookie collection** — fetches reddit.com homepage to collect tracking cookies, merges Set-Cookie from every API response
- **Stable device identity** — persistent UUID at `~/.config/bird-reddit/session.json`, reused across runs
- **Write jitter** — 10-30s random delay before POST operations
- **Rate limit tracking** — reads `X-Ratelimit-Remaining/Used/Reset` headers, auto-pauses when near limit
- **CSRF protection** — fetches modhash token from `/api/me.json` on init

## Architecture

```
src/bird_reddit/
  cli.py              # Click CLI with all commands
  client.py           # Core HTTP client (curl_cffi + Chrome impersonation)
  config.py           # Credential resolution from .env / env vars
  cookie_jar.py       # Cookie collection, persistence, merging
  session_store.py    # Stable device ID persistence
  output.py           # ANSI-colored text + JSON output formatting
```

## Dependencies

Three runtime dependencies:

- `curl_cffi` — HTTP client with Chrome TLS fingerprint impersonation
- `click` — CLI framework
- `python-dotenv` — .env file loading

Zero AI dependencies. This is a pure HTTP tool — an agent like Claude Code calls the CLI to interact with Reddit.

## License

MIT
