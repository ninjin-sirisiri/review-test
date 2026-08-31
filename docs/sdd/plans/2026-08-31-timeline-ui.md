# 文書としてのタイムライン Implementation Plan

**Goal:** タイムライン1画面を、見出しの強さでスキャンできる静的な読み物として出す。

**Architecture:** 実行時サーバは無い。変えるのは `render_html` と `RENDER_CSS` だけ。取り込み・正規化・マージ・`write_site` は触らない。レンダラは渡された件を並べ替えず、Page の HTML とトークン付き CSS を返す。

**Tech Stack:** Python 3.11+、pytest、stdlib `html.escape`。新しい依存は足さない。テストは `uv run python -m pytest`。

**Spec:** docs/sdd/specs/2026-08-31-timeline-ui-design.md

## Global Constraints

- 本文幅: `68ch`
- `body` 余白: 上下 `1.5rem`、左右 `1rem`
- `header` 下余白: `2.5rem`。下線の下パディング: `1rem`
- 件の間隔: `1.5rem`（マージンとパディング）
- `h1`: `2.25rem` / 700
- `h2`: `1.375rem` / 650
- 本文: `1rem` / 400、行間 `1.55`
- メタ: `0.875rem`
- `--muted`: CanvasText 62%
- `--line`: CanvasText 50%
- CSS ファイル: 1。JS ファイル: 0
- コントラスト: テキスト 4.5:1、区切り線 3:1
- 既定テストはネットワークに出ない。スクリーンショットは取らない。
- トークンは `:root` に置く。使わない変数は置かない。
- `box-shadow` は CSS に出さない。グラデーションは使わない。`article` に背景色は付けない。
- `script` 要素は出さない。`style.css` 以外の外部リソースは参照しない。
- `h1` はページに1つ。各件のタイトルは `h2`。`h3` 以下は使わない。
- 空メッセージは `main` 内の `p` に「更新はまだない」。
- レンダラは受け取った件を並べ替えない。
- アプリのファイルを増やさない。
- カード、影、グラデーション、大きなヒーロー。
- 外部 JS、CSS の追加ファイル、複数カラム。
- 対象や種類での絞り込み、日付グルーピング、対象別ページ。
- 「更新はまだない」の文言変更、項目の追加・削除、日時形式の変更。
- 独自のブランドカラー。システム色（Canvas / CanvasText / LinkText）以外は使わない。
- Web フォント。
- `nav` / `footer` / `aside`、見出しの無い `section` で件を包むこと。
- 取り込み・設定・マージ・書き出し処理の変更。
- 新しいコマンドは無い。

## File structure

| Path | Responsibility |
|---|---|
| `src/libwatch/render.py` | `render_html` と `RENDER_CSS`。この計画で変える唯一のアプリファイル |
| `tests/test_render.py` | ページ構造と CSS 文字列のテスト |
| `src/libwatch/write.py` | 触らない |
| `src/libwatch/build.py` | 触らない。今どおり `render_html` と `RENDER_CSS` を `site/` に渡す |

この表に無いアプリファイルを足さない。Node ツールチェーンを足さない。

## Task 1: 文書タイムラインの HTML と CSS

**Files:**
- Modify: `tests/test_render.py`
- Modify: `src/libwatch/render.py`

**Interfaces:** 名前と引数は今のまま。

- `render_html(entries: list[Entry]) -> str`
- `RENDER_CSS: str`
- `KIND_LABELS` は今のまま（`blog` → `公式ブログ`、`releases` → `リリースノート`）

`render_html` が出す木:

```text
<!DOCTYPE html>
<html lang="ja">
head: charset、viewport（width=device-width, initial-scale=1）、title「ライブラリ更新ウォッチ」、href="style.css"
body
  header
    h1 ライブラリ更新ウォッチ
  main
    0件: <p>更新はまだない</p>
    1件以上: article
      h2 > a（公式リンク、タイトル）
      要約があれば p
      p.meta（対象名 · 種類 · YYYY-MM-DD HH:MM UTC）
```

タイトル・要約・対象名・種類・href は `html.escape(..., quote=True)`。`nav` / `footer` / `aside` / `script` / `h3` は出さない。`style.css` 以外の外部リソースは参照しない。

`RENDER_CSS` は次の文字列（これ以外の変数・`box-shadow`・`text-decoration: none`・グラデーション・`article` の背景色は置かない）:

```css
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
```

- [ ] **Step 1: 失敗するテスト**

