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
