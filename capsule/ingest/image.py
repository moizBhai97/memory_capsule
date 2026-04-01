"""
Image ingestion — extracts text from images and screenshots using EasyOCR.
EasyOCR chosen over Tesseract because it handles real-world images better
(phone screenshots, bank slips, receipts, handwriting, mixed languages).
Runs on CPU — saves GPU for Whisper and LLM.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp", ".gif"}


def is_image(file_path: str) -> bool:
    return Path(file_path).suffix.lower() in SUPPORTED_EXTENSIONS


async def extract_text(file_path: str, languages: list[str] = None) -> dict:
    """
    Extract text from image using EasyOCR.
    Returns: {"text": str, "confidence": float, "blocks": list}

    languages: list of language codes e.g. ["en", "ar"] for English + Arabic
    Defaults to English only. Add more languages in config for multilingual support.
    """
    import easyocr
    import asyncio

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {file_path}")

    if languages is None:
        languages = ["en"]

    logger.info(f"Running OCR on {path.name} (languages: {languages})")

    # EasyOCR is synchronous — run in thread pool to not block async loop
    loop = asyncio.get_event_loop()

    def _run_ocr():
        # gpu=False — saves VRAM for Whisper + LLM
        reader = easyocr.Reader(languages, gpu=False, verbose=False)
        results = reader.readtext(str(path))
        return results

    results = await loop.run_in_executor(None, _run_ocr)

    if not results:
        return {"text": "", "confidence": 0.0, "blocks": []}

    blocks = [
        {
            "text": text,
            "confidence": float(conf),
            "bbox": bbox,
        }
        for bbox, text, conf in results
    ]

    # Join all text blocks into readable string
    full_text = "\n".join(b["text"] for b in blocks if b["confidence"] > 0.3)
    avg_confidence = sum(b["confidence"] for b in blocks) / len(blocks)

    return {
        "text": full_text.strip(),
        "confidence": round(avg_confidence, 2),
        "blocks": blocks,
    }


def detect_screenshot(file_path: str) -> bool:
    """
    Heuristic to detect if an image is a screenshot vs a photo.
    Screenshots are typically: PNG, have screen-like dimensions, come from screenshot folders.
    Used to set source_type correctly.
    """
    path = Path(file_path)

    # PNG is most common screenshot format
    if path.suffix.lower() != ".png":
        return False

    # Check dimensions — screenshots match screen aspect ratios
    try:
        from PIL import Image
        with Image.open(path) as img:
            w, h = img.size
            ratio = w / h
            # Common screen ratios: 16:9 (1.77), 16:10 (1.6), 4:3 (1.33), 9:16 (0.56 mobile)
            common_ratios = [16/9, 16/10, 4/3, 9/16, 21/9]
            is_screen_ratio = any(abs(ratio - r) < 0.1 for r in common_ratios)
            return is_screen_ratio
    except Exception:
        return False
