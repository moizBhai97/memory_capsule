"""
Provider interfaces — abstract base classes only.
Every AI provider implements these. Swap providers via config with zero code changes elsewhere.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResult:
    """Structured output from LLM processing a capsule."""
    summary: str
    tags: list[str]
    action_items: list[str]
    language: str = "en"
    reminders: list[dict] = None

    def __post_init__(self):
        if self.reminders is None:
            self.reminders = []


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
    segments: list[dict] | None = None

    def __post_init__(self):
        if self.segments is None:
            self.segments = []


class TranscriptionProvider(ABC):
    @abstractmethod
    async def transcribe(self, file_path: str) -> TranscriptionResult:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...
