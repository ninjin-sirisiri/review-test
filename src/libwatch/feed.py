from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Literal
from urllib.parse import urljoin, urlparse

ATOM_NS = "http://www.w3.org/2005/Atom"
ATOM = f"{{{ATOM_NS}}}"


class FeedError(ValueError):
    """Raised when bytes are neither RSS 2.0 nor Atom 1.0."""


@dataclass(frozen=True)
class Entry:
    target_name: str
    kind: Literal["blog", "releases"]
    title: str
    link: str
    summary: str | None
    published: datetime


def parse_feed(
    body: bytes,
    *,
    feed_url: str,
    target_name: str,
    kind: Literal["blog", "releases"],
) -> list[Entry]:
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise FeedError("invalid XML") from exc

    tag = root.tag
    if tag == "rss":
        return _parse_rss(root, feed_url=feed_url, target_name=target_name, kind=kind)
    if tag == f"{ATOM}feed":
        return _parse_atom(root, feed_url=feed_url, target_name=target_name, kind=kind)
    raise FeedError("not an RSS 2.0 or Atom 1.0 feed")


def _parse_rss(
    root: ET.Element,
    *,
    feed_url: str,
    target_name: str,
    kind: Literal["blog", "releases"],
) -> list[Entry]:
    entries: list[Entry] = []
    channel = root.find("channel")
    if channel is None:
        return entries
    for item in channel.findall("item"):
        entry = _entry_from_fields(
            title=_text(item.find("title")),
            raw_link=_text(item.find("link")),
            summary=_text(item.find("description")),
            published=_parse_rss_date(_text(item.find("pubDate"))),
            feed_url=feed_url,
            target_name=target_name,
            kind=kind,
        )
        if entry is not None:
            entries.append(entry)
    return entries


def _parse_atom(
    root: ET.Element,
    *,
    feed_url: str,
    target_name: str,
    kind: Literal["blog", "releases"],
) -> list[Entry]:
    entries: list[Entry] = []
    for item in root.findall(f"{ATOM}entry"):
        published = _parse_atom_date(
            _text(item.find(f"{ATOM}published"))
            or _text(item.find(f"{ATOM}updated"))
        )
        entry = _entry_from_fields(
            title=_text(item.find(f"{ATOM}title")),
            raw_link=_atom_link(item),
            summary=_text(item.find(f"{ATOM}summary")),
            published=published,
            feed_url=feed_url,
            target_name=target_name,
            kind=kind,
        )
        if entry is not None:
            entries.append(entry)
    return entries


def _entry_from_fields(
    *,
    title: str | None,
    raw_link: str | None,
    summary: str | None,
    published: datetime | None,
    feed_url: str,
    target_name: str,
    kind: Literal["blog", "releases"],
) -> Entry | None:
    if title is None or not title.strip():
        return None
    if raw_link is None or not raw_link.strip():
        return None
    if published is None:
        return None

    link = urljoin(feed_url, raw_link.strip())
    scheme = urlparse(link).scheme.lower()
    if scheme not in ("http", "https"):
        return None

    cleaned_summary: str | None
    if summary is None or not summary.strip():
        cleaned_summary = None
    else:
        cleaned_summary = summary

    return Entry(
        target_name=target_name,
        kind=kind,
        title=title,
        link=link,
        summary=cleaned_summary,
        published=published,
    )


def _text(el: ET.Element | None) -> str | None:
    if el is None or el.text is None:
        return None
    return el.text


def _atom_link(entry: ET.Element) -> str | None:
    links = entry.findall(f"{ATOM}link")
    if not links:
        return None
    alternate: str | None = None
    first_href: str | None = None
    for link in links:
        href = link.get("href")
        if not href:
            continue
        if first_href is None:
            first_href = href
        rel = link.get("rel", "alternate")
        if rel == "alternate" and alternate is None:
            alternate = href
    return alternate if alternate is not None else first_href


def _parse_rss_date(raw: str | None) -> datetime | None:
    if raw is None or not raw.strip():
        return None
    try:
        dt = parsedate_to_datetime(raw.strip())
    except (TypeError, ValueError, IndexError):
        return None
    return _as_utc(dt)


def _parse_atom_date(raw: str | None) -> datetime | None:
    if raw is None or not raw.strip():
        return None
    text = raw.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    return _as_utc(dt)


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
