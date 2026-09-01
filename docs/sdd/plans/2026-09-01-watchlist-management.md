# 管理画面からのウォッチ対象の変更 Implementation Plan

**Goal:** 読者が `python -m libwatch serve` の管理画面からウォッチ対象を追加・編集・削除し、正本の `watchlist.yml` だけを更新する。

**Architecture:** 引数なしのビルドは今のまま `site/` にタイムラインを書く。`serve` は `127.0.0.1` だけで静的 `site/` と管理画面を出し、POST は YAML を正規化して書きビルドしない。管理 HTML はプロセスだけが出し、`site/` には書かない。

**Tech Stack:** Python 3.11+、pytest、PyYAML、stdlib `http.server` / `http.client` / `hashlib` / `html` / `urllib.parse`。新しい依存は足さない。テストは `uv run python -m pytest`。既定テストはネットワークに出ない。

**Spec:** docs/sdd/specs/2026-09-01-watchlist-management-design.md

## Global Constraints

- 待ち受け: `127.0.0.1`。既定ポート 8000。`--port` は 1〜65535。使用中なら起動失敗。
- 許可 Origin: `http://127.0.0.1:{port}` のみ（実際に待っているポート）。`localhost` は案内しない。その Origin の書き込みは 403。
- POST 本文上限: 64 KiB。
- 衝突ハッシュ: SHA-256、小文字 hex、ファイルの生バイト。
- 成功: 303、`Location: /manage`。成功メッセージ用クエリなし。
- 管理 CSS パス: `/manage.css`。管理パス: `/manage`（末尾スラッシュ同一）。予約パスは `site/` より優先。
- クエリ: `edit`, `confirm_delete`。フォーム `action`: `add` | `edit` | `delete`。
- GET は YAML を変えない。追加・編集・削除の確定は POST だけ。
- 最後の1件に削除リンクを出さない。POST でも 0 件になる削除は拒否。
- 追加はリスト末尾。改名は位置を維持。並び替え UI なし。
- 画面保存はファイル全体の正規化置き換え。コメントは残さない。`releases` は解決済み atom URL。
- 管理画面に `script` を出さない。ビルド成果物に管理 HTML を書かない。読む画面から管理へのリンクを足さない。
- serve は保存時も起動時もビルドしない。フィードを取りに行かない。
- 第一引数が無ければビルド。第一引数が `serve` なら管理プロセス。それ以外の第一引数は起動失敗。`--port` は serve 専用。
- 未ビルドの `/` は 200 で「タイムラインはまだビルドされていない」。`/manage.css` を参照。管理へのリンクなし。
- 衝突エラー文言: 「設定ファイルが他で変更されています」
- クエリ不正・無い名前の文言: 「そのウォッチ対象はありません」
- 最後の1件削除の文言: 「最後のウォッチ対象は削除できません」
- 不正 `action` の文言: 「不正な操作です」
- 書き出し失敗の文言: 「保存できませんでした」
- 既定テストはネットワークに出ない。スクリーンショットは取らない。外部ホストへは出ない。
- Python 3.11 以上。HTTP 取り込みの 15 秒・2 MiB は触らない。
- 公開サイトからの保存、DB、ログイン、`0.0.0.0`、自動ビルド、管理画面の JS は作らない。

## File structure

| Path | Responsibility |
|---|---|
| `src/libwatch/config.py` | 読み込みに加え、テキストからの parse、正規化 dump、原子的書き込み、SHA-256 |
| `src/libwatch/manage.py` | 未ビルドページ、管理 HTML、管理 CSS。script なし |
| `src/libwatch/serve.py` | `127.0.0.1` の HTTP、Origin 検査、GET/POST、CLI `serve_main` |
| `src/libwatch/__main__.py` | 引数なしはビルド、`serve` は `serve_main` |
| `src/libwatch/render.py` | 触らない |
| `src/libwatch/build.py` | 触らない |
| `src/libwatch/write.py` | 触らない |
| `tests/test_dump.py` | dump / hash / 原子的書き込み |
| `tests/test_cli.py` | 引数の振り分け |
| `tests/test_serve.py` | HTTP の読み書き。`127.0.0.1` のみ |
| `tests/test_render.py` | 触らない（タイムラインに管理リンクが無いことを今のテストが担保） |
| `README.md` | ローカルプレビューを `serve` に置き換え |

