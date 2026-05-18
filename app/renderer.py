from __future__ import annotations

import asyncio
import base64
from dataclasses import replace
from pathlib import Path

import httpx
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import settings
from .fetcher import Post

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml", "j2"]),
)


async def _inline_media(client: httpx.AsyncClient, url: str) -> str | None:
    try:
        r = await client.get(url, timeout=10.0)
        r.raise_for_status()
    except (httpx.HTTPError, httpx.TimeoutException):
        return None
    ctype = r.headers.get("content-type", "image/jpeg").split(";")[0].strip()
    b64 = base64.b64encode(r.content).decode("ascii")
    return f"data:{ctype};base64,{b64}"


async def _post_with_inlined_media(post: Post) -> Post:
    async with httpx.AsyncClient(
        headers={"User-Agent": settings.user_agent, "Referer": "https://www.threads.com/"},
        follow_redirects=True,
    ) as client:
        coros = []
        if post.avatar_url:
            coros.append(_inline_media(client, post.avatar_url))
        for m in post.media:
            coros.append(_inline_media(client, m))
        results = await asyncio.gather(*coros) if coros else []

    new_avatar = post.avatar_url
    new_media = list(post.media)
    idx = 0
    if post.avatar_url:
        new_avatar = results[idx] or None
        idx += 1
    new_media = [results[idx + i] or post.media[i] for i in range(len(post.media))]
    new_media = [m for m in new_media if m and not m.startswith("http")]  # drop ones that failed (still http)
    if not new_media and post.media:
        new_media = []
    return replace(post, avatar_url=new_avatar, media=new_media)


async def render_card(post: Post) -> str:
    inlined = await _post_with_inlined_media(post)
    tpl = _env.get_template("card.html.j2")
    return tpl.render(post=inlined)


def render_index(*, adsense_client: str = "", message: str | None = None) -> str:
    tpl = _env.get_template("index.html.j2")
    return tpl.render(adsense_client=adsense_client, message=message)


def render_result(post: Post, img_b64: str) -> str:
    tpl = _env.get_template("result.html.j2")
    return tpl.render(post=post, img_b64=img_b64)


def render_error(message: str) -> str:
    tpl = _env.get_template("error.html.j2")
    return tpl.render(message=message)
