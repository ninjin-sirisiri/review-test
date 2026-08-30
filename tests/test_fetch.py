from email.message import Message
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

from libwatch.fetch import FetchError, fetch_feed


class FakeResp:
    def __init__(self, data: bytes, status: int = 200, headers: dict[str, str] | None = None):
        self._data = data
        self._status = status
        self.headers = Message()
        for key, value in (headers or {}).items():
            self.headers[key] = value

    def getcode(self) -> int:
        return self._status

    def read(self, n: int = -1) -> bytes:
        if n < 0:
            return self._data
        return self._data[:n]

    def __enter__(self) -> "FakeResp":
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_ok_and_user_agent() -> None:
    seen: list[Request] = []

    def urlopen(req: Request, timeout: float | None = None) -> FakeResp:
        seen.append(req)
        assert timeout == 15
        return FakeResp(b"<rss/>")

    assert fetch_feed("https://example.com/feed.xml", urlopen=urlopen) == b"<rss/>"
    assert seen[0].get_header("User-agent") == "LibWatch/0.1"


def test_timeout() -> None:
    def urlopen(req: Request, timeout: float | None = None) -> FakeResp:
        raise TimeoutError

    with pytest.raises(FetchError) as exc:
        fetch_feed("https://example.com/feed.xml", urlopen=urlopen)
    assert exc.value.reason == "timeout"


def test_urlerror() -> None:
    def urlopen(req: Request, timeout: float | None = None) -> FakeResp:
        raise URLError("no")

    with pytest.raises(FetchError) as exc:
        fetch_feed("https://example.com/feed.xml", urlopen=urlopen)
    assert exc.value.reason == "connection failed"


def test_http_404() -> None:
    def urlopen(req: Request, timeout: float | None = None) -> FakeResp:
        raise HTTPError("https://example.com/feed.xml", 404, "no", Message(), None)

    with pytest.raises(FetchError) as exc:
        fetch_feed("https://example.com/feed.xml", urlopen=urlopen)
    assert exc.value.reason == "HTTP 404"


def test_redirects_then_ok() -> None:
    calls: list[str] = []

    def urlopen(req: Request, timeout: float | None = None) -> FakeResp:
        url = req.full_url
        calls.append(url)
        if len(calls) <= 5:
            return FakeResp(
                b"",
                status=302,
                headers={"Location": f"https://example.com/r{len(calls)}"},
            )
        return FakeResp(b"<rss/>", status=200)

    body = fetch_feed("https://example.com/start", urlopen=urlopen)
    assert body == b"<rss/>"
    assert len(calls) == 6


def test_too_many_redirects() -> None:
    def urlopen(req: Request, timeout: float | None = None) -> FakeResp:
        return FakeResp(b"", status=302, headers={"Location": "https://example.com/next"})

    with pytest.raises(FetchError) as exc:
        fetch_feed("https://example.com/start", urlopen=urlopen)
    assert exc.value.reason == "too many redirects"


def test_content_length_too_large() -> None:
    def urlopen(req: Request, timeout: float | None = None) -> FakeResp:
        return FakeResp(b"x", status=200, headers={"Content-Length": "2097153"})

    with pytest.raises(FetchError) as exc:
        fetch_feed("https://example.com/feed.xml", urlopen=urlopen)
    assert exc.value.reason == "too large"


def test_body_too_large() -> None:
    def urlopen(req: Request, timeout: float | None = None) -> FakeResp:
        return FakeResp(b"x" * (2 * 1024 * 1024 + 1), status=200)

    with pytest.raises(FetchError) as exc:
        fetch_feed("https://example.com/feed.xml", urlopen=urlopen)
    assert exc.value.reason == "too large"
