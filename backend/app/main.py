"""
main.py — FastAPI application factory.

All routes live under /api/v1. Authentication is handled per-router via
the get_current_user dependency injected at each endpoint.

A background task periodically sweeps expired export files/records so
temp storage doesn't grow unbounded — see app/services/export_cleanup.py.
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base, AsyncSessionLocal
from app.routers import auth, projects, questions, parser, google_forms, exports
from app.routers.settings_dashboard import settings_router, dashboard_router
from app.services.export_cleanup import cleanup_expired_exports

logger = logging.getLogger(__name__)

EXPORT_CLEANUP_INTERVAL_SECONDS = 60 * 60  # sweep hourly


async def _export_cleanup_loop():
    """Runs cleanup_expired_exports() on a fixed interval until cancelled."""
    while True:
        try:
            await asyncio.sleep(EXPORT_CLEANUP_INTERVAL_SECONDS)
            async with AsyncSessionLocal() as db:
                await cleanup_expired_exports(db, exports.EXPORT_DIR)
                await db.commit()
        except asyncio.CancelledError:
            break
        except Exception as e:
            # Never let a cleanup failure crash the whole background loop —
            # log it and try again on the next interval.
            logger.error("Export cleanup sweep failed: %s", e, exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: auto-create all tables (Alembic handles migrations in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    cleanup_task = asyncio.create_task(_export_cleanup_loop())

    yield

    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.is_dev else None,
    redoc_url="/redoc" if settings.is_dev else None,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PREFIX = "/api/v1"

app.include_router(auth.router,         prefix=f"{PREFIX}/auth",      tags=["auth"])
app.include_router(projects.router,     prefix=f"{PREFIX}/projects",  tags=["projects"])
app.include_router(questions.router,    prefix=f"{PREFIX}/projects",  tags=["questions"])
app.include_router(parser.router,       prefix=f"{PREFIX}/parse",     tags=["parser"])
app.include_router(google_forms.router, prefix=f"{PREFIX}/forms",     tags=["forms"])
app.include_router(exports.router,      prefix=f"{PREFIX}/export",    tags=["exports"])
app.include_router(settings_router,     prefix=f"{PREFIX}/settings",  tags=["settings"])
app.include_router(dashboard_router,    prefix=f"{PREFIX}/dashboard", tags=["dashboard"])


@app.get("/health", tags=["health"])
async def health():
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }
