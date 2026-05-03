"""FastAPI entrypoint for Silicon Agents."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
import logging
from time import perf_counter
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
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


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
    )


logger = logging.getLogger(__name__)


def redact_db_target(value: str) -> str:
    text = str(value or "")
    if text.startswith(("postgresql://", "postgres://")):
        return "postgresql://<redacted>"
    return text

def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await FeedbackStore(settings.db_path).init()
        logger.info(
            "Silicon Agents starting version=%s db_path=%s pilot_access=%s",
            settings.app_version,
            redact_db_target(settings.db_path),
            "enabled" if settings.pilot_access_token else "disabled",
        )
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

    @app.middleware("http")
    async def pilot_access_and_logging(request: Request, call_next):
        started = perf_counter()
        path = request.url.path
        method = request.method.upper()
        access_enabled = bool(settings.pilot_access_token)
        exempt_paths = {"/health", "/pilot-login", "/pilot/unlock"}
        exempt_prefixes = ("/docs", "/openapi.json", "/redoc", "/sample-data")
        header_token = request.headers.get("X-Pilot-Access-Token", "")
        cookie_token = request.cookies.get(settings.pilot_cookie_name, "")

        if access_enabled and method != "OPTIONS" and path not in exempt_paths and not path.startswith(exempt_prefixes):
            authorized = header_token == settings.pilot_access_token or cookie_token == settings.pilot_access_token
            if not authorized:
                accepts_html = "text/html" in request.headers.get("accept", "")
                if path.startswith("/api/") or not accepts_html:
                    duration_ms = int((perf_counter() - started) * 1000)
                    logger.warning("Rejected unauthorized request method=%s path=%s duration_ms=%s", request.method, path, duration_ms)
                    return JSONResponse(status_code=401, content={"detail": "Pilot access token required."})
                next_path = quote(str(request.url.path if not request.url.query else f"{request.url.path}?{request.url.query}"), safe="/?=&")
                duration_ms = int((perf_counter() - started) * 1000)
                logger.warning("Redirected unauthorized browser request method=%s path=%s duration_ms=%s", request.method, path, duration_ms)
                return RedirectResponse(url=f"/pilot-login?next={next_path}", status_code=307)

        response = await call_next(request)
        duration_ms = int((perf_counter() - started) * 1000)
        logger.info(
            "Request method=%s path=%s status=%s duration_ms=%s",
            request.method,
            path,
            response.status_code,
            duration_ms,
        )
        return response

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

    @app.get("/pilot")
    async def pilot_page() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "pilot.html")

    @app.get("/product-docs")
    async def product_docs_page() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "docs.html")

    @app.get("/pitch")
    async def pitch_page() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "pitch.html")

    @app.get("/pilot-login")
    async def pilot_login_page() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "pilot_access.html")

    @app.post("/pilot/unlock")
    async def pilot_unlock(request: Request) -> JSONResponse:
        if not settings.pilot_access_token:
            return JSONResponse({"unlocked": True, "mode": "disabled"})
        header_token = request.headers.get("X-Pilot-Access-Token", "")
        if header_token != settings.pilot_access_token:
            return JSONResponse(status_code=401, content={"detail": "Invalid pilot access token."})
        response = JSONResponse({"unlocked": True})
        response.set_cookie(
            key=settings.pilot_cookie_name,
            value=settings.pilot_access_token,
            httponly=True,
            samesite="lax",
            secure=False,
            max_age=60 * 60 * 12,
        )
        return response

    return app


app = create_app()
