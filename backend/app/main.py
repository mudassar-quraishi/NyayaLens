"""
NyayaLens FastAPI application — main entry point.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import delete, select

from app.config import get_settings
from app.database import init_db, engine, async_session
from app.models import Session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("nyayalens")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown hooks."""
    settings = get_settings()
    logger.info("Starting NyayaLens — model=%s, demo=%s", settings.llm_model, settings.demo_mode)

    # Create tables
    await init_db()
    logger.info("Database initialized")

    # Clean up expired sessions on startup
    async with async_session() as db:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            delete(Session).where(Session.expires_at < now)
        )
        if result.rowcount:
            await db.commit()
            logger.info("Cleaned up %d expired sessions", result.rowcount)

    yield

    # Shutdown
    await engine.dispose()
    logger.info("NyayaLens stopped")


app = FastAPI(
    title="NyayaLens",
    description="AI-powered legal document analysis — information, not advice.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
from app.api.routes import router as core_router
from app.api.analysis import router as analysis_router
from app.api.qa import router as qa_router
from app.api.compare import router as compare_router
from app.api.obligations import router as obligations_router
from app.api.navigator import router as navigator_router
app.include_router(core_router)
app.include_router(analysis_router)
app.include_router(qa_router)
app.include_router(compare_router)
app.include_router(obligations_router)
app.include_router(navigator_router)


@app.get("/")
async def root():
    settings = get_settings()
    return {
        "name": "NyayaLens",
        "tagline": "Read the fine print before it reads you.",
        "version": "0.1.0",
        "demo_mode": settings.demo_mode,
        "disclaimer": "Information, not legal advice.",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
