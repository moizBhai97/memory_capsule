import json

import httpx

from ..base import EmbedProvider, ExtractionResult, LLMProvider
from .prompts import EXTRACTION_PROMPT


class GeminiLLM(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self._client = httpx.AsyncClient(timeout=120.0)

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

        response = await self._client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            params={"key": self.api_key},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.1,
                    "responseMimeType": "application/json",
                },
            },
        )
        response.raise_for_status()
        data = response.json()

        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "{}")
        )
        result = json.loads(text)

        return ExtractionResult(
            summary=result.get("summary", ""),
            tags=[t.lower().replace(" ", "-") for t in result.get("tags", [])[:10]],
            action_items=result.get("action_items", []),
            language=result.get("language", "en"),
            reminders=result.get("reminders", []),
        )

    async def health_check(self) -> bool:
        try:
            r = await self._client.get(
                "https://generativelanguage.googleapis.com/v1beta/models",
                params={"key": self.api_key},
                timeout=10.0,
            )
            return r.status_code == 200
        except Exception:
            return False


class GeminiEmbed(EmbedProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self._client = httpx.AsyncClient(timeout=60.0)
        self._dim: int | None = None

    async def embed(self, text: str) -> list[float]:
        response = await self._client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:embedContent",
            params={"key": self.api_key},
            json={
                "content": {"parts": [{"text": text}]},
            },
        )
        response.raise_for_status()
        data = response.json()
        values = data.get("embedding", {}).get("values", [])
        if not values:
            raise ValueError("Gemini embedding response missing values")
        self._dim = len(values)
        return values

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        # Keep simple and robust: call single-item endpoint concurrently.
        import asyncio

        return await asyncio.gather(*[self.embed(t) for t in texts])

    def dimension(self) -> int:
        return self._dim or 768

    async def health_check(self) -> bool:
        try:
            r = await self._client.get(
                "https://generativelanguage.googleapis.com/v1beta/models",
                params={"key": self.api_key},
                timeout=10.0,
            )
            return r.status_code == 200
        except Exception:
            return False
