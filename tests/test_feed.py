from datetime import datetime, timezone
from pathlib import Path

import pytest

from libwatch.feed import FeedError, parse_feed

FIXTURES = Path(__file__).parent / "fixtures" / "feeds"


def test_parse_rss() -> None:
    entries = parse_feed(
        (FIXTURES / "rss.xml").read_bytes(),
        feed_url="https://example.com/feed.xml",
        target_name="Lib",
        kind="blog",
    )
    assert len(entries) == 1
    entry = entries[0]
    assert entry.title == "Rss Title"
    assert entry.link == "https://example.com/rss-item"
    assert entry.summary == "Rss desc"
    assert entry.kind == "blog"
    assert entry.target_name == "Lib"
    assert entry.published == datetime(2026, 1, 2, 15, 4, 5, tzinfo=timezone.utc)


def test_parse_atom_ignores_content() -> None:
    entries = parse_feed(
        (FIXTURES / "atom.xml").read_bytes(),
        feed_url="https://example.com/atom.xml",
        target_name="Lib",
        kind="releases",
    )
    assert len(entries) == 1
    assert entries[0].summary == "Atom sum"
    assert entries[0].title == "Atom Title"
    assert "BODY" not in (entries[0].summary or "")
    assert entries[0].published == datetime(2026, 1, 3, 7, 8, 9, tzinfo=timezone.utc)


def test_relative_link() -> None:
    entries = parse_feed(
        (FIXTURES / "relative.xml").read_bytes(),
        feed_url="https://example.com/feed.xml",
        target_name="Lib",
        kind="blog",
    )
    assert entries[0].link == "https://example.com/rel-path"


def test_drop_bad_items() -> None:
    entries = parse_feed(
        (FIXTURES / "drop.xml").read_bytes(),
        feed_url="https://example.com/feed.xml",
        target_name="Lib",
        kind="blog",
    )
    assert [e.title for e in entries] == ["Keep"]
    assert entries[0].link == "https://example.com/keep"


def test_empty_feed() -> None:
    entries = parse_feed(
        (FIXTURES / "empty_rss.xml").read_bytes(),
        feed_url="https://example.com/feed.xml",
        target_name="Lib",
        kind="blog",
    )
    assert entries == []


def test_not_a_feed() -> None:
    with pytest.raises(FeedError):
        parse_feed(
            (FIXTURES / "not_feed.xml").read_bytes(),
            feed_url="https://example.com/feed.xml",
            target_name="Lib",
            kind="blog",
        )