この表に無いアプリファイルを足さない。Node ツールチェーンを足さない。Flask 等は足さない。

## Task 1: ウォッチリスト YAML の正規化書き込み

**Files:**
- Modify: `src/libwatch/config.py`
- Create: `tests/test_dump.py`

**Interfaces:**

- `parse_watchlist(text: str) -> Watchlist` — 失敗は `ConfigError`。検証規則は今の `load_watchlist` と同じ。
- `load_watchlist(path: Path) -> Watchlist` — ファイルを UTF-8 で読んで `parse_watchlist` に渡す。ファイル IO のエラーメッセージは今のまま（パスを含む）。
- `dump_watchlist(watchlist: Watchlist) -> str` — UTF-8 向けテキスト。トップレベルは `targets` のみ。各件のキー順は `name`、あれば `blog`、あれば `releases`。無い任意キーは出さない。値は `WatchTarget` のまま（`releases` はすでに atom URL）。
- `write_watchlist(path: Path, text: str) -> None` — 同じディレクトリの一時ファイルに書いて `os.replace`。失敗時は一時ファイルを消し、既存の `path` を残す。
- `sha256_hex(data: bytes) -> str` — SHA-256 の小文字 hex。

- [ ] **Step 1: 失敗するテスト**

`tests/test_dump.py` を次の内容にする。

```python
import os
from pathlib import Path

import pytest
import yaml

from libwatch.config import (
    ConfigError,
    WatchTarget,
    Watchlist,
    dump_watchlist,
    load_watchlist,
    parse_watchlist,
    sha256_hex,
    write_watchlist,
)


def test_parse_watchlist_roundtrip_values() -> None:
    text = """\
targets:
  - name: " React "
    blog: https://react.dev/rss.xml#frag
    releases: https://github.com/facebook/react/releases
"""
    watchlist = parse_watchlist(text)
    dumped = dump_watchlist(watchlist)
    again = parse_watchlist(dumped)
    assert again.targets == watchlist.targets
    data = yaml.safe_load(dumped)
    assert set(data.keys()) == {"targets"}
    assert list(data["targets"][0].keys()) == ["name", "blog", "releases"]
    assert data["targets"][0]["name"] == "React"
    assert data["targets"][0]["blog"] == "https://react.dev/rss.xml"
    assert (
        data["targets"][0]["releases"]
        == "https://github.com/facebook/react/releases.atom"
    )
    assert "#frag" not in dumped
    assert "facebook/react/releases\n" not in dumped


def test_dump_omits_missing_optional_keys() -> None:
    watchlist = parse_watchlist(
        "targets:\n  - name: A\n    blog: https://example.com/feed.xml\n"
    )
    dumped = dump_watchlist(watchlist)
    data = yaml.safe_load(dumped)
    assert "releases" not in data["targets"][0]
    assert "blog" in data["targets"][0]


def test_dump_drops_comments() -> None:
    text = """\
# keep me
targets:
  - name: A
    blog: https://example.com/feed.xml
"""
    dumped = dump_watchlist(parse_watchlist(text))
    assert "keep me" not in dumped


def test_sha256_hex_of_raw_bytes() -> None:
    assert sha256_hex(b"abc") == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_write_watchlist_replaces_and_leaves_no_tmp(tmp_path: Path) -> None:
    path = tmp_path / "watchlist.yml"
    path.write_text("OLD\n", encoding="utf-8")
    write_watchlist(path, "targets:\n  - name: A\n    blog: https://example.com/a.xml\n")
    assert "name: A" in path.read_text(encoding="utf-8")
    leftovers = [p.name for p in tmp_path.iterdir() if p.name != "watchlist.yml"]
    assert leftovers == []


def test_write_watchlist_keeps_old_file_if_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "watchlist.yml"
    path.write_text("OLD\n", encoding="utf-8")
    original_replace = os.replace

    def boom(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
        raise OSError("nope")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        write_watchlist(path, "NEW\n")
    assert path.read_text(encoding="utf-8") == "OLD\n"
    monkeypatch.setattr(os, "replace", original_replace)
    leftovers = [
        p.name
        for p in tmp_path.iterdir()
        if p.name != "watchlist.yml" and not p.name.startswith(".")
    ]
    assert leftovers == []


def test_load_watchlist_uses_parse(tmp_path: Path) -> None:
    path = tmp_path / "watchlist.yml"
    path.write_text(
        "targets:\n  - name: A\n    blog: https://example.com/feed.xml\n",
        encoding="utf-8",
    )
    assert load_watchlist(path).targets[0].name == "A"


def test_parse_watchlist_rejects_empty() -> None:
    with pytest.raises(ConfigError):
        parse_watchlist("targets: []\n")
```

