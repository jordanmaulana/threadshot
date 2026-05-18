from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from slowapi.middleware import SlowAPIMiddleware

from .routes import install_rate_limit_handler, router
from .shotter import get_shotter

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    shotter = get_shotter()
    await shotter.start()
    try:
        yield
    finally:
        await shotter.stop()


def create_app() -> FastAPI:
    app = FastAPI(title="Threadshot", lifespan=lifespan)
    install_rate_limit_handler(app)
    app.add_middleware(SlowAPIMiddleware)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.include_router(router)
    return app


app = create_app()
