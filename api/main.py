"""
FastAPI REST API — the integration surface for everything.
All integrations (webhooks, SDK, CLI, browser extension) go through here.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import state
from api.routes import capsules, search, webhooks, health
from config import get_config
from capsule.store.sqlite import SQLiteStore
from capsule.store.vector import VectorStore
from capsule.pipeline import Pipeline
from capsule.search.engine import SearchEngine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_config()

    sqlite = SQLiteStore(cfg.storage.sqlite_path)
    vector = VectorStore(cfg.storage.chroma_path)
    pipeline = Pipeline(sqlite, vector)
    engine = SearchEngine(sqlite, vector)

    state.init(sqlite, pipeline, engine)

    Path(cfg.storage.uploads_path).mkdir(parents=True, exist_ok=True)

    logger.info("API ready — %s capsules in store", sqlite.count())
    yield
    logger.info("API shutting down")


cfg = get_config()

app = FastAPI(
    title="Open Memory Capsule API",
    description="Capture everything. Remember forever. Search naturally.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(capsules.router, prefix="/api/capsules", tags=["capsules"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host=cfg.api.host, port=cfg.api.port, reload=cfg.debug)
