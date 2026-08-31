from datetime import datetime, timezone

from libwatch.feed import Entry
from libwatch.render import RENDER_CSS, render_html


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
    assert "<!DOCTYPE html>" in html
    assert 'lang="ja"' in html
    assert "<title>ライブラリ更新ウォッチ</title>" in html
    assert html.count('href="style.css"') == 1
    assert "<script" not in html
    assert "<article>" not in html
    header_start = html.index("<header>")
    header_end = html.index("</header>")
    h1 = "<h1>ライブラリ更新ウォッチ</h1>"
    assert header_start < html.index(h1) < header_end
    main = html[html.index("<main>") : html.index("</main>")]
    assert "<p>更新はまだない</p>" in main
    assert 'name="viewport"' in html
    assert "width=device-width" in html
    assert "initial-scale=1" in html


def test_entry_title_is_official_link() -> None:
    html = render_html(
        [_entry(title="Rss Title", link="https://example.com/rss-item")]
    )
    assert 'href="https://example.com/rss-item"' in html
    assert ">Rss Title</a>" in html
    assert '<h2><a href="https://example.com/rss-item">Rss Title</a></h2>' in html
    assert "<article>" in html
    header_start = html.index("<header>")
    header_end = html.index("</header>")
    assert header_start < html.index("<h1>ライブラリ更新ウォッチ</h1>") < header_end
    assert "<main>" in html


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


def test_two_entries_are_articles_with_h2_links() -> None:
    html = render_html(
        [
            _entry(title="First", link="https://example.com/a"),
            _entry(title="Second", link="https://example.com/b"),
        ]
    )
    assert html.count("<article>") == 2
    assert '<h2><a href="https://example.com/a">First</a></h2>' in html
    assert '<h2><a href="https://example.com/b">Second</a></h2>' in html
    assert "<h3" not in html
    assert "<nav" not in html
    assert "<footer" not in html
    assert "<aside" not in html


def test_render_css_document_tokens() -> None:
    assert "color-scheme: light dark" in RENDER_CSS
    assert "68ch" in RENDER_CSS
    assert "box-shadow" not in RENDER_CSS
    assert "text-decoration: none" not in RENDER_CSS
    assert ":root" in RENDER_CSS
    assert "CanvasText" in RENDER_CSS
    assert "50%" in RENDER_CSS
    assert "62%" in RENDER_CSS
