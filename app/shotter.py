from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from playwright.async_api import Browser, async_playwright


class Shotter:
    def __init__(self) -> None:
        self._playwright = None
        self._browser: Browser | None = None

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--font-render-hinting=medium",
            ],
        )

    async def stop(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def shoot(self, html: str, *, width: int = 600, scale: int = 2) -> bytes:
        if not self._browser:
            raise RuntimeError("Shotter not started")
        context = await self._browser.new_context(
            viewport={"width": width, "height": 800},
            device_scale_factor=scale,
            base_url="http://localhost",
        )
        try:
            page = await context.new_page()
            await page.set_content(html, wait_until="networkidle")
            element = page.locator("#card")
            return await element.screenshot(type="png", omit_background=True)
        finally:
            await context.close()

    async def fetch_page_meta(self, url: str, *, user_agent: str) -> dict:
        if not self._browser:
            raise RuntimeError("Shotter not started")
        context = await self._browser.new_context(user_agent=user_agent, viewport={"width": 1024, "height": 768})
        try:
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            try:
                await page.wait_for_selector("time[datetime]", timeout=12000)
            except Exception:
                pass
            return await page.evaluate(
                """() => {
                  const m = (p) => document.querySelector(`meta[property="${p}"]`)?.content || '';
                  const imgs = Array.from(document.querySelectorAll('img'));
                  const avatarImg = imgs.find(i => /profile picture/i.test(i.alt || ''));
                  const t = document.querySelector('time[datetime]');
                  const counts = [];
                  document.querySelectorAll('span, div').forEach(el => {
                    if (el.children.length === 0) {
                      const tx = (el.textContent || '').trim();
                      if (/^\\d[\\d.,]*[KMB]?$/.test(tx)) counts.push(tx);
                    }
                  });
                  return {
                    title: m('og:title'),
                    desc: m('og:description'),
                    og_image: m('og:image'),
                    avatar: avatarImg ? avatarImg.src : '',
                    time_text: t ? (t.textContent || '').trim() : '',
                    time_iso: t ? t.getAttribute('datetime') : '',
                    counts: counts.slice(0, 3),
                    final_url: location.href,
                  };
                }"""
            )
        finally:
            await context.close()


_shotter: Shotter | None = None


def get_shotter() -> Shotter:
    global _shotter
    if _shotter is None:
        _shotter = Shotter()
    return _shotter


@asynccontextmanager
async def lifespan_shotter() -> AsyncIterator[Shotter]:
    s = get_shotter()
    await s.start()
    try:
        yield s
    finally:
        await s.stop()
