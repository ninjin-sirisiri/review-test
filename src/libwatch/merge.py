from __future__ import annotations

from libwatch.feed import Entry


def _winner(left: Entry, right: Entry) -> Entry:
    if left.published != right.published:
        return left if left.published > right.published else right
    left_rel = left.kind == "releases"
    right_rel = right.kind == "releases"
    if left_rel != right_rel:
        return left if left_rel else right
    if left.target_name != right.target_name:
        return left if left.target_name < right.target_name else right
    if left.title != right.title:
        return left if left.title < right.title else right
    return left


def merge_entries(entries: list[Entry]) -> list[Entry]:
    by_link: dict[str, Entry] = {}
    for entry in entries:
        current = by_link.get(entry.link)
        if current is None:
            by_link[entry.link] = entry
        else:
            by_link[entry.link] = _winner(current, entry)
    return sorted(
        by_link.values(),
        key=lambda e: (-e.published.timestamp(), e.target_name, e.title),
    )
