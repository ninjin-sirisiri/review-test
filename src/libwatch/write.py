from __future__ import annotations

import os
import tempfile
from pathlib import Path


def write_site(site_dir: Path, html: str, css: str) -> None:
    site_dir.mkdir(parents=True, exist_ok=True)

    html_fd, html_tmp = tempfile.mkstemp(prefix=".index.", suffix=".tmp", dir=site_dir)
    css_fd, css_tmp = tempfile.mkstemp(prefix=".style.", suffix=".tmp", dir=site_dir)
    html_path = Path(html_tmp)
    css_path = Path(css_tmp)
    try:
        with os.fdopen(html_fd, "w", encoding="utf-8") as f:
            f.write(html)
        with os.fdopen(css_fd, "w", encoding="utf-8") as f:
            f.write(css)
        # Both temps must exist before either replace.
        if not html_path.is_file() or not css_path.is_file():
            raise OSError("temporary site files missing before replace")
        os.replace(html_path, site_dir / "index.html")
        os.replace(css_path, site_dir / "style.css")
    except Exception:
        for path in (html_path, css_path):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        raise
