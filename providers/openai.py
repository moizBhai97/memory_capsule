"""
OpenAI provider — paid, cloud, best quality.
Switch to this when you want better summaries/tags.
"""

import json
import logging

from .base import EmbedProvider, ExtractionResult, LLMProvider, EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


class OpenAILLM(LLMProvider):
    def __init__(self, api_key: str, model: str):
        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=api_key)
        except ImportError:
            raise ImportError("Run: pip install openai")
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

        response = await self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
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


class OpenAIEmbed(EmbedProvider):
    def __init__(self, api_key: str, model: str):
        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=api_key)
        except ImportError:
            raise ImportError("Run: pip install openai")
        self.model = model
        self._dim = 1536 if "3-small" in model else 3072

    async def embed(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(
            model=self.model,
            input=text,
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(
            model=self.model,
            input=texts,
        )
        return [d.embedding for d in sorted(response.data, key=lambda x: x.index)]

    def dimension(self) -> int:
        return self._dim

    async def health_check(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False
