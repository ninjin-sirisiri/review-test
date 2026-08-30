from __future__ import annotations

import re
from urllib.parse import urlparse

_OWNER_REPO = re.compile(r"^[A-Za-z0-9._-]+$")
_PATH = re.compile(
    r"^/(?P<owner>[A-Za-z0-9._-]+)/(?P<repo>[A-Za-z0-9._-]+)"
    r"(?:/releases(?:\.atom)?)?/?$"
)


class GitHubReleasesUrlError(ValueError):
    """Raised when a URL cannot be resolved to a GitHub releases Atom feed."""


def resolve_releases_feed_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise GitHubReleasesUrlError(f"unsupported scheme: {url!r}")
    if parsed.username is not None or parsed.password is not None:
        raise GitHubReleasesUrlError(f"credentials not allowed: {url!r}")
    hostname = (parsed.hostname or "").lower()
    if hostname != "github.com":
        raise GitHubReleasesUrlError(f"not github.com: {url!r}")
    match = _PATH.match(parsed.path or "")
    if match is None:
        raise GitHubReleasesUrlError(f"invalid github releases path: {url!r}")
    owner = match.group("owner")
    repo = match.group("repo")
    if not _OWNER_REPO.match(owner) or not _OWNER_REPO.match(repo):
        raise GitHubReleasesUrlError(f"invalid owner or repo: {url!r}")
    return f"https://github.com/{owner}/{repo}/releases.atom"
