"""
Integration test for the full pipeline.
Uses a real SQLite + ChromaDB (temp dirs) but mocks AI providers.
"""

import asyncio
import os
import tempfile
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from capsule.models import CapsuleStatus, SourceApp
from capsule.store.sqlite import SQLiteStore
from capsule.store.vector import VectorStore
from capsule.pipeline import Pipeline


@pytest.fixture
def tmp_dirs():
    with tempfile.TemporaryDirectory() as d:
        yield {
            "sqlite": os.path.join(d, "test.db"),
            "chroma": os.path.join(d, "chroma"),
            "uploads": os.path.join(d, "uploads"),
        }


@pytest.fixture
def stores(tmp_dirs):
    sqlite = SQLiteStore(tmp_dirs["sqlite"])
    vector = VectorStore(tmp_dirs["chroma"])
    return sqlite, vector


@pytest.mark.asyncio
async def test_pipeline_text(stores, tmp_dirs, monkeypatch):
    """Test full pipeline with mocked AI providers."""
    sqlite, vector = stores

    # Mock config
    mock_cfg = MagicMock()
    mock_cfg.storage.uploads_path = tmp_dirs["uploads"]

    monkeypatch.setattr("capsule.pipeline.get_config", lambda: mock_cfg)

    # Mock LLM provider
    from providers.base import LLMResult
    mock_llm = AsyncMock()
    mock_llm.extract_capsule_info.return_value = LLMResult(
        summary="Client confirmed $15k budget for the website project",
        tags=["ahmed", "budget", "15k", "website"],
        action_items=["Follow up by Friday"],
        language="en",
    )
    monkeypatch.setattr("capsule.pipeline.get_llm", lambda: mock_llm)

    # Mock embed provider
    mock_embed = AsyncMock()
    mock_embed.embed.return_value = [0.1] * 768
    monkeypatch.setattr("capsule.pipeline.get_embed", lambda: mock_embed)

    pipeline = Pipeline(sqlite, vector)

    capsule = await pipeline.process_text(
        text="Hey, just confirming the budget is $15k for the website",
        source_app=SourceApp.WHATSAPP_PERSONAL,
        source_sender="Ahmed",
        source_chat="Ahmed Client",
    )

    assert capsule.status == CapsuleStatus.READY
    assert capsule.summary == "Client confirmed $15k budget for the website project"
    assert "ahmed" in capsule.tags
    assert "Follow up by Friday" in capsule.action_items

    # Verify it was stored
    stored = sqlite.get(capsule.id)
    assert stored is not None
    assert stored.source_sender == "Ahmed"

    # Verify vector was stored
    assert vector.count() == 1


@pytest.mark.asyncio
async def test_pipeline_stores_and_retrieves(stores, tmp_dirs, monkeypatch):
    """Test that stored capsule can be retrieved."""
    sqlite, vector = stores

    mock_cfg = MagicMock()
    mock_cfg.storage.uploads_path = tmp_dirs["uploads"]

    monkeypatch.setattr("capsule.pipeline.get_config", lambda: mock_cfg)

    from providers.base import LLMResult
    mock_llm = AsyncMock()
    mock_llm.extract_capsule_info.return_value = LLMResult(
        summary="Test summary", tags=["test"], action_items=[], language="en"
    )
    monkeypatch.setattr("capsule.pipeline.get_llm", lambda: mock_llm)
    mock_embed = AsyncMock()
    mock_embed.embed.return_value = [0.5] * 768
    monkeypatch.setattr("capsule.pipeline.get_embed", lambda: mock_embed)

    pipeline = Pipeline(sqlite, vector)
    capsule = await pipeline.process_text(
        text="Test content",
        source_app=SourceApp.CLI,
    )

    all_capsules = sqlite.list(limit=10)
    assert len(all_capsules) == 1
    assert all_capsules[0].id == capsule.id
