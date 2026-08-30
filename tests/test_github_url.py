import pytest

from libwatch.github_url import GitHubReleasesUrlError, resolve_releases_feed_url


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "https://github.com/facebook/react",
            "https://github.com/facebook/react/releases.atom",
        ),
        (
            "https://github.com/facebook/react/",
            "https://github.com/facebook/react/releases.atom",
        ),
        (
            "https://github.com/facebook/react/releases",
            "https://github.com/facebook/react/releases.atom",
        ),
        (
            "https://github.com/facebook/react/releases/",
            "https://github.com/facebook/react/releases.atom",
        ),
        (
            "https://github.com/facebook/react/releases.atom",
            "https://github.com/facebook/react/releases.atom",
        ),
        (
            "http://GitHub.COM/Foo/Bar/releases.atom",
            "https://github.com/Foo/Bar/releases.atom",
        ),
        (
            "https://github.com/facebook/react/releases?foo=1#x",
            "https://github.com/facebook/react/releases.atom",
        ),
    ],
)
def test_resolve_releases_feed_url(url: str, expected: str) -> None:
    assert resolve_releases_feed_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://gitlab.com/facebook/react/releases",
        "https://www.github.com/facebook/react",
        "https://github.com/facebook/react/releases/tag/v1.0.0",
        "https://github.com/facebook/react/tree/main",
        "https://gist.github.com/foo/bar",
        "not-a-url",
        "https://github.com/facebook",
    ],
)
def test_resolve_releases_feed_url_rejects(url: str) -> None:
    with pytest.raises(GitHubReleasesUrlError):
        resolve_releases_feed_url(url)
