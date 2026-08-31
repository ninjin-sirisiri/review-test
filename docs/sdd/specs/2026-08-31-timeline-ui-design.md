# 文書としてのタイムライン

タイムライン1画面を、見出しの強さでスキャンできる静的な読み物にする。用語はリポジトリ直下の [CONTEXT.md](../../../CONTEXT.md) に従う。取り込み・設定・マージは [2026-08-30-libwatch-design.md](./2026-08-30-libwatch-design.md) のまま。このファイルは、その仕様の Page（タイムライン HTML と付属 CSS）を置き換える。衝突したら、マークアップと見た目はこのファイル、それ以外は親仕様。

## Classification

architectural

## Approach

文書としてのタイムライン。ページ見出しとランドマークを足し、各件のタイトルを見出しにする。余白・字・本文幅を段階で揃え、カードや影は使わない。OS のライト/ダークに追従する。カード型フィードと高密度リストは採らない。

## Goals

- 開いて数秒で、「ページ見出し」と「更新の並び」が目で分かれる。
- 見出しの強さが順位どおりになる。ページタイトル > 件のタイトル > 要約 > メタ（ウォッチ対象名・種類・日時）。
- 本文幅を読みやすい長さに抑え、余白と字サイズは段階で揃える。
- 文字はコントラスト 4.5:1 以上、区切り線は 3:1 以上。ライト/ダークは OS に追従する。
- 既存の読む単位は変えない。1本の時系列、同じ項目、公式リンク先はタイトルのまま。

## Non-goals

- カード、影、グラデーション、大きなヒーロー。
- 外部 JS、CSS の追加ファイル、複数カラム。
- 対象や種類での絞り込み、日付グルーピング、対象別ページ。
- 「更新はまだない」の文言変更、項目の追加・削除、日時形式の変更。
- 独自のブランドカラー。システム色（Canvas / CanvasText / LinkText）以外は使わない。
- Web フォント。
- `nav` / `footer` / `aside`、見出しの無い `section` で件を包むこと。
- 取り込み・設定・マージ・書き出し処理の変更。

## Architecture

実行時サーバは無い。読むのはビルドが書いた静的ファイルだけである。この変更はレンダラだけに閉じる。

```text
watchlist.yml
  → 取り込み・正規化・マージ（親仕様のまま）
  → render_html / RENDER_CSS（この仕様の HTML と CSS）
  → site/index.html と site/style.css
```

件の項目・並び・重複排除はレンダラに入る前に終わる。レンダラは受け取った件を並べ替えない。外部 JS は出さない。CSS はビルドが `site/style.css` に書く 1 ファイルだけ。単一カラム。

## Components

- **`render_html`**: 次節のページ構造の HTML 文字列を返す。実装は `src/libwatch/render.py`。
- **`RENDER_CSS`**: 見た目の規則の CSS 文字列。同じモジュール。ビルドが `site/style.css` に書く。
- **`write_site` / `build`**: 今どおり `render_html` の結果と `RENDER_CSS` を `site/` に書く。ロジックは変えない。

アプリのファイルを増やさない。

## Page

```text
html lang="ja"
  head
    meta charset="utf-8"
    meta name="viewport" content="width=device-width, initial-scale=1"
    title: ライブラリ更新ウォッチ
    link rel="stylesheet" href="style.css"
  body
    header
      h1: ライブラリ更新ウォッチ
    main
      0件: p「更新はまだない」
      1件以上: article（親仕様と同じ並び）
        h2 > a（href は公式リンク、テキストはタイトル）
        要約があれば p（要約テキスト）
        p.meta（ウォッチ対象名 · 種類 · 公開日時）
```

- `h1` はページに1つ。各件のタイトルは `h2`。`h3` 以下は使わない。
- 0件でも `header` と `h1` は出す。`article` は出さない。空メッセージは `main` 内の `p` に「更新はまだない」。
- 各件の出す項目は親仕様と同じ。タイトル（公式リンク先）、あれば要約、ウォッチ対象名、種類（「公式ブログ」または「リリースノート」）、公開日時（UTC、`YYYY-MM-DD HH:MM UTC`）。
- タイトル・要約・ウォッチ対象名・種類は HTML として解釈しない。`html.escape(..., quote=True)` したテキストとして出す。`href` もエスケープする。
- 失敗した更新源はページに出さない。
- `script` 要素は出さない。`style.css` 以外の外部リソースは参照しない。

