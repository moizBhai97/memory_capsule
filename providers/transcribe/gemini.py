"""
Gemini transcription provider.

Uses Gemini's multimodal API to transcribe audio. responseSchema enforces
structured output so no fragile JSON parsing fallback is needed.
"""

import base64
import json
import mimetypes
from pathlib import Path

import httpx

from ..base import TranscriptionProvider, TranscriptionResult

_TRANSCRIPTION_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "text":     {"type": "string", "description": "Full verbatim transcript"},
        "language": {"type": "string", "description": "BCP-47 language code or 'unknown'"},
    },
    "required": ["text", "language"],
    "additionalProperties": False,
}


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

        response = await self._client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            params={"key": self.api_key},
            json={
                "contents": [{
                    "parts": [
                        {"text": f"Transcribe this audio accurately. Language hint: {language_hint}."},
                        {"inline_data": {"mime_type": mime_type, "data": audio_b64}},
                    ],
                }],
                "generationConfig": {
                    "temperature": 0.0,
                    "responseMimeType": "application/json",
                    "responseSchema": _TRANSCRIPTION_SCHEMA,
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
        parsed = json.loads(text)
        return TranscriptionResult(
            text=(parsed.get("text") or "").strip(),
            language=(parsed.get("language") or "unknown").strip() or "unknown",
        )

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
