"""
Ingest router — given a file path or raw content, routes to the right handler.
Returns a dict with at minimum: {"text": str}
"""

import logging
from pathlib import Path
from typing import Optional

from .audio import is_audio, transcribe
from .image import is_image, extract_text as extract_image, detect_screenshot
from .pdf import is_pdf, extract_text as extract_pdf
from .text import is_text_file, extract_from_file, extract_from_url, extract_from_string
from capsule.models import CapsuleSource

logger = logging.getLogger(__name__)


async def ingest_file(
    file_path: str,
    whisper_model: str = "small",
    whisper_device: str = "cuda",
    whisper_language: str = None,
    ocr_languages: list[str] = None,
) -> tuple[CapsuleSource, dict]:
    """
    Detect file type, extract content, return (source_type, extracted_data).
    Single entry point for all file-based ingestion.
    """
    path = Path(file_path)

    if is_audio(file_path):
        logger.info(f"Detected audio: {path.name}")
        data = await transcribe(file_path, whisper_model, whisper_device, whisper_language)
        return CapsuleSource.AUDIO, data

    if is_pdf(file_path):
        logger.info(f"Detected PDF: {path.name}")
        data = await extract_pdf(file_path)
        return CapsuleSource.PDF, data

    if is_image(file_path):
        logger.info(f"Detected image: {path.name}")
        data = await extract_image(file_path, ocr_languages or ["en"])
        source_type = CapsuleSource.SCREENSHOT if detect_screenshot(file_path) else CapsuleSource.IMAGE
        return source_type, data

    if is_text_file(file_path):
        logger.info(f"Detected text file: {path.name}")
        data = await extract_from_file(file_path)
        return CapsuleSource.TEXT, data

    logger.warning(f"Unknown file type: {path.suffix}, attempting text read")
    try:
        data = await extract_from_file(file_path)
        return CapsuleSource.TEXT, data
    except Exception:
        return CapsuleSource.UNKNOWN, {"text": ""}


async def ingest_url(url: str) -> tuple[CapsuleSource, dict]:
    data = await extract_from_url(url)
    return CapsuleSource.URL, data


async def ingest_text(text: str) -> tuple[CapsuleSource, dict]:
    data = extract_from_string(text)
    return CapsuleSource.TEXT, data
