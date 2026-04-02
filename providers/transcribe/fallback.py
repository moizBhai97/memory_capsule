"""
Fallback transcriber — wraps the configured provider and walks a fallback
chain on failure, same pattern OpenClaw uses for STT auto-detection.
Local Whisper is always last: no API key, no network, always available.
"""

import logging
import os

from config import ProviderConfig, API_KEY_ENV
from ..base import TranscriptionProvider, TranscriptionResult

logger = logging.getLogger(__name__)

# Tried in order when the primary provider fails.
FALLBACK_CHAIN = ["openai", "groq", "gemini", "whisper"]

_FALLBACK_MODELS = {
    "openai": "whisper-1",
    "groq": "whisper-large-v3-turbo",
    "gemini": "gemini-2.0-flash",
    "whisper": "small",
}


class FallbackTranscriber(TranscriptionProvider):
    """
    Wraps a primary TranscriptionProvider. On failure, attempts each provider
    in FALLBACK_CHAIN in order until one succeeds.
    """

    def __init__(
        self,
        primary: TranscriptionProvider,
        primary_provider_id: str,
        language: str | None = None,
        device: str = "auto",
    ):
        self._primary = primary
        self._primary_provider_id = primary_provider_id
        self._language = language
        self._device = device

    async def transcribe(self, file_path: str) -> TranscriptionResult:
        try:
            return await self._primary.transcribe(file_path)
        except Exception as e:
            logger.warning(
                "Transcription failed with '%s': %s — trying fallback chain",
                self._primary_provider_id, e,
            )
            return await self._try_fallback(file_path)

    async def _try_fallback(self, file_path: str) -> TranscriptionResult:
        # Lazy import to avoid circular dependency:
        # registry.py imports from base.py; fallback.py importing registry at
        # module load would create a cycle via transcribe/__init__.py
        from ..registry import PROVIDER_REGISTRY

        for provider_id in FALLBACK_CHAIN:
            if provider_id == self._primary_provider_id:
                continue

            entry = PROVIDER_REGISTRY.get(provider_id, {})
            if "transcribe" not in entry:
                continue

            env_var = API_KEY_ENV.get(provider_id)
            api_key = os.getenv(env_var, "") if env_var else ""

            if provider_id != "whisper" and not api_key:
                continue  # skip cloud providers with no key

            fallback_cfg = ProviderConfig(
                model=f"{provider_id}/{_FALLBACK_MODELS[provider_id]}",
                api_key=api_key,
                extra={"language": self._language},
                device=self._device,
            )

            try:
                result = await entry["transcribe"](fallback_cfg).transcribe(file_path)
                logger.info("Fallback transcription succeeded via '%s'", provider_id)
                return result
            except Exception as fe:
                logger.warning("Fallback '%s' also failed: %s", provider_id, fe)

        raise RuntimeError("All transcription providers failed. Check your config and API keys.")

    async def health_check(self) -> bool:
        return await self._primary.health_check()
