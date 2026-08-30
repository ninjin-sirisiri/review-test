from pathlib import Path

import pytest

from libwatch.config import ConfigError, load_watchlist


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_load_valid_watchlist(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "watchlist.yml",
        """
targets:
  - name: " React "
    blog: https://react.dev/rss.xml#frag
    releases: https://github.com/facebook/react/releases
""",
    )
    watchlist = load_watchlist(path)
    assert len(watchlist.targets) == 1
    target = watchlist.targets[0]
    assert target.name == "React"
    assert target.blog == "https://react.dev/rss.xml"
    assert target.releases == "https://github.com/facebook/react/releases.atom"


def test_blog_only_or_releases_only(tmp_path: Path) -> None:
    blog_only = load_watchlist(
        _write(
            tmp_path / "blog.yml",
            "targets:\n  - name: A\n    blog: https://example.com/feed.xml\n",
        )
    )
    assert blog_only.targets[0].releases is None
    rel_only = load_watchlist(
        _write(
            tmp_path / "rel.yml",
            "targets:\n  - name: B\n    releases: https://github.com/a/b\n",
        )
    )
    assert rel_only.targets[0].blog is None


@pytest.mark.parametrize(
    "text",
    [
        "targets: []\n",
        "targets:\n  - name: A\n",
        "targets:\n  - name: A\n    blog: ''\n    releases: ''\n",
        "targets:\n  - name: '  '\n    blog: https://example.com/feed.xml\n",
        "targets:\n  - name: A\n    blog: https://example.com/feed.xml\n  - name: A\n    releases: https://github.com/a/b\n",
        "targets:\n  - name: A\n    blog: example.com/feed.xml\n",
        "targets:\n  - name: A\n    releases: https://gitlab.com/a/b\n",
        "extra: 1\ntargets:\n  - name: A\n    blog: https://example.com/feed.xml\n",
        "targets:\n  - name: A\n    blog: https://example.com/feed.xml\n    extra: 1\n",
        "not: yaml: [",
    ],
)
def test_load_watchlist_rejects(tmp_path: Path, text: str) -> None:
    path = tmp_path / "watchlist.yml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ConfigError):
        load_watchlist(path)


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_watchlist(tmp_path / "missing.yml")


def test_invalid_utf8(tmp_path: Path) -> None:
    path = tmp_path / "watchlist.yml"
    path.write_bytes(b"\xff\xfe")
    with pytest.raises(ConfigError):
        load_watchlist(path)
