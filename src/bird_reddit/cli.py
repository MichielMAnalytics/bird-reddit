"""Click CLI for Reddit - search, read, reply, post from the terminal."""

import sys

import click

from bird_reddit.config import resolve_credentials
from bird_reddit.client import RedditClient
from bird_reddit.output import (
    format_submission,
    format_comment,
    print_json,
    print_submission_text,
    print_comment_text,
    print_success,
    print_error,
)


@click.group()
@click.option("--json", "use_json", is_flag=True, help="Output as JSON")
@click.option("--no-jitter", is_flag=True, help="Disable random delay before writes")
@click.pass_context
def cli(ctx, use_json, no_jitter):
    """Reddit CLI - search, read, and reply from the terminal."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = use_json
    ctx.obj["no_jitter"] = no_jitter
    ctx.obj["_client"] = None


def _get_client(ctx):
    """Lazy client creation — only resolves credentials when a command actually runs."""
    if ctx.obj["_client"] is None:
        reddit_session = resolve_credentials()
        ctx.obj["_client"] = RedditClient(reddit_session, no_jitter=ctx.obj["no_jitter"])
    return ctx.obj["_client"]


# ── search ──────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("query")
@click.option("-s", "--subreddit", default=None, help="Limit to a specific subreddit")
@click.option("-n", "--count", default=25, help="Number of results")
@click.option("--sort", type=click.Choice(["relevance", "new", "hot", "top", "comments"]), default="new")
@click.option("--time", "time_filter", type=click.Choice(["all", "day", "week", "month", "year"]), default="week")
@click.pass_context
def search(ctx, query, subreddit, count, sort, time_filter):
    """Search for posts."""
    client = _get_client(ctx)
    data = client.search(query, subreddit=subreddit, count=count, sort=sort, time_filter=time_filter)

    posts = data.get("data", {}).get("children", [])
    if ctx.obj["json"]:
        print_json([format_submission(p) for p in posts])
    else:
        print(f"Found {len(posts)} results for '{query}'")
        print("\u2500" * 60)
        for p in posts:
            print_submission_text(p)


# ── read ────────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("post_id")
@click.option("-n", "--comments", "comment_count", default=20, help="Number of top comments")
@click.pass_context
def read(ctx, post_id, comment_count):
    """Read a post and its comments."""
    client = _get_client(ctx)
    result = client.read_post(post_id, comment_count=comment_count)

    post = result["post"]
    comments = result["comments"]

    if ctx.obj["json"]:
        out = format_submission(post) if post else {}
        out["comments"] = [format_comment(c) for c in comments]
        print_json(out)
    else:
        if post:
            print_submission_text(post)
        if comments:
            print(f"\u2500\u2500\u2500 Comments ({len(comments)}) \u2500\u2500\u2500")
            print()
            for c in comments:
                print_comment_text(c)


# ── reply ───────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("thing_id")
@click.argument("text")
@click.pass_context
def reply(ctx, thing_id, text):
    """Reply to a post (t3_xxx) or comment (t1_xxx)."""
    client = _get_client(ctx)
    result = client.reply(thing_id, text)

    # Reddit wraps reply in json.data.things
    things = result.get("json", {}).get("data", {}).get("things", [])
    errors = result.get("json", {}).get("errors", [])

    if errors:
        for err in errors:
            print_error(f"Reddit error: {err}")
        sys.exit(1)

    if ctx.obj["json"]:
        if things:
            comment_data = things[0].get("data", {})
            print_json({
                "status": "ok",
                "comment_id": comment_data.get("id", ""),
                "thing_id": thing_id,
                "url": f"https://reddit.com{comment_data.get('permalink', '')}",
            })
        else:
            print_json({"status": "ok", "thing_id": thing_id})
    else:
        if things:
            comment_data = things[0].get("data", {})
            print_success(f"Reply posted: https://reddit.com{comment_data.get('permalink', '')}")
        else:
            print_success("Reply posted")


# ── post ────────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("subreddit_name")
@click.argument("title")
@click.option("-b", "--body", default="", help="Post body text")
@click.option("-u", "--url", default=None, help="Link URL (creates link post)")
@click.pass_context
def post(ctx, subreddit_name, title, body, url):
    """Create a new post in a subreddit."""
    client = _get_client(ctx)
    result = client.submit_post(subreddit_name, title, body=body, url=url)

    data = result.get("json", {}).get("data", {})
    errors = result.get("json", {}).get("errors", [])

    if errors:
        for err in errors:
            print_error(f"Reddit error: {err}")
        sys.exit(1)

    post_url = data.get("url", "")
    post_id = data.get("id", "")

    if ctx.obj["json"]:
        print_json({"status": "ok", "post_id": post_id, "url": post_url})
    else:
        print_success(f"Post created: {post_url}")


# ── subreddit ───────────────────────────────────────────────────────────────

@cli.command()
@click.argument("name")
@click.option("-n", "--count", default=25, help="Number of posts")
@click.option("--sort", type=click.Choice(["hot", "new", "top", "rising"]), default="hot")
@click.option("--time", "time_filter", type=click.Choice(["all", "day", "week", "month", "year"]), default="week")
@click.pass_context
def subreddit(ctx, name, count, sort, time_filter):
    """Browse a subreddit."""
    client = _get_client(ctx)
    data = client.subreddit_posts(name, count=count, sort=sort, time_filter=time_filter)

    posts = data.get("data", {}).get("children", [])
    if ctx.obj["json"]:
        print_json([format_submission(p) for p in posts])
    else:
        print(f"r/{name} - {sort} ({len(posts)} posts)")
        print("\u2500" * 60)
        for p in posts:
            print_submission_text(p)


# ── whoami ──────────────────────────────────────────────────────────────────

@cli.command()
@click.pass_context
def whoami(ctx):
    """Show current authenticated user."""
    client = _get_client(ctx)
    result = client.me()

    d = result.get("data", result)
    name = d.get("name", "unknown")

    if ctx.obj["json"]:
        print_json({
            "name": name,
            "id": d.get("id", ""),
            "comment_karma": d.get("comment_karma", 0),
            "link_karma": d.get("link_karma", 0),
            "created": d.get("created_utc", ""),
        })
    else:
        print(f"\033[1m{name}\033[0m")
        print(f"  comment karma: {d.get('comment_karma', 0)}")
        print(f"  link karma: {d.get('link_karma', 0)}")


# ── check ───────────────────────────────────────────────────────────────────

@cli.command()
@click.pass_context
def check(ctx):
    """Check authentication status."""
    client = _get_client(ctx)
    try:
        result = client.me()
        d = result.get("data", result)
        name = d.get("name")
        if not name:
            raise ValueError("No user data returned - cookie may be invalid")
        if ctx.obj["json"]:
            print_json({"status": "ok", "user": name})
        else:
            print_success(f"Authenticated as u/{name}")
    except Exception as e:
        if ctx.obj["json"]:
            print_json({"status": "error", "error": str(e)})
        else:
            print_error(f"Auth failed: {e}")
        sys.exit(1)


# ── about ───────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("username")
@click.pass_context
def about(ctx, username):
    """Show info about a Reddit user."""
    client = _get_client(ctx)
    result = client.user_about(username)

    d = result.get("data", result)
    if ctx.obj["json"]:
        print_json({
            "name": d.get("name", ""),
            "id": d.get("id", ""),
            "comment_karma": d.get("comment_karma", 0),
            "link_karma": d.get("link_karma", 0),
            "is_mod": d.get("is_mod", False),
            "created": d.get("created_utc", ""),
        })
    else:
        print(f"\033[1m{d.get('name', username)}\033[0m")
        print(f"  comment karma: {d.get('comment_karma', 0)}")
        print(f"  link karma: {d.get('link_karma', 0)}")
        print(f"  moderator: {d.get('is_mod', False)}")


# ── mentions ────────────────────────────────────────────────────────────────

@cli.command()
@click.option("-n", "--count", default=25, help="Number of mentions")
@click.pass_context
def mentions(ctx, count):
    """Show recent mentions of your username."""
    client = _get_client(ctx)
    result = client.mentions(count=count)

    items = result.get("data", {}).get("children", [])
    if ctx.obj["json"]:
        print_json([format_comment(c) for c in items])
    else:
        print(f"Recent mentions ({len(items)})")
        print("\u2500" * 60)
        for c in items:
            print_comment_text(c)


def main():
    cli()
