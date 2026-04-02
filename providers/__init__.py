"""
Public provider API — the only surface the rest of the codebase touches.

  get_llm()         → LLMProvider
  get_embed()       → EmbedProvider
  get_transcriber() → TranscriptionProvider (with automatic fallback chain)

Registry, factory functions, and fallback logic live in:
  providers/registry.py
  providers/transcribe/fallback.py
"""

import logging
from functools import lru_cache

from config import Config, get_config, ProviderConfig, API_KEY_ENV
from .base import LLMProvider, EmbedProvider, TranscriptionProvider, TranscriptionResult
from .registry import PROVIDER_REGISTRY, PROVIDER_CATALOG

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve(cfg: ProviderConfig, capability: str):
    entry = PROVIDER_REGISTRY.get(cfg.provider_id)

    if entry and capability in entry:
        logger.info("Using %s/%s for %s", cfg.provider_id, cfg.model_id, capability)
        return entry[capability](cfg)

    # Unknown provider with a base_url → treat as openai-compatible
    if cfg.base_url or PROVIDER_CATALOG.get(cfg.provider_id, {}).get("openai_compatible"):
        if capability in ("llm", "embed"):
            logger.info("Unknown provider '%s' — treating as openai-compatible", cfg.provider_id)
            from .llm.openai_compatible import OpenAICompatibleLLM, OpenAICompatibleEmbed
            return OpenAICompatibleLLM(cfg) if capability == "llm" else OpenAICompatibleEmbed(cfg)

    raise ValueError(
        f"Provider '{cfg.provider_id}' does not support '{capability}'. "
        f"Available: {list(PROVIDER_REGISTRY)}"
    )


def _validate_api_key(cfg: ProviderConfig, capability: str) -> None:
    no_key_needed = {"ollama", "whisper"}
    if cfg.provider_id in no_key_needed:
        return
    if cfg.provider_id == "openai-compatible" and cfg.base_url:
        return  # custom endpoint, key optional
    if not cfg.api_key:
        env_var = API_KEY_ENV.get(cfg.provider_id, f"{cfg.provider_id.upper()}_API_KEY")
        raise ValueError(
            f"API key required for '{cfg.provider_id}'. "
            f"Set {env_var} env var or add api_key to config."
        )


# ---------------------------------------------------------------------------
# Public singletons
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_llm(config: Config = None) -> LLMProvider:
    cfg = (config or get_config()).llm
    _validate_api_key(cfg, "llm")
    return _resolve(cfg, "llm")


@lru_cache(maxsize=1)
def get_embed(config: Config = None) -> EmbedProvider:
    cfg = (config or get_config()).embed
    _validate_api_key(cfg, "embed")
    return _resolve(cfg, "embed")


@lru_cache(maxsize=1)
def get_transcriber(config: Config = None) -> TranscriptionProvider:
    from .transcribe.fallback import FallbackTranscriber

    cfg = (config or get_config()).transcribe
    _validate_api_key(cfg, "transcribe")
    primary = _resolve(cfg, "transcribe")

    return FallbackTranscriber(
        primary=primary,
        primary_provider_id=cfg.provider_id,
        language=cfg.extra.get("language"),
        device=cfg.device,
    )
