from datetime import datetime, timezone

from libwatch.feed import Entry
from libwatch.merge import merge_entries

UTC = timezone.utc


def _e(
    *,
    name: str,
    title: str,
    link: str,
    published: datetime,
    kind: str = "blog",
    summary: str | None = None,
) -> Entry:
    return Entry(
        target_name=name,
        kind=kind,  # type: ignore[arg-type]
        title=title,
        link=link,
        summary=summary,
        published=published,
    )


def test_sort_by_published_then_name_then_title() -> None:
    early = datetime(2026, 1, 1, tzinfo=UTC)
    late = datetime(2026, 1, 2, tzinfo=UTC)
    same = datetime(2026, 1, 3, tzinfo=UTC)
    entries = [
        _e(name="B", title="b", link="https://e/1", published=early),
        _e(name="A", title="z", link="https://e/2", published=late),
        _e(name="C", title="m", link="https://e/3", published=same),
        _e(name="A", title="a", link="https://e/4", published=same),
    ]
    merged = merge_entries(entries)
    assert [e.link for e in merged] == [
        "https://e/4",
        "https://e/3",
        "https://e/2",
        "https://e/1",
    ]


def test_same_link_keeps_newer() -> None:
    link = "https://e/same"
    older = _e(name="A", title="old", link=link, published=datetime(2026, 1, 1, tzinfo=UTC))
    newer = _e(name="B", title="new", link=link, published=datetime(2026, 1, 2, tzinfo=UTC))
    merged = merge_entries([older, newer])
    assert len(merged) == 1
    assert merged[0].title == "new"


def test_same_link_same_time_prefers_releases() -> None:
    link = "https://e/same"
    when = datetime(2026, 1, 1, tzinfo=UTC)
    blog = _e(name="A", title="blog", link=link, published=when, kind="blog")
    rel = _e(name="B", title="rel", link=link, published=when, kind="releases")
    merged = merge_entries([blog, rel])
    assert len(merged) == 1
    assert merged[0].kind == "releases"


def test_same_link_same_time_same_kind_prefers_name_then_title() -> None:
    link = "https://e/same"
    when = datetime(2026, 1, 1, tzinfo=UTC)
    z = _e(name="Z", title="a", link=link, published=when, kind="blog")
    a_late = _e(name="A", title="z", link=link, published=when, kind="blog")
    a_early = _e(name="A", title="a", link=link, published=when, kind="blog")
    merged = merge_entries([z, a_late, a_early])
    assert len(merged) == 1
    assert merged[0].target_name == "A"
    assert merged[0].title == "a"


def test_does_not_mutate_input() -> None:
    entries = [
        _e(name="A", title="a", link="https://e/1", published=datetime(2026, 1, 1, tzinfo=UTC))
    ]
    snapshot = list(entries)
    merge_entries(entries)
    assert entries == snapshot
