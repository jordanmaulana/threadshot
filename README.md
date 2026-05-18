# Threadshot

Paste a [Threads](https://www.threads.com) post URL, get a clean PNG screenshot. FastAPI + Playwright.

![sample](shot.png)

## Features

- Accepts `threads.com` / `threads.net` post URLs.
- Renders a self-contained card (avatar + media inlined as `data:` URIs) and screenshots it via headless Chromium.
- 10-minute in-memory cache per canonical URL.
- Per-IP rate limiting (slowapi).
- AdSense slot for monetization.

## Quick start

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run playwright install chromium
cp .env.example .env
uv run uvicorn app.main:app --reload
```

Open <http://localhost:8000>.

### Docker

```bash
docker compose up --build
```

Image already includes Playwright + Chromium (`mcr.microsoft.com/playwright/python`). Reads `.env` for config.

## Config

`.env` keys:

| Key | Default | Notes |
|---|---|---|
| `ADSENSE_CLIENT` | `""` | Google AdSense client id; empty disables ad slot. |
| `RATE_LIMIT` | `10/minute` | slowapi syntax (`N/second|minute|hour|day`). |

Other settings in [app/config.py](app/config.py): `user_agent`, `media_proxy_allowed_hosts`.

## Endpoints

- `GET /` — form page.
- `POST /shot` — form field `url`; returns HTML with embedded PNG (`data:image/png;base64,...`) plus download link.
- `GET /about`, `GET /privacy` — static pages.
- `GET /static/*` — CSS.

Errors render as HTML with status: `422` bad URL, `404` post missing/private, `429` rate limited, `502` blocked by Threads, `500` render failure.

## Tests

```bash
uv run pytest
uv run pytest tests/test_fetcher.py::test_parse_count
```

`pytest-asyncio` runs in auto mode. Tests stub the Playwright browser and the Threads page metadata; no network needed.

## Architecture

```
routes.py  →  fetcher.py  →  shotter.fetch_page_meta   (scrape og:* + DOM)
              renderer.py →  shotter.shoot             (screenshot #card)
```

One Chromium browser lives for the app's lifetime ([app/shotter.py](app/shotter.py)), started/stopped by FastAPI lifespan. Each request gets a fresh `BrowserContext`. See [CLAUDE.md](CLAUDE.md) for details and gotchas.

## License

TBD.
