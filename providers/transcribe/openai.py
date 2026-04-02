from pathlib import Path

from ..base import TranscriptionProvider, TranscriptionResult


class OpenAITranscriber(TranscriptionProvider):
    def __init__(self, api_key: str, model: str, language: str | None = None, base_url: str | None = None):
        try:
            from openai import AsyncOpenAI

            kwargs = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            self._client = AsyncOpenAI(**kwargs)
        except ImportError:
            raise ImportError("Run: pip install openai")
        self.model = model
        self.language = language

    async def transcribe(self, file_path: str) -> TranscriptionResult:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        with path.open("rb") as f:
            kwargs = {"model": self.model, "file": f}
            if self.language:
                kwargs["language"] = self.language
            result = await self._client.audio.transcriptions.create(**kwargs)

        text = getattr(result, "text", "") or ""
        language = getattr(result, "language", "unknown") or "unknown"
        return TranscriptionResult(text=text.strip(), language=language)

    async def health_check(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False
