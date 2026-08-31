# libwatch

ウォッチリストに登録したライブラリの公式ブログと GitHub Releases を、1本のタイムラインで見る静的サイトです。実行時のアプリサーバはなく、ビルドが `site/` に HTML を書き出します。

## 必要環境

- Python 3.11 以上
- [uv](https://docs.astral.sh/uv/)

## セットアップ

```bash
uv sync
```

## サイトの生成

リポジトリ直下で次を実行します。ウォッチ対象の正本は `watchlist.yml`、成果物は `site/index.html` と `site/style.css` です。

```bash
uv run python -m libwatch
```

## 開発サーバーの起動

生成した静的ファイルをローカルで確認するには、Python 標準ライブラリの HTTP サーバを使います。

```bash
uv run python -m http.server --directory site --bind 127.0.0.1 8000
```

ブラウザで http://127.0.0.1:8000/ を開きます。停止は `Ctrl+C` です。`site/` を再生成したあとは、ページを再読み込みしてください。
