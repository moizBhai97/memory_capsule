"""
Gemini embed provider.
"""

import httpx
import asyncio

from ..base import EmbedProvider


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
            json={"content": {"parts": [{"text": text}]}},
        )
        response.raise_for_status()
        values = response.json().get("embedding", {}).get("values", [])
        if not values:
            raise ValueError("Gemini embedding response missing values")
        self._dim = len(values)
        return values

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
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
