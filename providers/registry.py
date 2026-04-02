"""
Provider registry — maps provider_id to factory callables for each capability.

Adding a new provider  = one new entry in PROVIDER_REGISTRY + PROVIDER_CATALOG.
Adding a new capability = one new key in the relevant registry entries.
Nothing else changes.

Capability keys: "llm" | "embed" | "transcribe" | "ocr"
"""

from config import ProviderConfig
from .base import LLMProvider, EmbedProvider, TranscriptionProvider, OCRProvider


# ---------------------------------------------------------------------------
# Catalog — known provider metadata + capability flags
# ---------------------------------------------------------------------------

PROVIDER_CATALOG: dict[str, dict] = {
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",        # Ollama ignores the key but openai SDK requires one
        "openai_compatible": True,
        "supports_vision": True,    # llava and other vision models available
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "openai_compatible": True,
        "supports_vision": True,
        "default_transcribe_model": "whisper-large-v3-turbo",
    },
    "openai": {
        "base_url": "",
        "openai_compatible": True,
        "supports_vision": True,
    },
    "anthropic": {
        "base_url": "",
        "openai_compatible": False,
        "supports_vision": True,
    },
    "gemini": {
        "base_url": "",
        "openai_compatible": False,
        "supports_vision": True,
    },
    "whisper": {
        "base_url": "",
        "openai_compatible": False,
        "supports_vision": False,
    },
    "easyocr": {
        "base_url": "",
        "openai_compatible": False,
        "supports_vision": False,
    },
    "openai-compatible": {
        "base_url": "",
        "openai_compatible": True,
        "supports_vision": True,    # assumed — user picks a vision model if needed
    },
}


# ---------------------------------------------------------------------------
# Factory functions — private, only used by PROVIDER_REGISTRY below
# ---------------------------------------------------------------------------

# --- LLM ---

def _make_openai_compatible_llm(cfg: ProviderConfig) -> LLMProvider:
    from .llm.openai_compatible import OpenAICompatibleLLM
    return OpenAICompatibleLLM(cfg)


def _make_anthropic_llm(cfg: ProviderConfig) -> LLMProvider:
    from .llm.anthropic import AnthropicLLM
    return AnthropicLLM(cfg.api_key, cfg.model_id)


def _make_gemini_llm(cfg: ProviderConfig) -> LLMProvider:
    from .llm.gemini import GeminiLLM
    return GeminiLLM(cfg.api_key, cfg.model_id)


# --- Embed ---

def _make_openai_compatible_embed(cfg: ProviderConfig) -> EmbedProvider:
    from .embed.openai_compatible import OpenAICompatibleEmbed
    return OpenAICompatibleEmbed(cfg)


def _make_gemini_embed(cfg: ProviderConfig) -> EmbedProvider:
    from .embed.gemini import GeminiEmbed
    return GeminiEmbed(cfg.api_key, cfg.model_id)


# --- Transcribe ---

def _make_whisper_transcriber(cfg: ProviderConfig) -> TranscriptionProvider:
    from .transcribe.whisper import WhisperTranscriber
    return WhisperTranscriber(
        model_name=cfg.model_id,
        device=cfg.device,
        language=cfg.extra.get("language"),
        cache_dir=cfg.extra.get("cache_dir"),
    )


def _make_openai_compatible_transcriber(cfg: ProviderConfig) -> TranscriptionProvider:
    from .transcribe.openai_compatible import OpenAICompatibleTranscriber
    return OpenAICompatibleTranscriber(
        api_key=cfg.api_key,
        model=cfg.model_id,
        language=cfg.extra.get("language"),
    )


def _make_groq_transcriber(cfg: ProviderConfig) -> TranscriptionProvider:
    from .transcribe.openai_compatible import OpenAICompatibleTranscriber
    groq = PROVIDER_CATALOG["groq"]
    return OpenAICompatibleTranscriber(
        api_key=cfg.api_key,
        model=cfg.model_id or groq["default_transcribe_model"],
        language=cfg.extra.get("language"),
        base_url=cfg.base_url or groq["base_url"],
    )


def _make_gemini_transcriber(cfg: ProviderConfig) -> TranscriptionProvider:
    from .transcribe.gemini import GeminiTranscriber
    return GeminiTranscriber(
        api_key=cfg.api_key,
        model=cfg.model_id,
        language=cfg.extra.get("language"),
    )


# --- OCR ---

def _make_anthropic_ocr(cfg: ProviderConfig) -> OCRProvider:
    from .ocr.anthropic import AnthropicOCR
    return AnthropicOCR(cfg.api_key, cfg.model_id)


def _make_easyocr(cfg: ProviderConfig) -> OCRProvider:
    from .ocr.easyocr import EasyOCRProvider
    return EasyOCRProvider(cfg.model_id)


def _make_openai_compatible_ocr(cfg: ProviderConfig) -> OCRProvider:
    from .ocr.openai_compatible import OpenAICompatibleOCR
    return OpenAICompatibleOCR(cfg)


def _make_gemini_ocr(cfg: ProviderConfig) -> OCRProvider:
    from .ocr.gemini import GeminiOCR
    return GeminiOCR(cfg.api_key, cfg.model_id)


# ---------------------------------------------------------------------------
# Registry — provider_id → capabilities
# ---------------------------------------------------------------------------

PROVIDER_REGISTRY: dict[str, dict] = {
    "openai": {
        "llm":       _make_openai_compatible_llm,
        "embed":     _make_openai_compatible_embed,
        "transcribe": _make_openai_compatible_transcriber,
        "ocr":       _make_openai_compatible_ocr,
    },
    "groq": {
        "llm":       _make_openai_compatible_llm,
        "embed":     _make_openai_compatible_embed,
        "transcribe": _make_groq_transcriber,
        "ocr":       _make_openai_compatible_ocr,
    },
    "ollama": {
        "llm":       _make_openai_compatible_llm,
        "embed":     _make_openai_compatible_embed,
        "ocr":       _make_openai_compatible_ocr,
    },
    "openai-compatible": {
        "llm":       _make_openai_compatible_llm,
        "embed":     _make_openai_compatible_embed,
        "ocr":       _make_openai_compatible_ocr,
    },
    "anthropic": {
        "llm":       _make_anthropic_llm,
        "ocr":       _make_anthropic_ocr,
        # no embed — falls back to ollama
    },
    "gemini": {
        "llm":       _make_gemini_llm,
        "embed":     _make_gemini_embed,
        "transcribe": _make_gemini_transcriber,
        "ocr":       _make_gemini_ocr,
    },
    "whisper": {
        "transcribe": _make_whisper_transcriber,
    },
    "easyocr": {
        "ocr":       _make_easyocr,
    },
}
