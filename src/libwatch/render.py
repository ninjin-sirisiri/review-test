from __future__ import annotations

import html
from datetime import timezone

from libwatch.feed import Entry

KIND_LABELS = {
    "blog": "公式ブログ",
    "releases": "リリースノート",
}

RENDER_CSS = """\
:root {
  color-scheme: light dark;
  --text: CanvasText;
  --bg: Canvas;
  --muted: color-mix(in oklab, CanvasText 62%, Canvas);
  --line: color-mix(in oklab, CanvasText 50%, Canvas);
  --accent: LinkText;
}

body {
  max-width: 68ch;
  margin: 0 auto;
  padding: 1.5rem 1rem;
  font-family: system-ui, sans-serif;
  font-size: 1rem;
  font-weight: 400;
  line-height: 1.55;
  color: var(--text);
  background: var(--bg);
}

body > header {
  border-bottom: 1px solid var(--line);
  padding-bottom: 1rem;
  margin-bottom: 2.5rem;
}

h1 {
  font-size: 2.25rem;
  font-weight: 700;
  line-height: 1.2;
  margin: 0;
}

article + article {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--line);
}

article h2 {
  font-size: 1.375rem;
  font-weight: 650;
  line-height: 1.2;
  margin: 0 0 0.4em;
}

h2 a {
  color: var(--accent);
}

p.meta {
  font-size: 0.875rem;
  font-weight: 400;
  color: var(--muted);
}
"""


def render_html(entries: list[Entry]) -> str:
    parts: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="ja">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>ライブラリ更新ウォッチ</title>",
        '<link rel="stylesheet" href="style.css">',
        "</head>",
        "<body>",
        "<header>",
        "<h1>ライブラリ更新ウォッチ</h1>",
        "</header>",
        "<main>",
    ]
    if not entries:
        parts.append("<p>更新はまだない</p>")
    else:
        for entry in entries:
            parts.append(_render_entry(entry))
    parts.extend(["</main>", "</body>", "</html>", ""])
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
        f'<h2><a href="{href}">{title}</a></h2>',
    ]
    if entry.summary is not None:
        lines.append(f"<p>{html.escape(entry.summary, quote=True)}</p>")
    lines.append(
        f'<p class="meta">{target} · {kind} · {published}</p>'
    )
    lines.append("</article>")
    return "\n".join(lines)
