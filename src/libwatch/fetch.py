from __future__ import annotations

import socket
from collections.abc import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import HTTPErrorProcessor, HTTPRedirectHandler, Request, build_opener

MAX_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 5
REDIRECT_CODES = frozenset({301, 302, 303, 307, 308})
USER_AGENT = "LibWatch/0.1"
TIMEOUT = 15


class FetchError(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class _PassThroughHTTPErrorProcessor(HTTPErrorProcessor):
    def http_response(self, request, response):  # type: ignore[no-untyped-def]
        return response

    https_response = http_response


def _default_urlopen(req: Request, timeout: float | None = None) -> object:
    opener = build_opener(_PassThroughHTTPErrorProcessor)
    opener.handlers = [
        h for h in opener.handlers if not isinstance(h, HTTPRedirectHandler)
    ]
    return opener.open(req, timeout=timeout)


def fetch_feed(
    url: str,
    *,
    urlopen: Callable[..., object] | None = None,
) -> bytes:
    open_url = urlopen if urlopen is not None else _default_urlopen
    current = url
    redirects = 0

    while True:
        req = Request(current, headers={"User-Agent": USER_AGENT})
        try:
            opened = open_url(req, timeout=TIMEOUT)
        except TimeoutError as exc:
            raise FetchError("timeout") from exc
        except HTTPError as exc:
            raise FetchError(f"HTTP {exc.code}") from exc
        except URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                raise FetchError("timeout") from exc
            raise FetchError("connection failed") from exc

        try:
            with opened as resp:  # type: ignore[union-attr]
                code = resp.getcode()
                if code in REDIRECT_CODES:
                    if redirects >= MAX_REDIRECTS:
                        raise FetchError("too many redirects")
                    location = resp.headers.get("Location")
                    if not location:
                        raise FetchError("connection failed")
                    current = urljoin(current, location)
                    redirects += 1
                    continue
                if code != 200:
                    raise FetchError(f"HTTP {code}")
                content_length = resp.headers.get("Content-Length")
                if content_length is not None and int(content_length) > MAX_BYTES:
                    raise FetchError("too large")
                data = resp.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES:
                    raise FetchError("too large")
                return data
        except TimeoutError as exc:
            raise FetchError("timeout") from exc
