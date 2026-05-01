"""FastAPI entry point."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes import interactions, reports
from app.config import settings
from app.core.snp_catalog import summary as catalog_summary
from app.db.session import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("syntrx.api")


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    try:
        init_db()
    except Exception as e:
        log.warning("init_db skipped: %s", e)
    log.info("Syntrx %s starting (LLM=%s, catalog=%s)",
             __version__, settings.llm_provider, catalog_summary())
    yield


app = FastAPI(
    title="Syntrx API",
    description="AI-powered personalized medicine from your DNA.",
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reports.router, prefix="/api")
app.include_router(interactions.router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "llm_provider": os.getenv("LLM_PROVIDER", "mock"),
        "catalog": catalog_summary(),
    }


@app.get("/")
def root() -> dict:
    return {
        "name": "Syntrx",
        "tagline": "AI-powered personalized medicine from your DNA.",
        "docs": "/docs",
    }
