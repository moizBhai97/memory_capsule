"""
Provider interfaces — abstract base classes only.
Every AI provider implements these. Swap providers via config with zero code changes elsewhere.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMResult:
    """Structured output from LLM processing a capsule."""
    summary: str
    tags: list[str]
    action_items: list[str]
    language: str = "en"
    reminders: list[dict] = field(default_factory=list)


class LLMProvider(ABC):
    @abstractmethod
    async def extract_capsule_info(
        self,
        raw_content: str,
        source_app: str,
        source_sender: str | None = None,
        source_type: str = "unknown",
    ) -> LLMResult:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...


class EmbedProvider(ABC):
    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        ...

    @abstractmethod
    def dimension(self) -> int:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...


@dataclass
class TranscriptionResult:
    """Normalised transcription output across providers."""
    text: str
    language: str = "unknown"
    duration: float | None = None
    segments: list[dict] = field(default_factory=list)


class TranscriptionProvider(ABC):
    @abstractmethod
    async def transcribe(self, file_path: str) -> TranscriptionResult:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...


@dataclass
class OCRResult:
    """Normalised OCR output across providers."""
    text: str
    confidence: float | None = None          # 0.0–1.0, None if provider doesn't expose it
    blocks: list[dict] = field(default_factory=list)  # per-region detail when available


class OCRProvider(ABC):
    @abstractmethod
    async def extract_text(self, file_path: str, languages: list[str] | None = None) -> OCRResult:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...
