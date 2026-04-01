"""
Ollama provider — free, local, runs on your GPU.
Default provider. No API key needed. 100% private.

Models used:
- LLM: phi3.5:mini — best small instruction model, fits in 4GB VRAM
- Embed: nomic-embed-text — best open embedding model at its size
"""

import json
import logging
from typing import Any

import httpx

from .base import EmbedProvider, ExtractionResult, LLMProvider, EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


class OllamaLLM(LLMProvider):
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = httpx.AsyncClient(timeout=120.0)  # LLM calls can be slow on small GPU

    async def extract_capsule_info(
        self,
        raw_content: str,
        source_app: str,
        source_sender: str | None = None,
        source_type: str = "unknown",
    ) -> ExtractionResult:
        sender_line = f"Sender: {source_sender}" if source_sender else ""
        prompt = EXTRACTION_PROMPT.format(
            source_app=source_app,
            sender_line=sender_line,
            source_type=source_type,
            raw_content=raw_content[:4000],  # cap to avoid context overflow on small models
        )

        try:
            response = await self._client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",   # Ollama structured output — ensures valid JSON
                    "options": {
                        "temperature": 0.1,  # low temp for consistent extraction
                        "num_predict": 512,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
            result = json.loads(data["response"])
            return _parse_extraction(result)

        except json.JSONDecodeError as e:
            logger.warning(f"Ollama returned invalid JSON: {e}. Falling back to defaults.")
            return _fallback_extraction(raw_content)
        except httpx.HTTPError as e:
            logger.error(f"Ollama request failed: {e}")
            raise

    async def health_check(self) -> bool:
        try:
            r = await self._client.get(f"{self.base_url}/api/tags", timeout=5.0)
            return r.status_code == 200
        except Exception:
            return False


class OllamaEmbed(EmbedProvider):
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = httpx.AsyncClient(timeout=30.0)
        self._dim = 768  # nomic-embed-text dimension

    async def embed(self, text: str) -> list[float]:
        response = await self._client.post(
            f"{self.base_url}/api/embeddings",
            json={"model": self.model, "prompt": text},
        )
        response.raise_for_status()
        return response.json()["embedding"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        # Ollama doesn't have native batch — run concurrently
        import asyncio
        return await asyncio.gather(*[self.embed(t) for t in texts])

    def dimension(self) -> int:
        return self._dim

    async def health_check(self) -> bool:
        try:
            r = await self._client.get(f"{self.base_url}/api/tags", timeout=5.0)
            return r.status_code == 200
        except Exception:
            return False


def _parse_extraction(data: dict) -> ExtractionResult:
    return ExtractionResult(
        summary=data.get("summary", ""),
        tags=[t.lower().replace(" ", "-") for t in data.get("tags", [])[:10]],
        action_items=data.get("action_items", []),
        language=data.get("language", "en"),
        reminders=data.get("reminders", []),
    )


def _fallback_extraction(raw_content: str) -> ExtractionResult:
    """Used when LLM fails. Returns minimal valid result."""
    words = raw_content.split()[:10]
    return ExtractionResult(
        summary=raw_content[:200] if raw_content else "No content",
        tags=[],
        action_items=[],
        language="en",
        reminders=[],
    )