- [ ] **Step 2: 失敗を確認**

```bash
uv run python -m pytest tests/test_dump.py -q
```

`parse_watchlist` / `dump_watchlist` / `sha256_hex` / `write_watchlist` が無いため失敗する。

- [ ] **Step 3: 実装**

`src/libwatch/config.py` の先頭 import に `hashlib`、`os`、`tempfile` を足す。`load_watchlist` の YAML 以降を `parse_watchlist` に移す。ファイル IO と `parse_watchlist` 呼び出しだけを `load_watchlist` に残す。YAML 解析エラーは `ConfigError("invalid YAML in watchlist")` でよい（パス無し）。既存の `tests/test_config.py` はメッセージを固定していないので通す。

ファイル末尾に次を足す（既存の `_parse_target` 等は残す）。

```python
def parse_watchlist(text: str) -> Watchlist:
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError("invalid YAML in watchlist") from exc

    if not isinstance(data, dict):
        raise ConfigError("watchlist root must be a mapping")
    if set(data.keys()) != {"targets"}:
        raise ConfigError("watchlist root must contain only 'targets'")

    targets_raw = data["targets"]
    if not isinstance(targets_raw, list) or len(targets_raw) == 0:
        raise ConfigError("'targets' must be a non-empty list")

    seen_names: set[str] = set()
    targets: list[WatchTarget] = []
    for item in targets_raw:
        targets.append(_parse_target(item, seen_names))
    return Watchlist(targets=tuple(targets))


def dump_watchlist(watchlist: Watchlist) -> str:
    items: list[dict[str, str]] = []
    for target in watchlist.targets:
        item: dict[str, str] = {"name": target.name}
        if target.blog is not None:
            item["blog"] = target.blog
        if target.releases is not None:
            item["releases"] = target.releases
        items.append(item)
    dumped = yaml.safe_dump(
        {"targets": items},
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )
    if not dumped.endswith("\n"):
        dumped += "\n"
    return dumped


def write_watchlist(path: Path, text: str) -> None:
    directory = path.parent
    directory.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".watchlist.", suffix=".tmp", dir=directory)
    tmp_path = Path(tmp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp_path, path)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
```

`load_watchlist` は読めた `text` を `return parse_watchlist(text)` する。`yaml.safe_load` の重複は `parse_watchlist` 側だけにする。

- [ ] **Step 4: テストを通す**

```bash
uv run python -m pytest -q
```

全テストがネットワーク無しで緑。

- [ ] **Step 5: コミット**

```bash
git add src/libwatch/config.py tests/test_dump.py
git commit -m "$(cat <<'EOF'
ウォッチリスト YAML を正規化して原子的に書き出せるようにする。

EOF
)"
```

## Task 2: localhost の管理プロセス

**Files:**
- Create: `src/libwatch/manage.py`
- Create: `src/libwatch/serve.py`
- Modify: `src/libwatch/__main__.py`
- Create: `tests/test_cli.py`
- Create: `tests/test_serve.py`

**Interfaces:**

