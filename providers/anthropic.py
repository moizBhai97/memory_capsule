"""
Anthropic provider — paid, cloud, excellent at structured extraction.
"""

import json
import logging

from .base import EmbedProvider, ExtractionResult, LLMProvider, EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


class AnthropicLLM(LLMProvider):
    def __init__(self, api_key: str, model: str):
        try:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=api_key)
        except ImportError:
            raise ImportError("Run: pip install anthropic")
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
            raw_content=raw_content[:8000],
        )

        response = await self._client.messages.create(
            model=self.model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )

        result = json.loads(response.content[0].text)
        return ExtractionResult(
            summary=result.get("summary", ""),
            tags=[t.lower().replace(" ", "-") for t in result.get("tags", [])[:10]],
            action_items=result.get("action_items", []),
            language=result.get("language", "en"),
            reminders=result.get("reminders", []),
        )

    async def health_check(self) -> bool:
        try:
            # Minimal check — just verify client initializes
            return self._client is not None
        except Exception:
            return False


# Anthropic doesn't offer embeddings — use Ollama or OpenAI for that
class AnthropicEmbed(EmbedProvider):
    """Placeholder — Anthropic has no embedding API. Falls back to Ollama."""

    def __init__(self):
        raise NotImplementedError(
            "Anthropic does not provide embeddings. "
            "Set embed_provider: ollama in config (can mix providers)."
        )

    async def embed(self, text: str) -> list[float]: ...
    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...
    def dimension(self) -> int: ...
    async def health_check(self) -> bool: ...
