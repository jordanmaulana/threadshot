from __future__ import annotations

import base64

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from slowapi.errors import RateLimitExceeded

from .config import settings
from .fetcher import Blocked, PostNotFound, fetch, parse_url
from .ratelimit import limiter
from .renderer import render_card, render_error, render_index, render_result, render_static_page
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
    return HTMLResponse(render_static_page("about"))


@router.get("/privacy", response_class=HTMLResponse)
async def privacy() -> HTMLResponse:
    return HTMLResponse(render_static_page("privacy"))


def install_rate_limit_handler(app) -> None:
    from slowapi import _rate_limit_exceeded_handler

    async def handler(request: Request, exc: RateLimitExceeded) -> HTMLResponse:
        return HTMLResponse(render_error("Slow down — too many requests. Try again in a minute."),
                            status_code=429)

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, handler)
