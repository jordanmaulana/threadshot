# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Threadshot — FastAPI service that accepts a Threads (threads.com / threads.net) post URL and returns a PNG screenshot of a rendered card of that post. Monetization stub via AdSense client id env var. Python 3.11+, managed with `uv`.

## Commands

Dependency + tooling uses `uv`. Playwright Chromium is required at runtime (the Docker image ships it; locally install browsers once).

```bash
uv sync                           # install deps incl. dev
uv run playwright install chromium  # first-time local browser install
uv run uvicorn app.main:app --reload  # dev server on :8000
uv run pytest                     # all tests
uv run pytest tests/test_fetcher.py::test_parse_count  # single test
docker compose up --build         # containerized run (uses .env)
make install-css                  # one-time: install Tailwind CLI (npm)
make css                          # rebuild static/tailwind.css after any template class change
make css-watch                    # auto-rebuild during template edits
```

Frontend uses Tailwind v4 compiled via `@tailwindcss/cli`. Source is [static/tailwind.src.css](static/tailwind.src.css) which `@source`s the `templates/` dir and `app/routes.py`. The output `static/tailwind.css` is **committed** to git (deploy artifact) — the Dockerfile copies it as-is, no Node in the runtime image. Re-run `make css` and commit the result after editing any Tailwind class. [templates/card.html.j2](templates/card.html.j2) is screenshot-only and intentionally NOT in Tailwind.

Config via `.env` (see `.env.example`): `ADSENSE_CLIENT`, `RATE_LIMIT` (slowapi syntax e.g. `10/minute`). Other settings in [app/config.py](app/config.py): `USER_AGENT`, `MEDIA_PROXY_ALLOWED_HOSTS`.

## Architecture

Request flow for `POST /shot` (form field `url`):

1. [app/routes.py](app/routes.py) — validates URL via `parse_url`, calls `fetch`, renders card HTML, drives `Shotter.shoot`, returns base64 PNG embedded in result page.
2. [app/fetcher.py](app/fetcher.py) — `parse_url` enforces `threads.(com|net)/@handle/post/code` regex; `fetch` checks a 10-min `TTLCache`, then asks `Shotter.fetch_page_meta` to render the live Threads page in headless Chromium and scrape `og:*` meta, avatar `<img>`, `<time datetime>`, and engagement counts (`\d[\d.,]*[KMB]?` text nodes, first 3). Distinguishes profile-pic `og:image` (path contains `t51.82787-19` or `profile_pic`) from feed-media `og:image`. Detects `error=invalid_post`/login redirects → `PostNotFound`. Author display name parsed from `og:title` via `_OG_TITLE_RE`.
3. [app/renderer.py](app/renderer.py) — Jinja env over [templates/](templates/); `render_card` re-fetches avatar + media via `httpx` and **inlines them as `data:` URIs** so the screenshot is fully offline-resolvable. Templates auto-escape html/xml/j2.
4. [app/shotter.py](app/shotter.py) — singleton `Shotter` owning one Playwright Chromium browser, started in FastAPI `lifespan`. Two methods share the browser: `fetch_page_meta(url, user_agent)` and `shoot(html, width=600, scale=2)` which `set_content(..., wait_until="networkidle")` then screenshots the `#card` locator. Each call gets a fresh `BrowserContext`.

Rate limiting via `slowapi` ([app/ratelimit.py](app/ratelimit.py)), keyed on remote address; `RateLimitExceeded` → 429 HTML error from `install_rate_limit_handler` in [app/routes.py](app/routes.py).

Entry point [app/main.py](app/main.py) wires lifespan (starts/stops Shotter), `SlowAPIMiddleware`, `/static` mount, and the router.

## Conventions / gotchas

- `Shotter` is a process-wide singleton (`get_shotter()`); tests in [tests/test_routes.py](tests/test_routes.py) patch `app.shotter.Shotter.{start,stop,shoot}` to avoid launching Chromium. Mock `app.fetcher.get_shotter().fetch_page_meta` (see [tests/test_fetcher.py](tests/test_fetcher.py)) — do not call the real Threads site in tests.
- `_cache` in `fetcher` is module-global; `clear_cache` autouse fixture resets it between tests. Do the same when adding new fetcher tests.
- `pytest-asyncio` is in `asyncio_mode = "auto"` (see `pyproject.toml`) — async test functions need no decorator.
- Screenshot target element must have `id="card"` in [templates/card.html.j2](templates/card.html.j2); changing it breaks `shoot`.
- Media inlining tolerates per-asset failure: failed fetches drop from `post.media` but a failed avatar becomes `None` (template must handle absence). Only `MEDIA_PROXY_ALLOWED_HOSTS` are intended for media — current renderer does not enforce this; if adding a proxy endpoint, validate against that tuple.
- Engagement count parsing relies on Threads' DOM having short `<span>/<div>` leaf nodes matching the count regex; brittle to layout changes.
