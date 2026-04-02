"""
Anthropic OCR provider.

Uses Claude's vision capability to extract text from images.
Supports any Claude model with vision: claude-opus-4-6, claude-sonnet-4-6, claude-haiku-4-5, etc.
"""

import base64
import logging
from pathlib import Path

from ..base import OCRProvider, OCRResult
from ._shared import VISION_PROMPT

logger = logging.getLogger(__name__)


class AnthropicOCR(OCRProvider):
    def __init__(self, api_key: str, model: str):
        try:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=api_key)
        except ImportError:
            raise ImportError("Run: pip install anthropic")
        self.model = model

    async def extract_text(self, file_path: str, languages: list[str] | None = None) -> OCRResult:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        with open(path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")

        suffix = path.suffix.lower().lstrip(".")
        media_type = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                      "webp": "image/webp", "gif": "image/gif"}.get(suffix, "image/png")

        prompt = VISION_PROMPT
        if languages:
            prompt += f" The image may contain text in: {', '.join(languages)}."

        logger.info("AnthropicOCR on %s via %s", path.name, self.model)

        response = await self._client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }],
        )

        text = response.content[0].text if response.content else ""
        return OCRResult(text=text.strip(), confidence=None, blocks=[])

    async def health_check(self) -> bool:
        return self._client is not None
