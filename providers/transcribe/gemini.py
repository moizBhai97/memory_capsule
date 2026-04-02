import base64
import json
import mimetypes
from pathlib import Path

import httpx

from ..base import TranscriptionProvider, TranscriptionResult


class GeminiTranscriber(TranscriptionProvider):
    def __init__(self, api_key: str, model: str, language: str | None = None):
        self.api_key = api_key
        self.model = model
        self.language = language
        self._client = httpx.AsyncClient(timeout=180.0)

    async def transcribe(self, file_path: str) -> TranscriptionResult:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        mime_type = mimetypes.guess_type(str(path))[0] or "audio/wav"
        audio_b64 = base64.b64encode(path.read_bytes()).decode("ascii")

        language_hint = self.language or "auto"
        instruction = (
            "Transcribe this audio accurately. Return valid JSON only with this shape: "
            '{"text":"full transcript","language":"bcp47 or unknown"}. '
            f"Language hint: {language_hint}."
        )

        response = await self._client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            params={"key": self.api_key},
            json={
                "contents": [
                    {
                        "parts": [
                            {"text": instruction},
                            {"inline_data": {"mime_type": mime_type, "data": audio_b64}},
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.0,
                    "responseMimeType": "application/json",
                },
            },
        )
        response.raise_for_status()
        data = response.json()

        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "{}")
        )

        try:
            parsed = json.loads(text)
            transcript = (parsed.get("text") or "").strip()
            language = (parsed.get("language") or "unknown").strip() or "unknown"
        except json.JSONDecodeError:
            transcript = text.strip()
            language = "unknown"

        return TranscriptionResult(text=transcript, language=language)

    async def health_check(self) -> bool:
        try:
            r = await self._client.get(
                "https://generativelanguage.googleapis.com/v1beta/models",
                params={"key": self.api_key},
                timeout=10.0,
            )
            return r.status_code == 200
        except Exception:
            return False
