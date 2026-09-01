import os
from pathlib import Path

import pytest
import yaml

from libwatch.config import (
    ConfigError,
    WatchTarget,
    Watchlist,
    dump_watchlist,
    load_watchlist,
    parse_watchlist,
    sha256_hex,
    write_watchlist,
)


def test_parse_watchlist_roundtrip_values() -> None:
    text = """\
targets:
  - name: " React "
    blog: https://react.dev/rss.xml#frag
    releases: https://github.com/facebook/react/releases
"""
    watchlist = parse_watchlist(text)
    dumped = dump_watchlist(watchlist)
    again = parse_watchlist(dumped)
    assert again.targets == watchlist.targets
    data = yaml.safe_load(dumped)
    assert set(data.keys()) == {"targets"}
    assert list(data["targets"][0].keys()) == ["name", "blog", "releases"]
    assert data["targets"][0]["name"] == "React"
    assert data["targets"][0]["blog"] == "https://react.dev/rss.xml"
    assert (
        data["targets"][0]["releases"]
        == "https://github.com/facebook/react/releases.atom"
    )
    assert "#frag" not in dumped
    assert "facebook/react/releases\n" not in dumped


def test_dump_omits_missing_optional_keys() -> None:
    watchlist = parse_watchlist(
        "targets:\n  - name: A\n    blog: https://example.com/feed.xml\n"
    )
    dumped = dump_watchlist(watchlist)
    data = yaml.safe_load(dumped)
    assert "releases" not in data["targets"][0]
    assert "blog" in data["targets"][0]


def test_dump_drops_comments() -> None:
    text = """\
# keep me
targets:
  - name: A
    blog: https://example.com/feed.xml
"""
    dumped = dump_watchlist(parse_watchlist(text))
    assert "keep me" not in dumped


def test_sha256_hex_of_raw_bytes() -> None:
    assert sha256_hex(b"abc") == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_write_watchlist_replaces_and_leaves_no_tmp(tmp_path: Path) -> None:
    path = tmp_path / "watchlist.yml"
    path.write_text("OLD\n", encoding="utf-8")
    write_watchlist(path, "targets:\n  - name: A\n    blog: https://example.com/a.xml\n")
    assert "name: A" in path.read_text(encoding="utf-8")
    leftovers = [p.name for p in tmp_path.iterdir() if p.name != "watchlist.yml"]
    assert leftovers == []


def test_write_watchlist_keeps_old_file_if_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "watchlist.yml"
    path.write_text("OLD\n", encoding="utf-8")
    original_replace = os.replace

    def boom(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
        raise OSError("nope")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        write_watchlist(path, "NEW\n")
    assert path.read_text(encoding="utf-8") == "OLD\n"
    monkeypatch.setattr(os, "replace", original_replace)
    leftovers = [
        p.name
        for p in tmp_path.iterdir()
        if p.name != "watchlist.yml" and not p.name.startswith(".")
    ]
    assert leftovers == []


def test_load_watchlist_uses_parse(tmp_path: Path) -> None:
    path = tmp_path / "watchlist.yml"
    path.write_text(
        "targets:\n  - name: A\n    blog: https://example.com/feed.xml\n",
        encoding="utf-8",
    )
    assert load_watchlist(path).targets[0].name == "A"


def test_parse_watchlist_rejects_empty() -> None:
    with pytest.raises(ConfigError):
        parse_watchlist("targets: []\n")
