from io import StringIO
from pathlib import Path

from libwatch.build import build
from libwatch.fetch import FetchError

FIXTURES = Path(__file__).parent / "fixtures" / "feeds"


def test_bad_yaml_returns_1_and_does_not_touch_site(tmp_path: Path) -> None:
    (tmp_path / "watchlist.yml").write_text("not: valid: yaml: [", encoding="utf-8")
    site = tmp_path / "site"
    site.mkdir()
    index = site / "index.html"
    index.write_text("KEEP ME", encoding="utf-8")
    stderr = StringIO()

    code = build(cwd=tmp_path, fetch=lambda url: b"", stderr=stderr)

    assert code == 1
    assert index.read_text(encoding="utf-8") == "KEEP ME"
    assert stderr.getvalue() != ""


def test_bad_yaml_does_not_create_site(tmp_path: Path) -> None:
    (tmp_path / "watchlist.yml").write_text("targets: []\n", encoding="utf-8")
    stderr = StringIO()

    code = build(cwd=tmp_path, fetch=lambda url: b"", stderr=stderr)

    assert code == 1
    assert not (tmp_path / "site").exists()


def test_one_fetch_failure_still_writes_other_entries(tmp_path: Path) -> None:
    (tmp_path / "watchlist.yml").write_text(
        "\n".join(
            [
                "targets:",
                "  - name: Lib",
                "    blog: https://example.com/feed.xml",
                "    releases: https://github.com/acme/lib/releases",
                "",
            ]
        ),
        encoding="utf-8",
    )
    rss = (FIXTURES / "rss.xml").read_bytes()
    atom_url = "https://github.com/acme/lib/releases.atom"

    def fake_fetch(url: str) -> bytes:
        if url == "https://example.com/feed.xml":
            raise FetchError("HTTP 404")
        if url == atom_url:
            return rss
        raise AssertionError(f"unexpected url: {url}")

    stderr = StringIO()
    code = build(cwd=tmp_path, fetch=fake_fetch, stderr=stderr)

    assert code == 0
    html = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    assert "Rss Title" in html
    assert (
        "skip source: Lib blog https://example.com/feed.xml: HTTP 404\n"
        in stderr.getvalue()
    )


def test_all_fetch_errors_return_0_with_empty_message(tmp_path: Path) -> None:
    (tmp_path / "watchlist.yml").write_text(
        "\n".join(
            [
                "targets:",
                "  - name: Lib",
                "    blog: https://example.com/feed.xml",
                "",
            ]
        ),
        encoding="utf-8",
    )

    def fake_fetch(url: str) -> bytes:
        raise FetchError("HTTP 404")

    stderr = StringIO()
    code = build(cwd=tmp_path, fetch=fake_fetch, stderr=stderr)

    assert code == 0
    html = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    assert "更新はまだない" in html
    assert "skip source: Lib blog https://example.com/feed.xml: HTTP 404\n" in (
        stderr.getvalue()
    )


def test_atom_content_body_not_in_html(tmp_path: Path) -> None:
    (tmp_path / "watchlist.yml").write_text(
        "\n".join(
            [
                "targets:",
                "  - name: Lib",
                "    releases: https://github.com/acme/lib/releases",
                "",
            ]
        ),
        encoding="utf-8",
    )
    atom = (FIXTURES / "atom.xml").read_bytes()

    def fake_fetch(url: str) -> bytes:
        assert url == "https://github.com/acme/lib/releases.atom"
        return atom

    stderr = StringIO()
    code = build(cwd=tmp_path, fetch=fake_fetch, stderr=stderr)

    assert code == 0
    html = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    assert "Atom Title" in html
    assert "THIS IS BODY DO NOT USE" not in html
