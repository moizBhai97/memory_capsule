"""
EasyOCR provider — local neural network OCR.

Model format: "easyocr/en" or "easyocr/en,ar" (comma-separated language codes).
Models are downloaded automatically on first use to ~/.EasyOCR/model/.
Runs on CPU by default to preserve VRAM for Whisper and LLM.
"""

import asyncio
import logging
from pathlib import Path

from ..base import OCRProvider, OCRResult

logger = logging.getLogger(__name__)


class EasyOCRProvider(OCRProvider):
    """
    Local OCR using EasyOCR neural network models.
    model_id is treated as a comma-separated list of language codes: "en", "en,ar", etc.
    languages param in extract_text overrides the model_id languages when provided.
    """

    def __init__(self, model_id: str):
        # model_id doubles as language spec: "en" or "en,ar"
        self._default_languages = [l.strip() for l in model_id.split(",") if l.strip()]
        if not self._default_languages:
            self._default_languages = ["en"]

    async def extract_text(self, file_path: str, languages: list[str] | None = None) -> OCRResult:
        try:
            import easyocr
        except ImportError:
            raise ImportError("Run: pip install easyocr")

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        langs = languages or self._default_languages
        logger.info("EasyOCR on %s (languages: %s)", path.name, langs)

        loop = asyncio.get_running_loop()

        def _run():
            reader = easyocr.Reader(langs, gpu=False, verbose=False)
            return reader.readtext(str(path))

        results = await loop.run_in_executor(None, _run)

        if not results:
            return OCRResult(text="", confidence=0.0, blocks=[])

        blocks = [
            {"text": text, "confidence": float(conf), "bbox": bbox}
            for bbox, text, conf in results
        ]
        full_text = "\n".join(b["text"] for b in blocks if b["confidence"] > 0.3)
        avg_confidence = sum(b["confidence"] for b in blocks) / len(blocks)

        return OCRResult(
            text=full_text.strip(),
            confidence=round(avg_confidence, 2),
            blocks=blocks,
        )

    async def health_check(self) -> bool:
        try:
            import easyocr  # noqa: F401
            return True
        except ImportError:
            return False
