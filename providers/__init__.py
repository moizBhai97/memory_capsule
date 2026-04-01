"""
Provider factory — returns the right LLM + Embed provider based on config.
This is the only place that knows about which provider is active.
Everything else just uses LLMProvider / EmbedProvider interfaces.
"""

import logging
from functools import lru_cache

from config import Config, get_config
from .base import LLMProvider, EmbedProvider

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_llm(config: Config = None) -> LLMProvider:
    """Returns LLM provider singleton based on config."""
    cfg = config or get_config()

    if cfg.provider == "openai":
        if not cfg.openai.api_key:
            raise ValueError("OPENAI_API_KEY not set. Add to config or env.")
        from .openai import OpenAILLM
        logger.info(f"Using OpenAI LLM: {cfg.openai.llm_model}")
        return OpenAILLM(cfg.openai.api_key, cfg.openai.llm_model)

    elif cfg.provider == "anthropic":
        if not cfg.anthropic.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set. Add to config or env.")
        from .anthropic import AnthropicLLM
        logger.info(f"Using Anthropic LLM: {cfg.anthropic.llm_model}")
        return AnthropicLLM(cfg.anthropic.api_key, cfg.anthropic.llm_model)

    elif cfg.provider == "groq":
        if not cfg.groq.api_key:
            raise ValueError("GROQ_API_KEY not set. Add to config or env.")
        from .groq import GroqLLM
        logger.info(f"Using Groq LLM: {cfg.groq.llm_model}")
        return GroqLLM(cfg.groq.api_key, cfg.groq.llm_model)

    else:
        # Default: Ollama (local, free)
        from .ollama import OllamaLLM
        logger.info(f"Using Ollama LLM: {cfg.ollama.llm_model}")
        return OllamaLLM(cfg.ollama.base_url, cfg.ollama.llm_model)


@lru_cache(maxsize=1)
def get_embed(config: Config = None) -> EmbedProvider:
    """
    Returns embed provider singleton.
    Note: Anthropic and Groq don't offer embeddings.
    If those are selected as LLM provider, embeddings still use Ollama.
    This is intentional — best local embed model is nomic-embed-text via Ollama.
    """
    cfg = config or get_config()

    if cfg.provider == "openai":
        from .openai import OpenAIEmbed
        logger.info(f"Using OpenAI embeddings: {cfg.openai.embed_model}")
        return OpenAIEmbed(cfg.openai.api_key, cfg.openai.embed_model)

    # All other providers (ollama, anthropic, groq) use Ollama for embeddings
    from .ollama import OllamaEmbed
    logger.info(f"Using Ollama embeddings: {cfg.ollama.embed_model}")
    return OllamaEmbed(cfg.ollama.base_url, cfg.ollama.embed_model)
