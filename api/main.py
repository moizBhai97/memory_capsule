"""
FastAPI REST API — the integration surface for everything.
All integrations (webhooks, SDK, CLI, browser extension) go through here.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_config
from capsule.store.sqlite import SQLiteStore
from capsule.store.vector import VectorStore
from capsule.pipeline import Pipeline
from capsule.search.engine import SearchEngine

logger = logging.getLogger(__name__)

# Shared app state — initialized once on startup
_state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_config()

    # Initialize storage
    sqlite = SQLiteStore(cfg.storage.sqlite_path)
    vector = VectorStore(cfg.storage.chroma_path)
    pipeline = Pipeline(sqlite, vector)
    search = SearchEngine(sqlite, vector)

    _state["sqlite"] = sqlite
    _state["vector"] = vector
    _state["pipeline"] = pipeline
    _state["search"] = search

    # Ensure uploads dir exists
    Path(cfg.storage.uploads_path).mkdir(parents=True, exist_ok=True)

    logger.info(f"API ready — {sqlite.count()} capsules in store")
    yield
    logger.info("API shutting down")


app = FastAPI(
    title="Open Memory Capsule API",
    description="Capture everything. Remember forever. Search naturally.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

cfg = get_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
from api.routes import capsules, search, webhooks, health

app.include_router(health.router, tags=["health"])
app.include_router(capsules.router, prefix="/api/capsules", tags=["capsules"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])


def get_pipeline() -> Pipeline:
    return _state["pipeline"]


def get_search() -> SearchEngine:
    return _state["search"]


def get_sqlite() -> SQLiteStore:
    return _state["sqlite"]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host=cfg.api.host, port=cfg.api.port, reload=cfg.debug)
