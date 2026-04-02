"""
OpenAI-compatible embed provider.

Handles any provider that speaks the OpenAI Embeddings API:
  - openai/*            → api.openai.com
  - groq/*              → api.groq.com/openai/v1  (no embed — groq doesn't support it)
  - ollama/*            → localhost:11434/v1
  - openai-compatible/* → user-supplied base_url
"""

from ..base import EmbedProvider
from config import ProviderConfig
from .._openai_client import build_openai_client


# Known embedding dimensions — updated lazily after first call if unknown.
_KNOWN_DIMENSIONS: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
    "nomic-embed-text:latest": 768,
    "nomic-embed-text": 768,
    "mxbai-embed-large": 1024,
}


class OpenAICompatibleEmbed(EmbedProvider):
    """Embed provider for all OpenAI-compatible backends."""

    def __init__(self, cfg: ProviderConfig):
        self._client = build_openai_client(cfg)
        self.model = cfg.model_id
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
        return self._dim or _KNOWN_DIMENSIONS.get(self.model, 768)

    async def health_check(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False
