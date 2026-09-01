from __future__ import annotations

import html
from collections.abc import Iterable
from urllib.parse import quote

from libwatch.config import WatchTarget
from libwatch.render import RENDER_CSS


MANAGE_CSS: str = RENDER_CSS + """

label {
  display: block;
  margin-top: 0.75rem;
}

input {
  width: 100%;
  box-sizing: border-box;
}

button {
  margin-top: 1rem;
}
"""


def render_unbuilt_html() -> str:
    return "\n".join(
        [
            "<!DOCTYPE html>",
            '<html lang="ja">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "<title>ライブラリ更新ウォッチ</title>",
            '<link rel="stylesheet" href="/manage.css">',
            "</head>",
            "<body>",
            "<header>",
            "<h1>ライブラリ更新ウォッチ</h1>",
            "</header>",
            "<main>",
            "<p>タイムラインはまだビルドされていない</p>",
            "</main>",
            "</body>",
            "</html>",
            "",
        ]
    )


def render_manage_error_html(message: str) -> str:
    return _render_document(
        [
            "<main>",
            f"<p>{_escape(message)}</p>",
            "</main>",
        ]
    )


def render_manage_html(
    *,
    targets: Iterable[WatchTarget],
    file_hash: str,
    error: str | None = None,
    mode: str = "list",
    focus_name: str | None = None,
    form_name: str = "",
    form_blog: str = "",
    form_releases: str = "",
) -> str:
    target_list = tuple(targets)
    if mode == "confirm":
        name = focus_name if focus_name is not None else form_name
        return _render_document(
            [
                "<main>",
                f"<p>{_escape(name)} を削除しますか</p>",
                _confirm_form(name=name, file_hash=file_hash),
                '<p><a href="/manage">キャンセル</a></p>',
                "</main>",
            ]
        )

    parts: list[str] = ["<main>"]
    if error is not None:
        parts.append(f"<p>{_escape(error)}</p>")
    parts.extend(
        _target_form(
            action="add",
            file_hash=file_hash,
            form_name=form_name,
            form_blog=form_blog,
            form_releases=form_releases,
            button="追加",
            heading="追加",
        )
    )

    for target in target_list:
        if mode == "edit" and target.name == focus_name:
            parts.extend(
                _target_form(
                    action="edit",
                    file_hash=file_hash,
                    original_name=target.name,
                    form_name=form_name,
                    form_blog=form_blog,
                    form_releases=form_releases,
                    button="保存",
                    heading="編集",
                )
            )
            parts.append('<p><a href="/manage">キャンセル</a></p>')
        else:
            parts.extend(_render_target(target, show_delete=len(target_list) >= 2))

    parts.append("</main>")
    return _render_document(parts)


def _render_document(main_parts: list[str]) -> str:
    return "\n".join(
        [
            "<!DOCTYPE html>",
            '<html lang="ja">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "<title>ウォッチ対象</title>",
            '<link rel="stylesheet" href="/manage.css">',
            "</head>",
            "<body>",
            "<header>",
            "<h1>ウォッチ対象</h1>",
            '<a href="/">タイムライン</a>',
            "</header>",
            *main_parts,
            "</body>",
            "</html>",
            "",
        ]
    )


def _target_form(
    *,
    action: str,
    file_hash: str,
    form_name: str,
    form_blog: str,
    form_releases: str,
    button: str,
    heading: str,
    original_name: str | None = None,
) -> list[str]:
    prefix = "add" if action == "add" else "edit"
    parts = [f"<section><h2>{heading}</h2>", '<form action="/manage" method="post">']
    parts.append(f'<input type="hidden" name="action" value="{_escape(action)}">')
    parts.append(f'<input type="hidden" name="hash" value="{_escape(file_hash)}">')
    if original_name is not None:
        parts.append(
            '<input type="hidden" name="original_name" '
            f'value="{_escape(original_name)}">'
        )
    parts.extend(_form_fields(prefix, form_name, form_blog, form_releases))
    parts.append(f'<button type="submit">{button}</button>')
    parts.extend(["</form>", "</section>"])
    return parts


def _form_fields(prefix: str, name: str, blog: str, releases: str) -> list[str]:
    return [
        f'<label for="{prefix}-name">名前</label>',
        f'<input id="{prefix}-name" name="name" value="{_escape(name)}">',
        f'<label for="{prefix}-blog">公式ブログ</label>',
        f'<input id="{prefix}-blog" name="blog" value="{_escape(blog)}">',
        f'<label for="{prefix}-releases">リリースノート</label>',
        f'<input id="{prefix}-releases" name="releases" value="{_escape(releases)}">',
    ]


def _confirm_form(*, name: str, file_hash: str) -> str:
    return "\n".join(
        [
            '<form action="/manage" method="post">',
            '<input type="hidden" name="action" value="delete">',
            f'<input type="hidden" name="hash" value="{_escape(file_hash)}">',
            f'<input type="hidden" name="name" value="{_escape(name)}">',
            "<button type=\"submit\">削除する</button>",
            "</form>",
        ]
    )


def _render_target(target: WatchTarget, *, show_delete: bool) -> list[str]:
    parts = ["<section>", f"<h2>{_escape(target.name)}</h2>"]
    if target.blog is not None:
        parts.append(f"<p>公式ブログ: {_escape(target.blog)}</p>")
    if target.releases is not None:
        parts.append(f"<p>リリースノート: {_escape(target.releases)}</p>")
    edit_href = f"/manage?edit={quote(target.name, safe='')}"
    parts.append(f'<a href="{_escape(edit_href)}">編集</a>')
    if show_delete:
        delete_href = f"/manage?confirm_delete={quote(target.name, safe='')}"
        parts.append(f'<a href="{_escape(delete_href)}">削除</a>')
    parts.append("</section>")
    return parts


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)
