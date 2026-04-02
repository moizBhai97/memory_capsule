"""
Provider registry — maps provider_id to factory callables for each capability.

Adding a new provider = one new entry in PROVIDER_REGISTRY. Nothing else changes.

PROVIDER_CATALOG defines known provider metadata (base_url, openai-compatible flag).
Providers not in the catalog but with a base_url are treated as openai-compatible.
"""

from config import ProviderConfig
from .base import LLMProvider, EmbedProvider, TranscriptionProvider


# ---------------------------------------------------------------------------
# Catalog — known provider metadata
# ---------------------------------------------------------------------------

PROVIDER_CATALOG: dict[str, dict] = {
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",        # Ollama ignores the key but openai SDK requires one
        "openai_compatible": True,
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "openai_compatible": True,
    },
    "openai": {
        "base_url": "",             # uses SDK default
        "openai_compatible": True,
    },
    "anthropic": {
        "base_url": "",
        "openai_compatible": False,
    },
    "gemini": {
        "base_url": "",
        "openai_compatible": False,
    },
    "whisper": {
        "base_url": "",
        "openai_compatible": False,
    },
}


# ---------------------------------------------------------------------------
# Factory functions — private, only used by PROVIDER_REGISTRY below
# ---------------------------------------------------------------------------

def _make_openai_compatible_llm(cfg: ProviderConfig) -> LLMProvider:
    from .llm.openai_compatible import OpenAICompatibleLLM
    return OpenAICompatibleLLM(cfg)


def _make_openai_compatible_embed(cfg: ProviderConfig) -> EmbedProvider:
    from .llm.openai_compatible import OpenAICompatibleEmbed
    return OpenAICompatibleEmbed(cfg)


def _make_anthropic_llm(cfg: ProviderConfig) -> LLMProvider:
    from .llm.anthropic import AnthropicLLM
    return AnthropicLLM(cfg.api_key, cfg.model_id)


def _make_gemini_llm(cfg: ProviderConfig) -> LLMProvider:
    from .llm.gemini import GeminiLLM
    return GeminiLLM(cfg.api_key, cfg.model_id)


def _make_gemini_embed(cfg: ProviderConfig) -> EmbedProvider:
    from .llm.gemini import GeminiEmbed
    return GeminiEmbed(cfg.api_key, cfg.model_id)


def _make_whisper_transcriber(cfg: ProviderConfig) -> TranscriptionProvider:
    from .transcribe.whisper import WhisperTranscriber
    return WhisperTranscriber(
        model_name=cfg.model_id,
        device=cfg.device,
        language=cfg.extra.get("language"),
        cache_dir=cfg.extra.get("cache_dir"),
    )


def _make_openai_transcriber(cfg: ProviderConfig) -> TranscriptionProvider:
    from .transcribe.openai import OpenAITranscriber
    return OpenAITranscriber(
        api_key=cfg.api_key,
        model=cfg.model_id,
        language=cfg.extra.get("language"),
    )


def _make_groq_transcriber(cfg: ProviderConfig) -> TranscriptionProvider:
    # Groq audio API is OpenAI-compatible — same client, different base_url
    from .transcribe.openai import OpenAITranscriber
    return OpenAITranscriber(
        api_key=cfg.api_key,
        model=cfg.model_id or "whisper-large-v3-turbo",
        language=cfg.extra.get("language"),
        base_url=cfg.base_url or PROVIDER_CATALOG["groq"]["base_url"],
    )


def _make_gemini_transcriber(cfg: ProviderConfig) -> TranscriptionProvider:
    from .transcribe.gemini import GeminiTranscriber
    return GeminiTranscriber(
        api_key=cfg.api_key,
        model=cfg.model_id,
        language=cfg.extra.get("language"),
    )


# ---------------------------------------------------------------------------
# Registry — provider_id → capabilities
# ---------------------------------------------------------------------------

PROVIDER_REGISTRY: dict[str, dict] = {
    "openai": {
        "llm": _make_openai_compatible_llm,
        "embed": _make_openai_compatible_embed,
        "transcribe": _make_openai_transcriber,
    },
    "groq": {
        "llm": _make_openai_compatible_llm,
        "embed": _make_openai_compatible_embed,
        "transcribe": _make_groq_transcriber,
    },
    "ollama": {
        "llm": _make_openai_compatible_llm,
        "embed": _make_openai_compatible_embed,
    },
    "openai-compatible": {
        "llm": _make_openai_compatible_llm,
        "embed": _make_openai_compatible_embed,
    },
    "anthropic": {
        "llm": _make_anthropic_llm,
        # no embed — falls back to ollama
    },
    "gemini": {
        "llm": _make_gemini_llm,
        "embed": _make_gemini_embed,
        "transcribe": _make_gemini_transcriber,
    },
    "whisper": {
        "transcribe": _make_whisper_transcriber,
    },
}
