from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import yaml

from libwatch.github_url import GitHubReleasesUrlError, resolve_releases_feed_url


class ConfigError(ValueError):
    """Raised when a watchlist file cannot be loaded or validated."""


@dataclass(frozen=True)
class WatchTarget:
    name: str
    blog: str | None
    releases: str | None


@dataclass(frozen=True)
class Watchlist:
    targets: tuple[WatchTarget, ...]


def load_watchlist(path: Path) -> Watchlist:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ConfigError(f"watchlist not found: {path}") from exc
    except UnicodeDecodeError as exc:
        raise ConfigError(f"watchlist is not valid UTF-8: {path}") from exc
    except OSError as exc:
        raise ConfigError(f"cannot read watchlist: {path}") from exc

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in watchlist: {path}") from exc

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


def _parse_target(item: object, seen_names: set[str]) -> WatchTarget:
    if not isinstance(item, dict):
        raise ConfigError("each target must be a mapping")
    allowed = {"name", "blog", "releases"}
    if not set(item.keys()).issubset(allowed):
        raise ConfigError("target contains unknown keys")
    if "name" not in item:
        raise ConfigError("target missing 'name'")

    name_raw = item["name"]
    if not isinstance(name_raw, str):
        raise ConfigError("target 'name' must be a string")
    name = name_raw.strip()
    if not name:
        raise ConfigError("target 'name' must be non-empty after trim")
    if name in seen_names:
        raise ConfigError(f"duplicate target name: {name!r}")
    seen_names.add(name)

    blog = _optional_url_field(item.get("blog"), field="blog")
    releases_raw = _optional_url_field(item.get("releases"), field="releases")
    if blog is None and releases_raw is None:
        raise ConfigError("target needs blog and/or releases")

    blog_url = _normalize_blog(blog) if blog is not None else None
    releases_url = None
    if releases_raw is not None:
        try:
            releases_url = resolve_releases_feed_url(releases_raw)
        except GitHubReleasesUrlError as exc:
            raise ConfigError(str(exc)) from exc

    return WatchTarget(name=name, blog=blog_url, releases=releases_url)


def _optional_url_field(value: object, *, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigError(f"target '{field}' must be a string")
    stripped = value.strip()
    if not stripped:
        return None
    return stripped


def _normalize_blog(url: str) -> str:
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
    except ValueError as exc:
        raise ConfigError(f"blog URL must be absolute http(s): {url!r}") from exc
    if parsed.scheme not in {"http", "https"}:
        raise ConfigError(f"blog URL must be absolute http(s): {url!r}")
    if not hostname:
        raise ConfigError(f"blog URL must include a hostname: {url!r}")
    return urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, "")
    )
