"""
Image ingestion — extracts text from images and screenshots via the configured OCR provider.
Default provider is EasyOCR (local). Override via config: ocr.model: "openai/gpt-4o-mini" etc.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp", ".gif"}


def is_image(file_path: str) -> bool:
    return Path(file_path).suffix.lower() in SUPPORTED_EXTENSIONS


async def extract_text(file_path: str, languages: list[str] | None = None) -> dict:
    """
    Extract text from image using the configured OCR provider.
    Returns: {"text": str, "confidence": float | None, "blocks": list}
    """
    from providers import get_ocr

    ocr = get_ocr()
    result = await ocr.extract_text(file_path, languages=languages)

    return {
        "text": result.text,
        "confidence": result.confidence,
        "blocks": result.blocks,
    }


def detect_screenshot(file_path: str) -> bool:
    """
    Heuristic: is this image a screenshot vs a photo?
    Screenshots are typically PNG with screen-like aspect ratios.
    """
    path = Path(file_path)

    if path.suffix.lower() != ".png":
        return False

    try:
        from PIL import Image
        with Image.open(path) as img:
            w, h = img.size
            ratio = w / h
            common_ratios = [16/9, 16/10, 4/3, 9/16, 21/9]
            return any(abs(ratio - r) < 0.1 for r in common_ratios)
    except Exception:
        return False