- `libwatch.__main__.main(argv: list[str] | None = None) -> int` — `argv is None` なら `sys.argv[1:]`。空なら `build_main()`。`argv[0] == "serve"` なら `serve_main(argv[1:])`。それ以外は stderr に `unknown command: {argv[0]}` を書いて 1。
- `serve_main(argv: list[str], *, cwd: Path | None = None, stdout: TextIO | None = None, stderr: TextIO | None = None) -> int` — `cwd` 既定 `Path.cwd()`。`--port` だけ認める。既定 8000。整数でない・範囲外・未知引数は stderr に理由を書いて 1。bind 失敗も 1。成功時は待って 0（テストは `make_server` を使う）。
- `make_server(cwd: Path, port: int) -> HTTPServer` — `("127.0.0.1", port)`。`port == 0` はテスト用に OS が空きポートを付ける。CLI は 0 を渡さない。
- `MANAGE_CSS: str` — タイムラインと同じトークン（`--text` / `--bg` / `--muted` / `--line` / `--accent`、`68ch`、`color-scheme: light dark`、`box-shadow` なし）。フォーム用の規則を足してよい。
- `render_unbuilt_html() -> str`
- `render_manage_html(...)` — 後述の Page。

HTTP 規則は spec の Data flow / Error handling どおり。テストは `http.client.HTTPConnection("127.0.0.1", port)` を使う。外部ホスト名には接続しない。

管理 HTML のボタン文言は「追加」「保存」「削除する」。キャンセルは `a href="/manage"`。表示ラベルは「名前」「公式ブログ」「リリースノート」。

- [ ] **Step 1: 失敗するテスト**

`tests/test_cli.py`:

```python
from io import StringIO

from libwatch.__main__ import main


def test_no_args_runs_build(monkeypatch) -> None:
    called = {"n": 0}

    def fake_build() -> int:
        called["n"] += 1
        return 0

    monkeypatch.setattr("libwatch.__main__.build_main", fake_build)
    assert main([]) == 0
    assert called["n"] == 1


def test_unknown_command_is_error(capsys) -> None:
    assert main(["build"]) == 1
    captured = capsys.readouterr()
    assert "unknown command: build" in captured.err


def test_serve_rejects_bad_port(monkeypatch) -> None:
    from libwatch.serve import serve_main

    stderr = StringIO()
    assert serve_main(["--port", "0"], stderr=stderr) == 1
    assert serve_main(["--port", "foo"], stderr=stderr) == 1
    assert serve_main(["--host", "127.0.0.1"], stderr=stderr) == 1
    assert serve_main(["--port", "8000", "extra"], stderr=stderr) == 1
```

`tests/test_serve.py`:

