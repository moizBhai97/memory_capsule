"""
PDF ingestion — extracts text from PDFs using PyMuPDF.
Falls back to OCR for scanned/image-only PDFs.
No GPU needed. Fast and reliable.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def is_pdf(file_path: str) -> bool:
    return Path(file_path).suffix.lower() == ".pdf"


async def extract_text(file_path: str) -> dict:
    """
    Extract text from PDF.
    Returns: {"text": str, "pages": int, "is_scanned": bool, "metadata": dict}

    Strategy:
    1. Try PyMuPDF direct text extraction (fast, accurate for text PDFs)
    2. If extracted text is too short (scanned PDF), fall back to OCR
    """
    import fitz  # PyMuPDF

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    logger.info(f"Extracting text from {path.name}")

    doc = fitz.open(str(path))
    pages = []
    total_text = ""

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        pages.append({"page": page_num + 1, "text": text.strip()})
        total_text += text + "\n"

    pdf_metadata = doc.metadata or {}
    doc.close()

    total_text = total_text.strip()
    is_scanned = len(total_text) < 100  # very little text = likely scanned

    # If scanned, try OCR on each page as image
    if is_scanned:
        logger.info(f"{path.name} appears scanned, running OCR fallback")
        total_text = await _ocr_pdf(file_path)

    return {
        "text": total_text,
        "pages": len(pages),
        "is_scanned": is_scanned,
        "metadata": {
            "title": pdf_metadata.get("title", ""),
            "author": pdf_metadata.get("author", ""),
            "subject": pdf_metadata.get("subject", ""),
            "creator": pdf_metadata.get("creator", ""),
        },
    }


async def _ocr_pdf(file_path: str) -> str:
    """Convert PDF pages to images and run OCR."""
    import fitz
    import asyncio
    from .image import extract_text as ocr_image
    import tempfile
    import os

    doc = fitz.open(file_path)
    all_text = []

    with tempfile.TemporaryDirectory() as tmpdir:
        for page_num in range(min(len(doc), 20)):  # cap at 20 pages for sanity
            page = doc[page_num]
            # Render at 2x for better OCR accuracy
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            img_path = os.path.join(tmpdir, f"page_{page_num}.png")
            pix.save(img_path)

            result = await ocr_image(img_path)
            if result["text"]:
                all_text.append(result["text"])

    doc.close()
    return "\n\n".join(all_text)
