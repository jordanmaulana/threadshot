from __future__ import annotations

import base64

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from slowapi.errors import RateLimitExceeded

from .config import settings
from .fetcher import Blocked, PostNotFound, fetch, parse_url
from .ratelimit import limiter
from .renderer import render_card, render_error, render_index, render_result
from .shotter import get_shotter

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse(render_index(
        adsense_client=settings.adsense_client,
        ga_measurement_id=settings.ga_measurement_id,
    ))


@router.post("/shot", response_class=HTMLResponse)
@limiter.limit(settings.rate_limit)
async def shot(request: Request, url: str = Form(...)) -> HTMLResponse:
    try:
        parse_url(url)
    except ValueError as e:
        return HTMLResponse(render_error(str(e)), status_code=422)

    try:
        post = await fetch(url)
    except PostNotFound:
        return HTMLResponse(render_error("Post not found or deleted."), status_code=404)
    except Blocked as e:
        return HTMLResponse(render_error(f"Blocked by Threads ({e})."), status_code=502)
    except Exception:
        return HTMLResponse(render_error("Could not fetch this post."), status_code=500)

    try:
        html = await render_card(post)
        png = await get_shotter().shoot(html)
    except Exception:
        return HTMLResponse(render_error("Failed to render screenshot."), status_code=500)

    img_b64 = base64.b64encode(png).decode("ascii")
    return HTMLResponse(render_result(post, img_b64))


@router.get("/about", response_class=HTMLResponse)
async def about() -> HTMLResponse:
    body = (
        "<h2 class='text-2xl font-semibold mt-2 mb-3'>About Threadshot</h2>"
        "<p class='mb-3'>Threadshot turns any public Threads post into a clean PNG image you can share. "
        "Paste the post URL on the home page and download the screenshot.</p>"
        "<p><a href='/' class='text-neutral-700 underline-offset-2 hover:underline'>Back</a></p>"
    )
    return HTMLResponse(_page("About", body))


@router.get("/privacy", response_class=HTMLResponse)
async def privacy() -> HTMLResponse:
    body = (
        "<h2 class='text-2xl font-semibold mt-2 mb-3'>Privacy</h2>"
        "<p class='mb-3'>Threadshot does not store post URLs, generated images, or personal data. "
        "Posts are fetched from threads.com on demand and rendered in memory. "
        "Analytics and ads are provided by Google AdSense; see Google's policy.</p>"
        "<p><a href='/' class='text-neutral-700 underline-offset-2 hover:underline'>Back</a></p>"
    )
    return HTMLResponse(_page("Privacy", body))


def _page(title: str, body_html: str) -> str:
    return (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{title} — Threadshot</title>"
        "<link rel='stylesheet' href='/static/tailwind.css'>"
        "</head><body class='bg-neutral-50 text-neutral-900 antialiased'>"
        "<main class='max-w-3xl mx-auto px-5 py-10'>"
        f"{body_html}"
        "</main></body></html>"
    )


def install_rate_limit_handler(app) -> None:
    from slowapi import _rate_limit_exceeded_handler

    async def handler(request: Request, exc: RateLimitExceeded) -> HTMLResponse:
        return HTMLResponse(render_error("Slow down — too many requests. Try again in a minute."),
                            status_code=429)

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, handler)
