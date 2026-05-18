from unittest.mock import AsyncMock, patch

import pytest

from app import fetcher
from app.fetcher import PostNotFound, _parse_count, fetch, parse_url


def test_parse_url_valid():
    assert parse_url("https://www.threads.com/@user/post/ABC123") == ("user", "ABC123")
    assert parse_url("https://threads.net/@user.name/post/XYZ?igshid=1") == ("user.name", "XYZ")


def test_parse_url_invalid():
    with pytest.raises(ValueError):
        parse_url("https://example.com/foo")
    with pytest.raises(ValueError):
        parse_url("https://www.threads.com/@user")


def test_parse_count():
    assert _parse_count("7") == 7
    assert _parse_count("1,234") == 1234
    assert _parse_count("1.2K") == 1200
    assert _parse_count("3M") == 3_000_000
    assert _parse_count("") is None
    assert _parse_count("nope") is None


@pytest.fixture(autouse=True)
def clear_cache():
    fetcher._cache.clear()
    yield
    fetcher._cache.clear()


async def test_fetch_parses_full_payload():
    fake = {
        "title": "Laisa (@laiszura) on Threads",
        "desc": "dibilang kerja engga.",
        "og_image": "https://cdn.example.com/t51.82787-19/avatar.jpg",
        "avatar": "https://cdn.example.com/t51.82787-19/avatar_small.jpg",
        "time_text": "2h",
        "time_iso": "2026-05-18T00:54:11.000Z",
        "counts": ["7", "11", "1"],
        "final_url": "https://www.threads.com/@laiszura/post/X",
    }
    with patch("app.fetcher.get_shotter") as gs:
        gs.return_value.fetch_page_meta = AsyncMock(return_value=fake)
        post = await fetch("https://www.threads.com/@laiszura/post/X")
    assert post.handle == "laiszura"
    assert post.author == "Laisa"
    assert post.text == "dibilang kerja engga."
    assert post.avatar_url == "https://cdn.example.com/t51.82787-19/avatar_small.jpg"
    assert post.media == []
    assert post.time_text == "2h"
    assert post.created_at == "2026-05-18T00:54:11.000Z"
    assert post.like_count == 7
    assert post.reply_count == 11
    assert post.repost_count == 1


async def test_fetch_media_post_separates_avatar():
    fake = {
        "title": "U (@u) on Threads",
        "desc": "look",
        "og_image": "https://cdn.example.com/feed_image.jpg",
        "avatar": "https://cdn.example.com/t51.82787-19/avatar.jpg",
        "time_text": "1d",
        "time_iso": "2026-05-17T00:00:00.000Z",
        "counts": [],
        "final_url": "https://www.threads.com/@u/post/X",
    }
    with patch("app.fetcher.get_shotter") as gs:
        gs.return_value.fetch_page_meta = AsyncMock(return_value=fake)
        post = await fetch("https://www.threads.com/@u/post/X")
    assert post.avatar_url == "https://cdn.example.com/t51.82787-19/avatar.jpg"
    assert post.media == ["https://cdn.example.com/feed_image.jpg"]
    assert post.like_count is None


async def test_fetch_invalid_post_redirect():
    fake = {"title": "", "desc": "", "og_image": "", "avatar": "",
            "time_text": "", "time_iso": "", "counts": [],
            "final_url": "https://www.threads.com/?error=invalid_post"}
    with patch("app.fetcher.get_shotter") as gs:
        gs.return_value.fetch_page_meta = AsyncMock(return_value=fake)
        with pytest.raises(PostNotFound):
            await fetch("https://www.threads.com/@u/post/X")


async def test_fetch_empty_metadata():
    fake = {"title": "Threads", "desc": "", "og_image": "", "avatar": "",
            "time_text": "", "time_iso": "", "counts": [],
            "final_url": "https://www.threads.com/@u/post/X"}
    with patch("app.fetcher.get_shotter") as gs:
        gs.return_value.fetch_page_meta = AsyncMock(return_value=fake)
        with pytest.raises(PostNotFound):
            await fetch("https://www.threads.com/@u/post/X")
