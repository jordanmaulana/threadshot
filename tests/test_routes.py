from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app import fetcher
from app.fetcher import Post


@pytest.fixture
def client():
    with patch("app.shotter.Shotter.start", new=AsyncMock()), \
         patch("app.shotter.Shotter.stop", new=AsyncMock()), \
         patch("app.shotter.Shotter.shoot", new=AsyncMock(return_value=b"\x89PNG\r\n\x1a\nFAKE")):
        from app.main import create_app
        app = create_app()
        with TestClient(app) as c:
            yield c


@pytest.fixture(autouse=True)
def clear_cache():
    fetcher._cache.clear()


def test_index_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Threadshot" in r.text
    assert "<form" in r.text


def test_index_no_ga_when_unset(client):
    r = client.get("/")
    assert "googletagmanager.com" not in r.text


def test_index_includes_ga_snippet(client):
    from app.config import settings
    with patch.object(settings, "ga_measurement_id", "G-TEST123"):
        r = client.get("/")
    assert r.status_code == 200
    assert "googletagmanager.com/gtag/js?id=G-TEST123" in r.text
    assert "gtag('config', 'G-TEST123')" in r.text
    assert "htmx:afterOnLoad" in r.text


def test_shot_rejects_bad_url(client):
    r = client.post("/shot", data={"url": "https://example.com"})
    assert r.status_code == 422
    assert "valid" in r.text.lower()


def test_shot_happy_path(client):
    fake = Post(
        url="https://www.threads.com/@u/post/X",
        author="U", handle="u", avatar_url=None,
        text="hi", created_at=None, media=[],
    )
    with patch("app.routes.fetch", new=AsyncMock(return_value=fake)):
        r = client.post("/shot", data={"url": "https://www.threads.com/@u/post/X"})
    assert r.status_code == 200
    assert "data:image/png;base64" in r.text
    assert "Download PNG" in r.text


def test_shot_post_not_found(client):
    from app.fetcher import PostNotFound
    with patch("app.routes.fetch", new=AsyncMock(side_effect=PostNotFound("gone"))):
        r = client.post("/shot", data={"url": "https://www.threads.com/@u/post/X"})
    assert r.status_code == 404
    assert "not found" in r.text.lower()
