import os
from pathlib import Path

import pytest

from libwatch.write import write_site


def test_write_site_replaces_broken_index(tmp_path: Path) -> None:
    site = tmp_path / "site"
    site.mkdir()
    broken = site / "index.html"
    broken.write_text("<html>BROKEN", encoding="utf-8")

    html = "<!DOCTYPE html><html lang=\"ja\"><head><title>ok</title></head><body>done</body></html>"
    css = "body { max-width: 40rem; margin: 0 auto; }"

    write_site(site, html, css)

    assert (site / "index.html").read_text(encoding="utf-8") == html
    assert (site / "style.css").read_text(encoding="utf-8") == css
    leftovers = [
        p.name
        for p in site.iterdir()
        if p.name not in {"index.html", "style.css"}
    ]
    assert leftovers == []


def test_write_site_rolls_back_if_css_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("OLD_HTML", encoding="utf-8")
    (site / "style.css").write_text("OLD_CSS", encoding="utf-8")

    original_replace = os.replace

    def replace_and_fail(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
        if Path(dst).name == "style.css":
            raise OSError("disk full")
        original_replace(src, dst)

    monkeypatch.setattr(os, "replace", replace_and_fail)

    with pytest.raises(OSError, match="disk full"):
        write_site(site, "NEW_HTML", "NEW_CSS")

    assert (site / "index.html").read_text(encoding="utf-8") == "OLD_HTML"
    assert (site / "style.css").read_text(encoding="utf-8") == "OLD_CSS"


def test_write_site_removes_new_index_if_first_css_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    site = tmp_path / "site"
    site.mkdir()

    original_replace = os.replace

    def replace_and_fail(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
        if Path(dst).name == "style.css":
            raise OSError("disk full")
        original_replace(src, dst)

    monkeypatch.setattr(os, "replace", replace_and_fail)

    with pytest.raises(OSError, match="disk full"):
        write_site(site, "NEW_HTML", "NEW_CSS")

    assert not (site / "index.html").exists()
    assert not (site / "style.css").exists()
