"""
OpenAI-compatible OCR provider.

Uses any OpenAI-compatible vision LLM to extract text from images.
One class handles: openai/gpt-4o, openai/gpt-4o-mini, groq/llama-vision, ollama/llava, etc.

When to use over EasyOCR:
- Better at understanding context (receipts, forms, mixed layouts)
- No separate model download
- Costs tokens — not free
- Requires a vision-capable model
"""

import base64
import logging
from pathlib import Path

from ..base import OCRProvider, OCRResult
from config import ProviderConfig
from .._openai_client import build_openai_client
from ._shared import VISION_PROMPT

logger = logging.getLogger(__name__)


class OpenAICompatibleOCR(OCRProvider):
    """
    OCR via any OpenAI-compatible vision LLM.
    languages param is passed as a hint in the prompt when provided.
    """

    def __init__(self, cfg: ProviderConfig):
        self._client = build_openai_client(cfg)
        self.model = cfg.model_id
        self.provider_id = cfg.provider_id

    async def extract_text(self, file_path: str, languages: list[str] | None = None) -> OCRResult:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        with open(path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")

        suffix = path.suffix.lower().lstrip(".")
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                "webp": "image/webp", "gif": "image/gif"}.get(suffix, "image/png")

        prompt = VISION_PROMPT
        if languages:
            prompt += f" The image may contain text in: {', '.join(languages)}."

        logger.info("OpenAICompatibleOCR on %s via %s/%s", path.name, self.provider_id, self.model)

        response = await self._client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_data}"}},
                    {"type": "text", "text": prompt},
                ],
            }],
            max_tokens=1024,
            temperature=0.0,
        )

        text = response.choices[0].message.content or ""
        return OCRResult(text=text.strip(), confidence=None, blocks=[])

    async def health_check(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False
