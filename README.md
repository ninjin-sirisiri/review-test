# libwatch

ウォッチリストに登録したライブラリの公式ブログと GitHub Releases を、1本のタイムラインで見る静的サイトです。読む成果物はビルドが `site/` に書く HTML で、公開用にアプリサーバは不要です。ウォッチ対象の正本は `watchlist.yml` です。手編集してもよいです。ローカルでプレビューし、画面からウォッチ対象を増減するときだけ管理プロセスを使います。

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

生成した `site/` は、サーバ無しでファイルとして開いても読めます。

## ローカルプレビューと管理

同じディレクトリで次を実行します。待ち受けは `127.0.0.1` だけです。

```bash
uv run python -m libwatch serve
```

起動時に表示される `http://127.0.0.1:8000/`（タイムライン）と `http://127.0.0.1:8000/manage`（ウォッチ対象の追加・編集・削除）をブラウザで開きます。`localhost` というホスト名は使わないでください。停止は `Ctrl+C` です。

ポートを変える例:

```bash
uv run python -m libwatch serve --port 8001
```

画面で `watchlist.yml` を変えたあとにタイムラインへ新しい更新を載せるには、もう一度 `uv run python -m libwatch` でビルドします。管理プロセスは再起動しなくて構いません。ページを再読み込みしてください。