```python
from __future__ import annotations

import socket
import threading
from collections.abc import Iterator
from http.client import HTTPConnection
from pathlib import Path
from urllib.parse import urlencode

import pytest
import yaml

from libwatch.config import load_watchlist, sha256_hex
from libwatch.serve import make_server


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture
def cwd(tmp_path: Path) -> Path:
    (tmp_path / "watchlist.yml").write_text(
        "targets:\n  - name: Python\n    blog: https://example.com/python.xml\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def port(cwd: Path) -> Iterator[int]:
    chosen = _free_port()
    httpd = make_server(cwd, chosen)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield chosen
    finally:
        httpd.shutdown()
        thread.join(timeout=5)
        httpd.server_close()


def _conn(port: int) -> HTTPConnection:
    return HTTPConnection("127.0.0.1", port, timeout=5)


def _hash(cwd: Path) -> str:
    return sha256_hex((cwd / "watchlist.yml").read_bytes())


def test_unbuilt_root_is_200(port: int) -> None:
    conn = _conn(port)
    conn.request("GET", "/")
    resp = conn.getresponse()
    body = resp.read().decode("utf-8")
    conn.close()
    assert resp.status == 200
    assert "タイムラインはまだビルドされていない" in body
    assert 'href="/manage.css"' in body
    assert "/manage\"" not in body.replace('href="/manage.css"', "")
    assert "<script" not in body
    assert "<h1>ライブラリ更新ウォッチ</h1>" in body


def test_built_root_is_site_index(cwd: Path, port: int) -> None:
    site = cwd / "site"
    site.mkdir()
    (site / "index.html").write_text(
        "<!DOCTYPE html><html lang=\"ja\"><body><h1>ライブラリ更新ウォッチ</h1></body></html>",
        encoding="utf-8",
    )
    conn = _conn(port)
    conn.request("GET", "/")
    resp = conn.getresponse()
    body = resp.read().decode("utf-8")
    conn.close()
    assert resp.status == 200
    assert "ライブラリ更新ウォッチ" in body
    assert "タイムラインはまだビルドされていない" not in body
    assert 'href="/manage"' not in body


def test_get_manage_lists_and_add_form_without_delete(cwd: Path, port: int) -> None:
    before = (cwd / "watchlist.yml").read_bytes()
    conn = _conn(port)
    conn.request("GET", "/manage")
    resp = conn.getresponse()
    body = resp.read().decode("utf-8")
    conn.close()
    assert resp.status == 200
    assert "<title>ウォッチ対象</title>" in body
    assert "Python" in body
    assert 'name="action" value="add"' in body
    assert "削除" not in body
    assert 'href="/"' in body
    assert "<script" not in body
    assert (cwd / "watchlist.yml").read_bytes() == before


def test_edit_query_does_not_write(cwd: Path, port: int) -> None:
    before = (cwd / "watchlist.yml").read_bytes()
    conn = _conn(port)
    conn.request("GET", "/manage?edit=Python")
    resp = conn.getresponse()
    body = resp.read().decode("utf-8")
    conn.close()
    assert resp.status == 200
    assert 'name="action" value="edit"' in body
    assert 'name="original_name" value="Python"' in body
    assert (cwd / "watchlist.yml").read_bytes() == before


def test_confirm_delete_last_item_is_error(cwd: Path, port: int) -> None:
    conn = _conn(port)
    conn.request("GET", "/manage?confirm_delete=Python")
    resp = conn.getresponse()
    body = resp.read().decode("utf-8")
    conn.close()
    assert resp.status == 200
    assert "最後のウォッチ対象は削除できません" in body
    assert "削除しますか" not in body


def test_unknown_edit_is_list_error(cwd: Path, port: int) -> None:
    conn = _conn(port)
    conn.request("GET", "/manage?edit=Nope")
    resp = conn.getresponse()
    body = resp.read().decode("utf-8")
    conn.close()
    assert "そのウォッチ対象はありません" in body
    assert 'name="action" value="edit"' not in body


def test_post_add_appends_and_redirects(cwd: Path, port: int) -> None:
    digest = _hash(cwd)
    body = urlencode(
        {
            "action": "add",
            "hash": digest,
            "name": "React",
            "blog": "",
            "releases": "https://github.com/facebook/react/releases",
        }
    )
    conn = _conn(port)
    conn.request(
        "POST",
        "/manage",
        body=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": f"http://127.0.0.1:{port}",
        },
    )
    resp = conn.getresponse()
    resp.read()
    conn.close()
    assert resp.status == 303
    assert resp.getheader("Location") == "/manage"
    names = [t.name for t in load_watchlist(cwd / "watchlist.yml").targets]
    assert names == ["Python", "React"]
    dumped = yaml.safe_load((cwd / "watchlist.yml").read_text(encoding="utf-8"))
    assert dumped["targets"][1]["releases"] == (
        "https://github.com/facebook/react/releases.atom"
    )


def test_post_edit_renames_in_place(cwd: Path, port: int) -> None:
    (cwd / "watchlist.yml").write_text(
        "\n".join(
            [
                "targets:",
                "  - name: A",
                "    blog: https://example.com/a.xml",
                "  - name: B",
                "    blog: https://example.com/b.xml",
                "",
            ]
        ),
        encoding="utf-8",
    )
    digest = _hash(cwd)
    body = urlencode(
        {
            "action": "edit",
            "hash": digest,
            "original_name": "A",
            "name": "Alpha",
            "blog": "https://example.com/a.xml",
            "releases": "",
        }
    )
    conn = _conn(port)
    conn.request(
        "POST",
        "/manage",
        body=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": f"http://127.0.0.1:{port}",
        },
    )
    resp = conn.getresponse()
    resp.read()
    conn.close()
    assert resp.status == 303
    names = [t.name for t in load_watchlist(cwd / "watchlist.yml").targets]
    assert names == ["Alpha", "B"]


def test_post_delete_last_rejected(cwd: Path, port: int) -> None:
    digest = _hash(cwd)
    before = (cwd / "watchlist.yml").read_bytes()
    body = urlencode({"action": "delete", "hash": digest, "name": "Python"})
    conn = _conn(port)
    conn.request(
        "POST",
        "/manage",
        body=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": f"http://127.0.0.1:{port}",
        },
    )
    resp = conn.getresponse()
    page = resp.read().decode("utf-8")
    conn.close()
    assert resp.status == 200
    assert "最後のウォッチ対象は削除できません" in page
    assert (cwd / "watchlist.yml").read_bytes() == before


def test_stale_hash_rejected(cwd: Path, port: int) -> None:
    body = urlencode(
        {
            "action": "add",
            "hash": "00" * 32,
            "name": "React",
            "blog": "https://example.com/r.xml",
            "releases": "",
        }
    )
    before = (cwd / "watchlist.yml").read_bytes()
    conn = _conn(port)
    conn.request(
        "POST",
        "/manage",
        body=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": f"http://127.0.0.1:{port}",
        },
    )
    resp = conn.getresponse()
    page = resp.read().decode("utf-8")
    conn.close()
    assert resp.status == 200
    assert "設定ファイルが他で変更されています" in page
    assert (cwd / "watchlist.yml").read_bytes() == before


def test_origin_required(cwd: Path, port: int) -> None:
    digest = _hash(cwd)
    body = urlencode(
        {
            "action": "add",
            "hash": digest,
            "name": "X",
            "blog": "https://example.com/x.xml",
            "releases": "",
        }
    )
    before = (cwd / "watchlist.yml").read_bytes()
    conn = _conn(port)
    conn.request(
        "POST",
        "/manage",
        body=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    resp = conn.getresponse()
    resp.read()
    conn.close()
    assert resp.status == 403
    assert (cwd / "watchlist.yml").read_bytes() == before

    conn = _conn(port)
    conn.request(
        "POST",
        "/manage",
        body=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": f"http://localhost:{port}",
        },
    )
    resp = conn.getresponse()
    resp.read()
    conn.close()
    assert resp.status == 403
    assert (cwd / "watchlist.yml").read_bytes() == before


def test_site_manage_html_does_not_win(cwd: Path, port: int) -> None:
    site = cwd / "site"
    site.mkdir()
    (site / "manage.html").write_text("STATIC", encoding="utf-8")
    conn = _conn(port)
    conn.request("GET", "/manage")
    resp = conn.getresponse()
    body = resp.read().decode("utf-8")
    conn.close()
    assert "STATIC" not in body
    assert "<title>ウォッチ対象</title>" in body


def test_put_is_405(cwd: Path, port: int) -> None:
    before = (cwd / "watchlist.yml").read_bytes()
    conn = _conn(port)
    conn.request("PUT", "/manage")
    resp = conn.getresponse()
    resp.read()
    conn.close()
    assert resp.status == 405
    assert (cwd / "watchlist.yml").read_bytes() == before


def test_duplicate_name_keeps_input(cwd: Path, port: int) -> None:
    digest = _hash(cwd)
    before = (cwd / "watchlist.yml").read_bytes()
    body = urlencode(
        {
            "action": "add",
            "hash": digest,
            "name": "Python",
            "blog": "https://example.com/other.xml",
            "releases": "",
        }
    )
    conn = _conn(port)
    conn.request(
        "POST",
        "/manage",
        body=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": f"http://127.0.0.1:{port}",
        },
    )
    resp = conn.getresponse()
    page = resp.read().decode("utf-8")
    conn.close()
    assert resp.status == 200
    assert 'value="Python"' in page
    assert 'value="https://example.com/other.xml"' in page
    assert (cwd / "watchlist.yml").read_bytes() == before


def test_two_targets_show_delete_and_post_removes(cwd: Path, port: int) -> None:
    (cwd / "watchlist.yml").write_text(
        "targets:\n"
        "  - name: A\n    blog: https://example.com/a.xml\n"
        "  - name: B\n    blog: https://example.com/b.xml\n",
        encoding="utf-8",
    )
    site = cwd / "site"
    site.mkdir()
    (site / "index.html").write_text("KEEP", encoding="utf-8")
    conn = _conn(port)
    conn.request("GET", "/manage")
    page = conn.getresponse().read().decode("utf-8")
    conn.close()
    assert "confirm_delete=A" in page
    assert "confirm_delete=B" in page
    digest = _hash(cwd)
    body = urlencode({"action": "delete", "hash": digest, "name": "A"})
    conn = _conn(port)
    conn.request(
        "POST",
        "/manage",
        body=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": f"http://127.0.0.1:{port}",
        },
    )
    resp = conn.getresponse()
    resp.read()
    conn.close()
    assert resp.status == 303
    names = [t.name for t in load_watchlist(cwd / "watchlist.yml").targets]
    assert names == ["B"]
    assert (site / "index.html").read_text(encoding="utf-8") == "KEEP"
```

