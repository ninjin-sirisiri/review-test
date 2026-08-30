from __future__ import annotations

import html
from datetime import timezone

from libwatch.feed import Entry

KIND_LABELS = {
    "blog": "公式ブログ",
    "releases": "リリースノート",
}

RENDER_CSS = """\
body {
  max-width: 40rem;
  margin: 0 auto;
  padding: 1.5rem 1rem;
  font-family: system-ui, sans-serif;
  line-height: 1.5;
}
article {
  margin-bottom: 1.5rem;
}
article .meta {
  color: #444;
  font-size: 0.9rem;
}
"""


def render_html(entries: list[Entry]) -> str:
    parts: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="ja">',
        "<head>",
        '<meta charset="utf-8">',
        "<title>ライブラリ更新ウォッチ</title>",
        '<link rel="stylesheet" href="style.css">',
        "</head>",
        "<body>",
    ]
    if not entries:
        parts.append("更新はまだない")
    else:
        for entry in entries:
            parts.append(_render_entry(entry))
    parts.extend(["</body>", "</html>", ""])
    return "\n".join(parts)


def _render_entry(entry: Entry) -> str:
    title = html.escape(entry.title, quote=True)
    href = html.escape(entry.link, quote=True)
    target = html.escape(entry.target_name, quote=True)
    kind = html.escape(KIND_LABELS[entry.kind], quote=True)
    published = entry.published.astimezone(timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC"
    )
    lines = [
        "<article>",
        f'<a href="{href}">{title}</a>',
    ]
    if entry.summary is not None:
        lines.append(f"<p>{html.escape(entry.summary, quote=True)}</p>")
    lines.append(
        f'<p class="meta">{target} · {kind} · {published}</p>'
    )
    lines.append("</article>")
    return "\n".join(lines)
