from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Literal, TextIO

from libwatch.config import ConfigError, WatchTarget, load_watchlist
from libwatch.feed import Entry, FeedError, parse_feed
from libwatch.fetch import FetchError, fetch_feed
from libwatch.merge import merge_entries
from libwatch.render import RENDER_CSS, render_html
from libwatch.write import write_site


def build(*, cwd: Path, fetch: Callable[[str], bytes], stderr: TextIO) -> int:
    try:
        watchlist = load_watchlist(cwd / "watchlist.yml")
    except ConfigError as exc:
        print(str(exc), file=stderr)
        return 1

    collected: list[Entry] = []
    for target in watchlist.targets:
        if target.blog is not None:
            collected.extend(
                _fetch_source(
                    target=target,
                    kind="blog",
                    url=target.blog,
                    fetch=fetch,
                    stderr=stderr,
                )
            )
        if target.releases is not None:
            collected.extend(
                _fetch_source(
                    target=target,
                    kind="releases",
                    url=target.releases,
                    fetch=fetch,
                    stderr=stderr,
                )
            )

    merged = merge_entries(collected)
    html = render_html(merged)
    write_site(cwd / "site", html, RENDER_CSS)
    return 0


def _fetch_source(
    *,
    target: WatchTarget,
    kind: Literal["blog", "releases"],
    url: str,
    fetch: Callable[[str], bytes],
    stderr: TextIO,
) -> list[Entry]:
    try:
        body = fetch(url)
        return parse_feed(
            body,
            feed_url=url,
            target_name=target.name,
            kind=kind,
        )
    except FetchError as exc:
        reason = exc.reason
    except FeedError:
        reason = "not a feed"
    except Exception:
        reason = "connection failed"

    stderr.write(f"skip source: {target.name} {kind} {url}: {reason}\n")
    return []


def build_main() -> int:
    return build(cwd=Path.cwd(), fetch=fetch_feed, stderr=sys.stderr)
