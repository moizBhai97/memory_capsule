"""
Shared AsyncOpenAI client builder used by all openai-compatible providers
(llm, embed, ocr). Resolves api_key and base_url from config + catalog.
"""

from config import ProviderConfig


def build_openai_client(cfg: ProviderConfig):
    try:
        from openai import AsyncOpenAI
    except ImportError:
        raise ImportError("Run: pip install openai")

    from .registry import PROVIDER_CATALOG
    catalog = PROVIDER_CATALOG.get(cfg.provider_id, {})
    api_key = cfg.api_key or catalog.get("api_key") or "no-key"
    base_url = cfg.base_url or catalog.get("base_url") or None

    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return AsyncOpenAI(**kwargs)
