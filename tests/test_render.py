from datetime import datetime, timezone

from libwatch.feed import Entry
from libwatch.render import render_html


def _entry(
    *,
    title: str = "Title",
    link: str = "https://example.com/item",
    summary: str | None = "Summary",
    target_name: str = "Lib",
    kind: str = "blog",
    published: datetime | None = None,
) -> Entry:
    return Entry(
        target_name=target_name,
        kind=kind,  # type: ignore[arg-type]
        title=title,
        link=link,
        summary=summary,
        published=published
        or datetime(2026, 1, 2, 15, 4, 5, tzinfo=timezone.utc),
    )


def test_summary_script_is_escaped() -> None:
    html = render_html([_entry(summary="<script>alert(1)</script>")])
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_zero_entries_shows_empty_message() -> None:
    html = render_html([])
    assert "更新はまだない" in html
    assert '<!DOCTYPE html>' in html
    assert 'lang="ja"' in html
    assert "<title>ライブラリ更新ウォッチ</title>" in html
    assert 'href="style.css"' in html


def test_entry_title_is_official_link() -> None:
    html = render_html(
        [_entry(title="Rss Title", link="https://example.com/rss-item")]
    )
    assert 'href="https://example.com/rss-item"' in html
    assert ">Rss Title</a>" in html


def test_datetime_format_minutes_utc() -> None:
    html = render_html(
        [
            _entry(
                published=datetime(2026, 1, 2, 15, 4, 5, tzinfo=timezone.utc),
            )
        ]
    )
    assert "2026-01-02 15:04 UTC" in html
    assert "15:04:05" not in html


def test_kind_labels() -> None:
    blog_html = render_html([_entry(kind="blog")])
    releases_html = render_html([_entry(kind="releases")])
    assert "公式ブログ" in blog_html
    assert "リリースノート" in releases_html
