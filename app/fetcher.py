from __future__ import annotations

import re
from dataclasses import dataclass, field

from cachetools import TTLCache

from .config import settings
from .shotter import get_shotter


class FetcherError(Exception):
    pass


class PostNotFound(FetcherError):
    pass


class Blocked(FetcherError):
    pass


@dataclass
class Post:
    url: str
    author: str
    handle: str
    avatar_url: str | None
    text: str
    created_at: str | None = None
    time_text: str | None = None
    media: list[str] = field(default_factory=list)
    like_count: int | None = None
    reply_count: int | None = None
    repost_count: int | None = None


_URL_RE = re.compile(
    r"^https?://(?:www\.)?threads\.(?:com|net)/@([\w.\-]+)/post/([\w\-]+)/?(?:[?#].*)?$"
)
_OG_TITLE_RE = re.compile(r"^(.*?)\s*\(@([\w.\-]+)\)\s+on\s+Threads")

_cache: TTLCache[str, Post] = TTLCache(maxsize=1000, ttl=600)


def parse_url(url: str) -> tuple[str, str]:
    m = _URL_RE.match(url.strip())
    if not m:
        raise ValueError("Not a valid Threads post URL")
    return m.group(1), m.group(2)


def _canonical(url: str) -> str:
    handle, code = parse_url(url)
    return f"https://www.threads.com/@{handle}/post/{code}"


def _parse_count(s: str) -> int | None:
    s = s.strip().replace(",", "")
    if not s:
        return None
    mult = 1
    if s[-1] in ("K", "M", "B"):
        mult = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}[s[-1]]
        s = s[:-1]
    try:
        return int(float(s) * mult)
    except ValueError:
        return None


async def fetch(url: str) -> Post:
    canon = _canonical(url)
    if canon in _cache:
        return _cache[canon]

    handle_from_url, _ = parse_url(canon)
    shotter = get_shotter()
    raw = await shotter.fetch_page_meta(canon, user_agent=settings.user_agent)

    final_url = raw.get("final_url", canon)
    if "error=invalid_post" in final_url or "login" in final_url.lower():
        raise PostNotFound(f"Post not found or private: {canon}")

    title = raw.get("title") or ""
    desc = raw.get("desc") or ""
    og_image = raw.get("og_image") or ""
    avatar = raw.get("avatar") or ""

    if not desc and not og_image and not avatar:
        raise PostNotFound("Post metadata empty")

    handle = handle_from_url
    author = handle
    m = _OG_TITLE_RE.match(title)
    if m:
        author = m.group(1).strip()
        handle = m.group(2).strip()

    avatar_url = avatar or None
    # og:image is profile pic for text-only posts; fall back if no DOM avatar
    if not avatar_url and og_image and ("profile_pic" in og_image.lower() or "t51.82787-19" in og_image):
        avatar_url = og_image

    media: list[str] = []
    if og_image and og_image != avatar_url and "t51.82787-19" not in og_image:
        media = [og_image]

    counts = raw.get("counts") or []
    like = _parse_count(counts[0]) if len(counts) > 0 else None
    reply = _parse_count(counts[1]) if len(counts) > 1 else None
    repost = _parse_count(counts[2]) if len(counts) > 2 else None

    post = Post(
        url=canon,
        author=author,
        handle=handle,
        avatar_url=avatar_url,
        text=desc,
        created_at=raw.get("time_iso") or None,
        time_text=raw.get("time_text") or None,
        media=media,
        like_count=like,
        reply_count=reply,
        repost_count=repost,
    )
    _cache[canon] = post
    return post