- [ ] **Step 2: 失敗を確認**

```bash
uv run python -m pytest tests/test_cli.py tests/test_serve.py -q
```

`main` / `make_server` が無いため失敗する。

- [ ] **Step 3: 実装**

`src/libwatch/__main__.py` を次にする。`python -m libwatch` のときだけ `main()` する。pytest が `from libwatch.__main__ import main` してもプロセスを終えない。

```python
from __future__ import annotations

import sys

from libwatch.build import build_main
from libwatch.serve import serve_main


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        return build_main()
    if args[0] == "serve":
        return serve_main(args[1:])
    print(f"unknown command: {args[0]}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

`src/libwatch/manage.py` は次を満たす HTML 文字列を返す。`html.escape(..., quote=True)` を名前・URL・エラー・hidden 値に使う。`script` を出さない。

- `render_unbuilt_html()`: spec の未ビルド `/` の木。title と h1 は「ライブラリ更新ウォッチ」。本文は「タイムラインはまだビルドされていない」。`link href="/manage.css"`。管理への `a` は出さない。
- `render_manage_error_html(message: str)`: ヘッダ（h1「ウォッチ対象」、`a href="/"`「タイムライン」）とエラーの `p` だけ。フォームなし。
- `render_manage_html(*, targets, file_hash, error=None, mode="list", focus_name=None, form_name="", form_blog="", form_releases="")`:
  - `mode == "confirm"`: 確認専用。`p`「{name} を削除しますか」。POST hidden `action=delete`, `hash`, `name`。ボタン「削除する」。キャンセル `href="/manage"`。一覧・追加・編集なし。
  - それ以外: 追加フォーム（hidden `action=add`, `hash`。フィールド name/blog/releases。ボタン「追加」）。`mode == "edit"` のとき `focus_name` の件だけ編集フォーム（hidden `action=edit`, `hash`, `original_name`。ボタン「保存」。キャンセル `href="/manage"`）。他件は表示と「編集」リンク `href="/manage?edit={quote(name, safe='')}"`。`len(targets) >= 2` のときだけ「削除」リンク `href="/manage?confirm_delete={quote(name, safe='')}"`。
  - `mode == "list"` で検証失敗の入力を戻すときは追加フォームに `form_*` を入れる。
  - `mode == "edit"` で検証失敗のときは編集フォームに `form_*` を入れる。
- `MANAGE_CSS`: `src/libwatch/render.py` の `RENDER_CSS` と同じ `:root` と `body` / `header` / `h1` 規則に加え、`label { display: block; margin-top: 0.75rem; }`、`input { width: 100%; }`、`button { margin-top: 1rem; }`。`box-shadow` と `script` は出さない。

`src/libwatch/serve.py`:

- `MAX_POST_BYTES = 65536`
- `expected_origin(port: int) -> str` は `http://127.0.0.1:{port}`
- Origin ヘッダがあればその文字列だけを比較。無ければ `Referer` から `scheme://hostname:port`（ポート省略時は 80/443）を取り同じ文字列と比較。どちらも無ければ拒否。
- `Content-Type` は `;` より前を strip して lower が `application/x-www-form-urlencoded`
- パスは `urllib.parse.urlsplit` の path を unquote し、`/` で始まるよう正規化。`/manage` と `/manage/` は管理。`/manage.css` は CSS。それ以外は `cwd/site` 配下。`Path.resolve()` して `site.resolve()` の外なら 404。ディレクトリは 404。`index.html` は `/` だけ特別扱い（無ければ未ビルド HTML）。
- GET `/manage`: `watchlist.yml` をバイトで読む。UTF-8 / `parse_watchlist` 失敗なら `render_manage_error_html`（`ConfigError` の文字）。成功ならクエリを判定（両方ある・空・無い名前 → 「そのウォッチ対象はありません」で list。最後の1件の `confirm_delete` → 「最後のウォッチ対象は削除できません」で list。正規の confirm / edit / list）。
- POST `/manage`: spec の 1〜8。add は targets 末尾に dict を足して `yaml.safe_dump` → `parse_watchlist`。失敗なら 200 で追加フォームに入力を残す。edit は `original_name` の位置を置き換え、位置は変えない。delete は当該 name を除く。成功なら `dump_watchlist` + `write_watchlist` のあと 303。`write_watchlist` が例外なら既存ファイルを残し「保存できませんでした」。
- `make_server`: `HTTPServer(("127.0.0.1", port), Handler)`。Handler は `self.server.cwd` と `self.server.server_port` を使う。`log_message` は空実装。
- `serve_main`: `argparse` で `--port` のみ（`allow_abbrev=False`）。default 8000。1〜65535 以外は 1。`make_server(cwd, port)` のあと stdout に spec の2行を書いて `serve_forever()`。`OSError` は stderr に出して 1。
- POST `/` や POST `/manage.css` は 405。
- 2件以上の削除リンクが出ること。GET だけでは YAML バイトが変わらないこと。上のテストがカバーする。

