from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.database import init_database
from app.exceptions.handlers import register_exception_handlers
from app.middleware.logging import RequestLoggingMiddleware
from app.services.auth_service import bootstrap_admin_from_environment


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings.media_root.mkdir(parents=True, exist_ok=True)
    if settings.auto_create_schema:
        init_database()
    bootstrap_admin_from_environment()
    yield


configure_logging()
app = FastAPI(
    title=settings.project_name,
    version="1.0.0",
    description="Role-scoped listing capture, review, and public approved-listing search.",
    lifespan=lifespan,
)
register_exception_handlers(app)
app.add_middleware(RequestLoggingMiddleware)
app.mount("/media", StaticFiles(directory=str(settings.media_root), check_dir=False), name="media")
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {"message": settings.project_name, "docs": "/docs", "api_v1": settings.api_v1_prefix}


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
