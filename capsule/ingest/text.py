"""
Text ingestion — handles plain text, URLs, and email bodies.
The simplest handler but still does meaningful cleanup.
"""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".xml", ".html", ".htm"}


def is_text_file(file_path: str) -> bool:
    return Path(file_path).suffix.lower() in TEXT_EXTENSIONS


async def extract_from_file(file_path: str) -> dict:
    """Read and clean text from a file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        raw = f.read()

    suffix = path.suffix.lower()

    if suffix in (".html", ".htm"):
        text = _strip_html(raw)
    else:
        text = raw

    return {"text": _clean(text)}


async def extract_from_url(url: str) -> dict:
    """
    Fetch and extract text from a URL.
    Simple fetch for now. Future: swap for Crawl4AI for better extraction.
    """
    import httpx
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if not parsed.scheme:
        raise ValueError(f"Invalid URL: {url}")

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")

        if "pdf" in content_type:
            # Save and process as PDF
            import tempfile, os
            from .pdf import extract_text as extract_pdf
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(response.content)
                tmp_path = f.name
            try:
                return await extract_pdf(tmp_path)
            finally:
                os.unlink(tmp_path)

        text = _strip_html(response.text)

    return {
        "text": _clean(text),
        "url": url,
        "domain": parsed.netloc,
    }


def extract_from_string(text: str) -> dict:
    """Process raw text string — used by API, webhooks, CLI."""
    return {"text": _clean(text)}


def _strip_html(html: str) -> str:
    """Remove HTML tags, keep readable text."""
    # Remove scripts and styles first
    html = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    # Remove all tags
    html = re.sub(r"<[^>]+>", " ", html)
    # Decode common HTML entities
    html = html.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return html


def _clean(text: str) -> str:
    """Normalize whitespace, remove junk."""
    # Collapse multiple newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse multiple spaces
    text = re.sub(r" {2,}", " ", text)
    return text.strip()
