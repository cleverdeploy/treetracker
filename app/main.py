from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.auth import configure_oauth
from app.config import get_settings
from app.routes import api, auth as auth_routes, pages, photos


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Tree Tracker", docs_url=None, redoc_url=None)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        same_site="lax",
        https_only=settings.base_url.startswith("https://"),
        max_age=60 * 60 * 24 * 30,
    )
    configure_oauth()

    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    app.include_router(auth_routes.router)
    app.include_router(api.router)
    app.include_router(photos.router)
    app.include_router(pages.router)

    @app.get("/manifest.webmanifest")
    def manifest():
        from fastapi.responses import FileResponse
        return FileResponse(static_dir / "manifest.webmanifest", media_type="application/manifest+json")

    @app.get("/sw.js")
    def sw():
        from fastapi.responses import FileResponse
        return FileResponse(static_dir / "sw.js", media_type="application/javascript")

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    return app


app = create_app()
