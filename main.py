"""FastAPI entrypoint for Silicon Agents."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from silicon_agents.api.router_benchmark import router as benchmark_router
from silicon_agents.api.router_config import router as config_router
from silicon_agents.api.router_feedback import router as feedback_router
from silicon_agents.api.router_verify import router as verify_router
from silicon_agents.api.router_yield import router as yield_router
from silicon_agents.core.config import get_settings
from silicon_agents.storage.feedback_store import FeedbackStore


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
SAMPLE_DATA_DIR = BASE_DIR / "sample_data"

def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await FeedbackStore(settings.db_path).init()
        yield

    app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(benchmark_router)
    app.include_router(config_router)
    app.include_router(verify_router)
    app.include_router(yield_router)
    app.include_router(feedback_router)
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
    app.mount("/sample-data", StaticFiles(directory=SAMPLE_DATA_DIR), name="sample-data")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": settings.app_version}

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/agent01")
    async def agent01_page() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "agent01.html")

    @app.get("/agent02")
    async def agent02_page() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "agent02.html")

    @app.get("/configuration")
    async def configuration_page() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "configuration.html")

    @app.get("/history")
    async def history_page() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "history.html")

    return app


app = create_app()