`tests/test_render.py` を次の内容にする。既存のエスケープ・日時・種類・公式リンクのテストは残す。`RENDER_CSS` を import する。

```python
from datetime import datetime, timezone

from libwatch.feed import Entry
from libwatch.render import RENDER_CSS, render_html


def _entry(
    *,
    title: str = "Title",
    link: str = "https://example.com/item",
    summary: str | None = "Summary",
    target_name: str = "Lib",
    kind: str = "blog",
    published: datetime | None = None,
) -> Entry:
    return Entry(
        target_name=target_name,
        kind=kind,  # type: ignore[arg-type]
        title=title,
        link=link,
        summary=summary,
        published=published
        or datetime(2026, 1, 2, 15, 4, 5, tzinfo=timezone.utc),
    )


def test_summary_script_is_escaped() -> None:
    html = render_html([_entry(summary="<script>alert(1)</script>")])
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_zero_entries_shows_empty_message() -> None:
    html = render_html([])
    assert "更新はまだない" in html
    assert "<!DOCTYPE html>" in html
    assert 'lang="ja"' in html
    assert "<title>ライブラリ更新ウォッチ</title>" in html
    assert html.count('href="style.css"') == 1
    assert "<script" not in html
    assert "<article>" not in html
    header_start = html.index("<header>")
    header_end = html.index("</header>")
    h1 = "<h1>ライブラリ更新ウォッチ</h1>"
    assert header_start < html.index(h1) < header_end
    main = html[html.index("<main>") : html.index("</main>")]
    assert "<p>更新はまだない</p>" in main
    assert 'name="viewport"' in html
    assert "width=device-width" in html
    assert "initial-scale=1" in html


def test_entry_title_is_official_link() -> None:
    html = render_html(
        [_entry(title="Rss Title", link="https://example.com/rss-item")]
    )
    assert 'href="https://example.com/rss-item"' in html
    assert ">Rss Title</a>" in html
    assert '<h2><a href="https://example.com/rss-item">Rss Title</a></h2>' in html
    assert "<article>" in html
    header_start = html.index("<header>")
    header_end = html.index("</header>")
    assert header_start < html.index("<h1>ライブラリ更新ウォッチ</h1>") < header_end
    assert "<main>" in html


def test_datetime_format_minutes_utc() -> None:
    html = render_html(
        [
            _entry(
                published=datetime(2026, 1, 2, 15, 4, 5, tzinfo=timezone.utc),
            )
        ]
    )
    assert "2026-01-02 15:04 UTC" in html
    assert "15:04:05" not in html


def test_kind_labels() -> None:
    blog_html = render_html([_entry(kind="blog")])
    releases_html = render_html([_entry(kind="releases")])
    assert "公式ブログ" in blog_html
    assert "リリースノート" in releases_html


def test_two_entries_are_articles_with_h2_links() -> None:
    html = render_html(
        [
            _entry(title="First", link="https://example.com/a"),
            _entry(title="Second", link="https://example.com/b"),
        ]
    )
    assert html.count("<article>") == 2
    assert '<h2><a href="https://example.com/a">First</a></h2>' in html
    assert '<h2><a href="https://example.com/b">Second</a></h2>' in html
    assert "<h3" not in html
    assert "<nav" not in html
    assert "<footer" not in html
    assert "<aside" not in html


def test_render_css_document_tokens() -> None:
    assert "color-scheme: light dark" in RENDER_CSS
    assert "68ch" in RENDER_CSS
    assert "box-shadow" not in RENDER_CSS
    assert "text-decoration: none" not in RENDER_CSS
    assert ":root" in RENDER_CSS
    assert "CanvasText" in RENDER_CSS
    assert "50%" in RENDER_CSS
    assert "62%" in RENDER_CSS
```

- [ ] **Step 2: 失敗を確認**

```bash
uv run python -m pytest tests/test_render.py -q
```

`test_zero_entries_shows_empty_message` と `test_entry_title_is_official_link` と新規テストが失敗する。エスケープ・日時・種類は今の HTML でも通ってよい。

- [ ] **Step 3: 実装**

`src/libwatch/render.py` を次にする。`write.py` と `build.py` は編集しない。

```python
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
```

- [ ] **Step 4: テストを通す**

```bash
uv run python -m pytest -q
```

全テストがネットワーク無しで緑。

- [ ] **Step 5: コミット**

```bash
git add src/libwatch/render.py tests/test_render.py
git commit -m "$(cat <<'EOF'
タイムラインを見出しでスキャンできる文書にする。

EOF
)"
```
