"""
OpenAI-compatible LLM + Embed provider.

Handles any provider that speaks the OpenAI Chat Completions API:
  - openai/*       → api.openai.com (SDK default)
  - groq/*         → api.groq.com/openai/v1
  - ollama/*       → localhost:11434/v1
  - openai-compatible/*  → user-supplied base_url

All of these use the same openai.AsyncOpenAI client, just with different
base_url and api_key values pulled from PROVIDER_CATALOG or config.
"""

import json
import logging

from ..base import EmbedProvider, LLMResult, LLMProvider
from .prompts import EXTRACTION_PROMPT
from config import ProviderConfig
from ..registry import PROVIDER_CATALOG

logger = logging.getLogger(__name__)


def _parse_json_response(content: str) -> dict:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        if start == -1:
            raise

        decoder = json.JSONDecoder()
        parsed, _ = decoder.raw_decode(content[start:])
        return parsed


def _build_client(cfg: ProviderConfig):
    try:
        from openai import AsyncOpenAI
    except ImportError:
        raise ImportError("Run: pip install openai")

    catalog = PROVIDER_CATALOG.get(cfg.provider_id, {})

    api_key = cfg.api_key or catalog.get("api_key") or "no-key"
    base_url = cfg.base_url or catalog.get("base_url") or None

    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url

    return AsyncOpenAI(**kwargs)


class OpenAICompatibleLLM(LLMProvider):
    """
    Single LLM provider class for all OpenAI-compatible backends.
    Instantiated with a ProviderConfig — provider_id and model_id are parsed
    from the "provider/model" string.
    """

    def __init__(self, cfg: ProviderConfig):
        self._client = _build_client(cfg)
        self.model = cfg.model_id
        self.provider_id = cfg.provider_id

    async def extract_capsule_info(
        self,
        raw_content: str,
        source_app: str,
        source_sender: str | None = None,
        source_type: str = "unknown",
    ) -> LLMResult:
        sender_line = f"Sender: {source_sender}" if source_sender else ""
        prompt = EXTRACTION_PROMPT.format(
            source_app=source_app,
            sender_line=sender_line,
            source_type=source_type,
            raw_content=raw_content[:8000],
        )

        kwargs = dict(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=512,
        )

        # Ollama's OpenAI-compatible endpoint doesn't support response_format yet
        if self.provider_id not in ("ollama",):
            kwargs["response_format"] = {"type": "json_object"}

        response = await self._client.chat.completions.create(**kwargs)
        result = _parse_json_response(response.choices[0].message.content)

        return LLMResult(
            summary=result.get("summary", ""),
            tags=[t.lower().replace(" ", "-") for t in result.get("tags", [])[:10]],
            action_items=result.get("action_items", []),
            language=result.get("language", "en"),
            reminders=result.get("reminders", []),
        )

    async def health_check(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False


class OpenAICompatibleEmbed(EmbedProvider):
    """Embed provider for all OpenAI-compatible backends."""

    def __init__(self, cfg: ProviderConfig):
        self._client = _build_client(cfg)
        self.model = cfg.model_id
        # dimension varies by model; we detect lazily on first call
        self._dim: int | None = None

    async def embed(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(model=self.model, input=text)
        vec = response.data[0].embedding
        self._dim = len(vec)
        return vec

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(model=self.model, input=texts)
        vecs = [d.embedding for d in sorted(response.data, key=lambda x: x.index)]
        if vecs:
            self._dim = len(vecs[0])
        return vecs

    def dimension(self) -> int:
        # Known defaults; updated lazily after first embed call
        known = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
            "nomic-embed-text:latest": 768,
            "nomic-embed-text": 768,
            "mxbai-embed-large": 1024,
        }
        return self._dim or known.get(self.model, 768)

    async def health_check(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False
