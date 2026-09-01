from __future__ import annotations

import argparse
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import NoReturn, TextIO, cast
from urllib.parse import parse_qs, unquote, urlsplit

import yaml

from libwatch.config import (
    ConfigError,
    WatchTarget,
    Watchlist,
    dump_watchlist,
    parse_watchlist,
    sha256_hex,
    write_watchlist,
)
from libwatch.manage import (
    MANAGE_CSS,
    render_manage_error_html,
    render_manage_html,
    render_unbuilt_html,
)


MAX_POST_BYTES = 65536
CONFLICT_ERROR = "設定ファイルが他で変更されています"
UNKNOWN_TARGET_ERROR = "そのウォッチ対象はありません"
LAST_TARGET_ERROR = "最後のウォッチ対象は削除できません"
INVALID_ACTION_ERROR = "不正な操作です"
SAVE_ERROR = "保存できませんでした"


class WatchlistHTTPServer(HTTPServer):
    cwd: Path


def expected_origin(port: int) -> str:
    return f"http://127.0.0.1:{port}"


def make_server(cwd: Path, port: int) -> HTTPServer:
    httpd = WatchlistHTTPServer(("127.0.0.1", port), _Handler)
    httpd.cwd = cwd
    return httpd


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        try:
            path, query = _request_path(self.path)
        except ValueError:
            self._send_text(404, "Not Found\n")
            return

        if path == "/manage.css":
            self._send_text(200, MANAGE_CSS, content_type="text/css; charset=utf-8")
        elif path in {"/manage", "/manage/"}:
            self._get_manage(query)
        elif path == "/":
            self._get_root()
        else:
            self._get_static(path)

    def do_POST(self) -> None:
        try:
            path, _ = _request_path(self.path)
        except ValueError:
            self._method_not_allowed()
            return

        if path not in {"/manage", "/manage/"}:
            self._method_not_allowed()
            return
        if not self._origin_allowed():
            self._send_text(403, "Forbidden\n")
            return

        length = self._content_length()
        if length is None or length > MAX_POST_BYTES:
            self._send_text(400, "Bad Request\n")
            return
        if not self._is_form_content_type():
            self._send_text(400, "Bad Request\n")
            return

        body = self.rfile.read(length)
        if len(body) != length:
            self._send_text(400, "Bad Request\n")
            return
        try:
            form = parse_qs(body.decode("utf-8"), keep_blank_values=True)
        except (UnicodeDecodeError, ValueError):
            self._send_text(400, "Bad Request\n")
            return

        config_path = self._config_path()
        try:
            snapshot, watchlist = _read_watchlist(config_path)
        except ConfigError as exc:
            self._send_html(200, render_manage_error_html(str(exc)))
            return

        file_hash = sha256_hex(snapshot)
        if _form_value(form, "hash") != file_hash:
            self._send_manage_page(watchlist, file_hash, error=CONFLICT_ERROR)
            return

        action = _form_value(form, "action")
        if action not in {"add", "edit", "delete"}:
            self._send_manage_page(watchlist, file_hash, error=INVALID_ACTION_ERROR)
            return

        if action == "add":
            self._post_add(form, snapshot, watchlist, file_hash)
        elif action == "edit":
            self._post_edit(form, snapshot, watchlist, file_hash)
        else:
            self._post_delete(form, snapshot, watchlist, file_hash)

    def do_HEAD(self) -> None:
        self._method_not_allowed()

    def do_PUT(self) -> None:
        self._method_not_allowed()

    def do_DELETE(self) -> None:
        self._method_not_allowed()

    def do_PATCH(self) -> None:
        self._method_not_allowed()

    def do_OPTIONS(self) -> None:
        self._method_not_allowed()

    def do_TRACE(self) -> None:
        self._method_not_allowed()

    def do_CONNECT(self) -> None:
        self._method_not_allowed()

    def __getattr__(self, name: str):
        if name.startswith("do_"):
            return self._method_not_allowed
        raise AttributeError(name)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _get_root(self) -> None:
        index = _safe_site_file(self._cwd(), "/index.html")
        if index is None:
            self._send_html(200, render_unbuilt_html())
            return
        try:
            body = index.read_bytes()
        except (OSError, ValueError):
            self._send_text(404, "Not Found\n")
            return
        self._send_bytes(200, body, content_type="text/html; charset=utf-8")

    def _get_static(self, path: str) -> None:
        file_path = _safe_site_file(self._cwd(), path)
        if file_path is None:
            self._send_text(404, "Not Found\n")
            return
        try:
            body = file_path.read_bytes()
        except (OSError, ValueError):
            self._send_text(404, "Not Found\n")
            return
        self._send_bytes(200, body, content_type=_content_type(file_path))

    def _get_manage(self, query: str) -> None:
        config_path = self._config_path()
        try:
            snapshot, watchlist = _read_watchlist(config_path)
        except ConfigError as exc:
            self._send_html(200, render_manage_error_html(str(exc)))
            return

        file_hash = sha256_hex(snapshot)
        try:
            params = parse_qs(query, keep_blank_values=True)
        except ValueError:
            self._send_manage_page(watchlist, file_hash, error=UNKNOWN_TARGET_ERROR)
            return

        has_edit = "edit" in params
        has_delete = "confirm_delete" in params
        if has_edit and has_delete:
            self._send_manage_page(watchlist, file_hash, error=UNKNOWN_TARGET_ERROR)
            return

        if has_delete:
            name = _query_value(params, "confirm_delete")
            target = _find_target(watchlist, name)
            if name is None or target is None:
                self._send_manage_page(
                    watchlist, file_hash, error=UNKNOWN_TARGET_ERROR
                )
            elif len(watchlist.targets) == 1:
                self._send_manage_page(watchlist, file_hash, error=LAST_TARGET_ERROR)
            else:
                self._send_manage_page(
                    watchlist,
                    file_hash,
                    mode="confirm",
                    focus_name=target.name,
                )
            return

        if has_edit:
            name = _query_value(params, "edit")
            target = _find_target(watchlist, name)
            if name is None or target is None:
                self._send_manage_page(
                    watchlist, file_hash, error=UNKNOWN_TARGET_ERROR
                )
            else:
                self._send_manage_page(
                    watchlist,
                    file_hash,
                    mode="edit",
                    focus_name=target.name,
                    form_name=target.name,
                    form_blog=target.blog or "",
                    form_releases=target.releases or "",
                )
            return

        self._send_manage_page(watchlist, file_hash)

    def _post_add(
        self,
        form: dict[str, list[str]],
        snapshot: bytes,
        watchlist: Watchlist,
        file_hash: str,
    ) -> None:
        name = _form_value(form, "name")
        blog = _form_value(form, "blog")
        releases = _form_value(form, "releases")
        try:
            candidate = _candidate_with_added_target(
                watchlist,
                name=name,
                blog=blog,
                releases=releases,
            )
        except ConfigError as exc:
            self._send_manage_page(
                watchlist,
                file_hash,
                error=str(exc),
                form_name=name,
                form_blog=blog,
                form_releases=releases,
            )
            return

        self._save_candidate(
            snapshot,
            watchlist,
            candidate,
            file_hash,
            form_name=name,
            form_blog=blog,
            form_releases=releases,
        )

    def _post_edit(
        self,
        form: dict[str, list[str]],
        snapshot: bytes,
        watchlist: Watchlist,
        file_hash: str,
    ) -> None:
        original_name = _form_value(form, "original_name")
        target = _find_target(watchlist, original_name)
        if target is None:
            self._send_manage_page(watchlist, file_hash, error=UNKNOWN_TARGET_ERROR)
            return

        name = _form_value(form, "name")
        blog = _form_value(form, "blog")
        releases = _form_value(form, "releases")
        try:
            candidate = _candidate_with_replaced_target(
                watchlist,
                original_name=original_name,
                name=name,
                blog=blog,
                releases=releases,
            )
        except ConfigError as exc:
            self._send_manage_page(
                watchlist,
                file_hash,
                error=str(exc),
                mode="edit",
                focus_name=target.name,
                form_name=name,
                form_blog=blog,
                form_releases=releases,
            )
            return

        self._save_candidate(
            snapshot,
            watchlist,
            candidate,
            file_hash,
            mode="edit",
            focus_name=target.name,
            form_name=name,
            form_blog=blog,
            form_releases=releases,
        )

    def _post_delete(
        self,
        form: dict[str, list[str]],
        snapshot: bytes,
        watchlist: Watchlist,
        file_hash: str,
    ) -> None:
        name = _form_value(form, "name")
        target = _find_target(watchlist, name)
        if target is None:
            self._send_manage_page(watchlist, file_hash, error=UNKNOWN_TARGET_ERROR)
            return
        if len(watchlist.targets) == 1:
            self._send_manage_page(watchlist, file_hash, error=LAST_TARGET_ERROR)
            return

        candidate = Watchlist(tuple(t for t in watchlist.targets if t.name != name))
        self._save_candidate(snapshot, watchlist, candidate, file_hash)

    def _save_candidate(
        self,
        snapshot: bytes,
        watchlist: Watchlist,
        candidate: Watchlist,
        file_hash: str,
        *,
        mode: str = "list",
        focus_name: str | None = None,
        form_name: str = "",
        form_blog: str = "",
        form_releases: str = "",
    ) -> None:
        config_path = self._config_path()
        try:
            latest = config_path.read_bytes()
        except (OSError, ValueError) as exc:
            self._send_html(200, render_manage_error_html(str(exc)))
            return

        if latest != snapshot:
            try:
                latest_watchlist = _parse_watchlist_bytes(latest, config_path)
            except ConfigError as exc:
                self._send_html(200, render_manage_error_html(str(exc)))
            else:
                self._send_manage_page(
                    latest_watchlist,
                    sha256_hex(latest),
                    error=CONFLICT_ERROR,
                )
            return

        try:
            write_watchlist(config_path, dump_watchlist(candidate))
        except Exception:
            self._send_manage_page(
                watchlist,
                file_hash,
                error=SAVE_ERROR,
                mode=mode,
                focus_name=focus_name,
                form_name=form_name,
                form_blog=form_blog,
                form_releases=form_releases,
            )
            return

        self._send_bytes(303, b"", headers={"Location": "/manage"})

    def _send_manage_page(
        self,
        watchlist: Watchlist,
        file_hash: str,
        *,
        error: str | None = None,
        mode: str = "list",
        focus_name: str | None = None,
        form_name: str = "",
        form_blog: str = "",
        form_releases: str = "",
    ) -> None:
        self._send_html(
            200,
            render_manage_html(
                targets=watchlist.targets,
                file_hash=file_hash,
                error=error,
                mode=mode,
                focus_name=focus_name,
                form_name=form_name,
                form_blog=form_blog,
                form_releases=form_releases,
            ),
        )

    def _origin_allowed(self) -> bool:
        expected = expected_origin(self._httpd().server_port)
        origin = self.headers.get("Origin")
        if origin is not None:
            return origin == expected

        referer = self.headers.get("Referer")
        if referer is None:
            return False
        return _referer_origin(referer) == expected

    def _content_length(self) -> int | None:
        value = self.headers.get("Content-Length")
        if value is None:
            return None
        try:
            length = int(value, 10)
        except ValueError:
            return None
        if length < 0:
            return None
        return length

    def _is_form_content_type(self) -> bool:
        value = self.headers.get("Content-Type", "")
        return value.split(";", 1)[0].strip().lower() == (
            "application/x-www-form-urlencoded"
        )

    def _cwd(self) -> Path:
        return self._httpd().cwd

    def _httpd(self) -> WatchlistHTTPServer:
        return cast(WatchlistHTTPServer, self.server)

    def _config_path(self) -> Path:
        return self._cwd() / "watchlist.yml"

    def _send_html(self, status: int, body: str) -> None:
        self._send_text(status, body, content_type="text/html; charset=utf-8")

    def _send_text(
        self,
        status: int,
        body: str,
        *,
        content_type: str = "text/plain; charset=utf-8",
    ) -> None:
        self._send_bytes(status, body.encode("utf-8"), content_type=content_type)

    def _send_bytes(
        self,
        status: int,
        body: bytes,
        *,
        content_type: str = "text/plain; charset=utf-8",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if headers is not None:
            for key, value in headers.items():
                self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _method_not_allowed(self) -> None:
        self._send_text(
            405,
            "Method Not Allowed\n",
            content_type="text/plain; charset=utf-8",
        )


class _ServeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise argparse.ArgumentError(None, message)


def serve_main(
    argv: list[str],
    *,
    cwd: Path | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    out = sys.stdout if stdout is None else stdout
    err = sys.stderr if stderr is None else stderr
    parser = _ServeArgumentParser(
        prog="python -m libwatch serve",
        allow_abbrev=False,
        add_help=False,
    )
    parser.add_argument("--port", type=int, default=8000)
    try:
        args = parser.parse_args(argv)
    except argparse.ArgumentError as exc:
        print(str(exc), file=err)
        return 1

    if not 1 <= args.port <= 65535:
        print("port must be between 1 and 65535", file=err)
        return 1

    root = Path.cwd() if cwd is None else cwd
    try:
        httpd = make_server(root, args.port)
    except OSError as exc:
        print(str(exc), file=err)
        return 1

    try:
        actual_port = httpd.server_port
        print(f"http://127.0.0.1:{actual_port}/", file=out)
        print(f"http://127.0.0.1:{actual_port}/manage", file=out)
        out.flush()
        httpd.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        httpd.server_close()
    return 0


def _request_path(request_target: str) -> tuple[str, str]:
    parsed = urlsplit(request_target)
    path = unquote(parsed.path)
    if not path.startswith("/"):
        path = "/" + path
    return path, parsed.query


def _safe_site_file(cwd: Path, request_path: str) -> Path | None:
    try:
        site = (cwd / "site").resolve()
        candidate = (cwd / "site" / request_path.lstrip("/")).resolve()
        if candidate == site or not candidate.is_relative_to(site):
            return None
        if not candidate.is_file():
            return None
    except (OSError, RuntimeError, ValueError):
        return None
    return candidate


def _content_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    if guessed is None:
        return "application/octet-stream"
    if guessed.startswith("text/"):
        return f"{guessed}; charset=utf-8"
    return guessed


def _referer_origin(referer: str) -> str | None:
    try:
        parsed = urlsplit(referer)
        if parsed.scheme not in {"http", "https"}:
            return None
        if parsed.username is not None or parsed.password is not None:
            return None
        hostname = parsed.hostname
        if not hostname:
            return None
        port = parsed.port
    except ValueError:
        return None

    if port is None:
        port = 80 if parsed.scheme == "http" else 443
    return f"{parsed.scheme}://{hostname}:{port}"


def _read_watchlist(path: Path) -> tuple[bytes, Watchlist]:
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise ConfigError(f"watchlist not found: {path}") from exc
    except OSError as exc:
        raise ConfigError(f"cannot read watchlist: {path}") from exc
    return raw, _parse_watchlist_bytes(raw, path)


def _parse_watchlist_bytes(raw: bytes, path: Path) -> Watchlist:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ConfigError(f"watchlist is not valid UTF-8: {path}") from exc
    return parse_watchlist(text)


def _query_value(params: dict[str, list[str]], key: str) -> str | None:
    values = params.get(key)
    if values is None or len(values) != 1 or values[0] == "":
        return None
    return values[0]


def _form_value(form: dict[str, list[str]], key: str) -> str:
    values = form.get(key)
    if not values:
        return ""
    return values[0]


def _find_target(watchlist: Watchlist, name: str | None) -> WatchTarget | None:
    if name is None:
        return None
    return next((target for target in watchlist.targets if target.name == name), None)


def _target_mapping(target: WatchTarget) -> dict[str, str]:
    item: dict[str, str] = {"name": target.name}
    if target.blog is not None:
        item["blog"] = target.blog
    if target.releases is not None:
        item["releases"] = target.releases
    return item


def _raw_target_mapping(name: str, blog: str, releases: str) -> dict[str, str]:
    return {"name": name, "blog": blog, "releases": releases}


def _parse_candidate(items: list[dict[str, str]]) -> Watchlist:
    raw = yaml.safe_dump(
        {"targets": items},
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )
    return parse_watchlist(raw)


def _candidate_with_added_target(
    watchlist: Watchlist,
    *,
    name: str,
    blog: str,
    releases: str,
) -> Watchlist:
    items = [_target_mapping(target) for target in watchlist.targets]
    items.append(_raw_target_mapping(name, blog, releases))
    return _parse_candidate(items)


def _candidate_with_replaced_target(
    watchlist: Watchlist,
    *,
    original_name: str,
    name: str,
    blog: str,
    releases: str,
) -> Watchlist:
    items: list[dict[str, str]] = []
    for target in watchlist.targets:
        if target.name == original_name:
            items.append(_raw_target_mapping(name, blog, releases))
        else:
            items.append(_target_mapping(target))
    return _parse_candidate(items)
