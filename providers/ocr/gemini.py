"""
Gemini vision OCR provider.

Uses the Gemini vision API to extract text from images.
Supports the same models as GeminiLLM (gemini-2.0-flash, etc.).
"""

import base64
import logging
from pathlib import Path

import httpx

from ..base import OCRProvider, OCRResult
from ._shared import VISION_PROMPT

logger = logging.getLogger(__name__)


class GeminiOCR(OCRProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self._client = httpx.AsyncClient(timeout=120.0)

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

        logger.info("GeminiOCR on %s via %s", path.name, self.model)

        response = await self._client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            params={"key": self.api_key},
            json={
                "contents": [{
                    "parts": [
                        {"inline_data": {"mime_type": mime, "data": image_data}},
                        {"text": prompt},
                    ],
                }],
                "generationConfig": {"temperature": 0.0},
            },
        )
        response.raise_for_status()
        data = response.json()

        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
        return OCRResult(text=text.strip(), confidence=None, blocks=[])

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