`serve_main` がテストから bind しないよう、不正引数は `make_server` の前に return する。

- [ ] **Step 4: テストを通す**

```bash
uv run python -m pytest -q
```

全テストがネットワーク無しで緑。失敗したら `127.0.0.1` 以外に繋いでいないかを先に見る。

- [ ] **Step 5: コミット**

```bash
git add src/libwatch/manage.py src/libwatch/serve.py src/libwatch/__main__.py tests/test_cli.py tests/test_serve.py
git commit -m "$(cat <<'EOF'
localhost でウォッチ対象を追加・編集・削除できる管理プロセスを足す。

EOF
)"
```

## Task 3: README のローカルプレビューを serve に替える

**Files:**
- Modify: `README.md`

**Interfaces:** なし。アプリコードは触らない。

- [ ] **Step 1: README を直す**

`README.md` を次にする。コードブロック以外の説明も、読む成果物にサーバは不要であることと、管理・ローカルプレビューは `serve` であることを書く。`python -m http.server` は出さない。コピーした `site/` をサーバ無しで開いてよいことは残す。GitHub Actions には触れない。

```markdown
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
```

内側のフェンスが壊れないよう、実装時は README 全体を上記の本文にする。ネストした ``` は、内側をインデント 4 スペースのコードブロックにするか、外側だけを使う。この計画では「README の見出しとコマンドは上のブロックと同一の文言にする」を正とし、Markdown のフェンスはファイルとして妥当な入れ子（内側コマンドはインデント付きフェンスなし、またはチルダフェンス）にする。実装者は次の構造にする。

- 見出しと段落は上の文章どおり
- コマンドは単独の ` ```bash ` フェンス
- `http.server` という文字列はファイルに出さない
- `127.0.0.1:8000/manage` を含める
- 「サーバ無しでファイルとして開いても読めます」を含める

- [ ] **Step 2: 確認**

```bash
uv run python -m pytest -q
rg -n "http.server" README.md
```

テストは緑。`rg` は一致なし（終了コード 1）。`rg` が無ければ `grep -n "http.server" README.md` で一致なし。

- [ ] **Step 3: コミット**

```bash
git add README.md
git commit -m "$(cat <<'EOF'
ローカル確認と管理を libwatch serve に案内する。

EOF
)"
```
