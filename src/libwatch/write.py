from __future__ import annotations

import os
import tempfile
from pathlib import Path


def write_site(site_dir: Path, html: str, css: str) -> None:
    site_dir.mkdir(parents=True, exist_ok=True)

    html_dest = site_dir / "index.html"
    css_dest = site_dir / "style.css"
    prev_html = html_dest.read_bytes() if html_dest.is_file() else None

    html_fd, html_tmp = tempfile.mkstemp(prefix=".index.", suffix=".tmp", dir=site_dir)
    css_fd, css_tmp = tempfile.mkstemp(prefix=".style.", suffix=".tmp", dir=site_dir)
    html_path = Path(html_tmp)
    css_path = Path(css_tmp)
    html_replaced = False
    try:
        with os.fdopen(html_fd, "w", encoding="utf-8") as f:
            f.write(html)
        with os.fdopen(css_fd, "w", encoding="utf-8") as f:
            f.write(css)
        # Both temps must exist before either replace.
        if not html_path.is_file() or not css_path.is_file():
            raise OSError("temporary site files missing before replace")
        os.replace(html_path, html_dest)
        html_replaced = True
        os.replace(css_path, css_dest)
    except Exception:
        for path in (html_path, css_path):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        if html_replaced:
            try:
                _restore_html(html_dest, prev_html, site_dir)
            except Exception:
                pass
        raise


def _restore_html(html_dest: Path, prev_html: bytes | None, site_dir: Path) -> None:
    if prev_html is None:
        html_dest.unlink(missing_ok=True)
        return
    fd, tmp = tempfile.mkstemp(prefix=".index.rollback.", suffix=".tmp", dir=site_dir)
    tmp_path = Path(tmp)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(prev_html)
        os.replace(tmp_path, html_dest)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise
