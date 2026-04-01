"""
Groq provider — free tier available, extremely fast inference.
Great middle ground: free + cloud quality + speed.
Uses OpenAI-compatible API so minimal code.
"""

import json
import logging

from .base import EmbedProvider, ExtractionResult, LLMProvider, EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


class GroqLLM(LLMProvider):
    def __init__(self, api_key: str, model: str):
        try:
            from groq import AsyncGroq
            self._client = AsyncGroq(api_key=api_key)
        except ImportError:
            raise ImportError("Run: pip install groq")
        self.model = model

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
            raw_content=raw_content[:6000],
        )

        response = await self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=512,
        )

        result = json.loads(response.choices[0].message.content)
        return ExtractionResult(
            summary=result.get("summary", ""),
            tags=[t.lower().replace(" ", "-") for t in result.get("tags", [])[:10]],
            action_items=result.get("action_items", []),
            language=result.get("language", "en"),
            reminders=result.get("reminders", []),
        )

    async def health_check(self) -> bool:
        try:
            models = await self._client.models.list()
            return True
        except Exception:
            return False


# Groq has no embedding API — use Ollama for embeddings
class GroqEmbed(EmbedProvider):
    def __init__(self):
        raise NotImplementedError(
            "Groq does not provide embeddings. "
            "Embeddings will use Ollama automatically."
        )

    async def embed(self, text: str) -> list[float]: ...
    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...
    def dimension(self) -> int: ...
    async def health_check(self) -> bool: ...
