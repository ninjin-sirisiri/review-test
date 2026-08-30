from pathlib import Path

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