## Visual

トークンは `:root` に置く。使わない変数は置かない。

```css
color-scheme: light dark;
--text: CanvasText;
--bg: Canvas;
--muted: color-mix(in oklab, CanvasText 62%, Canvas);
--line: color-mix(in oklab, CanvasText 50%, Canvas);
--accent: LinkText;
```

`--line` を 50% にするのは、区切り線のコントラスト 3:1 を満たすため。本文・見出し・リンクは 4.5:1 以上。`--muted` のメタも 4.5:1 以上。

| 対象 | 規則 |
|---|---|
| `body` | `max-width: 68ch`。左右中央。`padding: 1.5rem 1rem`。`font-family: system-ui, sans-serif`。本文色 `--text`、背景 `--bg`。字 `1rem` / 400、行間 `1.55` |
| `body > header` | 下線 `1px solid var(--line)`。`padding-bottom: 1rem`。`margin-bottom: 2.5rem` |
| `h1` | `2.25rem` / 700、行間 `1.2`。上マージン 0 |
| `article h2` | `1.375rem` / 650、行間 `1.2`。`margin: 0 0 0.4em`。件が多いので章見出しより一段小さくする。`h1` より小さく、本文より大きい |
| `h2 a` | 色 `--accent`。下線を残す（`text-decoration: none` にしない） |
| 要約の `p`、空メッセージの `p` | 本文と同じ色・サイズ。空メッセージは薄くしない |
| `p.meta` | `0.875rem` / 400。色 `--muted` |
| `article + article` | `margin-top: 1.5rem`。`padding-top: 1.5rem`。`border-top: 1px solid var(--line)`。枠・影・カード背景は付けない |

`box-shadow` は CSS に出さない。グラデーションは使わない。`article` に背景色は付けない。

## Data flow

1. 親仕様どおりウォッチリストを読み、取り込み、正規化し、マージする。
2. `render_html` がマージ結果を受け取り、Page の HTML を返す。0件なら空メッセージのページ。
3. `RENDER_CSS` を `style.css` として、HTML と揃えて `site/` に書く（親仕様の書き出し）。

並べ順・重複排除・件の落とし方は親仕様。このレンダラはそれを変えない。

## Error handling

新しい失敗はない。マージまで通れば HTML と CSS は必ず出る。0件は失敗ではなく、Page の空ページを書く。

設定エラー・取り込みスキップ・書き出しのロールバックは親仕様のまま。ページに失敗した更新源は出さない。

## Numeric defaults

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

## Consuming paths

- 読者は今までどおり `watchlist.yml` を編集し、リポジトリ直下で `python3 -m libwatch` を実行し、`site/index.html` をブラウザで開く。
- ローカル確認は README の開発サーバ手順のまま。新しいコマンドは無い。
- GitHub Actions の間隔と成果物は親仕様のまま。

## Testing

既定テストはネットワークに出ない。スクリーンショットは取らない。対象は主に `tests/test_render.py`。

残す:

- タイトルは公式リンク。要約・対象名・種類はエスケープする。`href` もエスケープする。
- 日時は `YYYY-MM-DD HH:MM UTC`。種類は「公式ブログ」「リリースノート」。
- 0件の本文に「更新はまだない」。`href="style.css"` を1つ参照する。`script` は無い。

足す:

- `header` の中に `h1`（テキストは「ライブラリ更新ウォッチ」）と、`main` がある。
- 各件は `article`。タイトルは `h2` > `a`。
- 0件でも `header` と `h1` はある。`article` は無い。空メッセージは `main` 内。
- `name="viewport"` があり、`content` に `width=device-width` と `initial-scale=1` を含む。
- CSS に `color-scheme: light dark` と `68ch` がある。`box-shadow` は無い。
