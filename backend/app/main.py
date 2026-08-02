from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.metadata import router as metadata_router
from backend.app.api.v1.workflows import router as workflows_router
from backend.app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router, prefix=settings.api_prefix)
    app.include_router(workflows_router, prefix=settings.api_prefix)
    app.include_router(metadata_router, prefix=settings.api_prefix)
    return app


app = create_app()
