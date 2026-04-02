"""
Local Whisper transcription provider.
Handles device selection (auto/cpu/cuda) and VRAM cleanup internally.
"""

import logging
from pathlib import Path

from ..base import TranscriptionProvider, TranscriptionResult

logger = logging.getLogger(__name__)


class WhisperTranscriber(TranscriptionProvider):
    def __init__(
        self,
        model_name: str = "small",
        device: str = "auto",
        language: str | None = None,
        cache_dir: str | None = None,
    ):
        self.model_name = model_name
        self.device = device
        self.language = language
        self.cache_dir = cache_dir

    async def transcribe(self, file_path: str) -> TranscriptionResult:
        try:
            import whisper
            import torch
        except ImportError:
            raise ImportError("Run: pip install openai-whisper torch")

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        device = self.device
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        elif device == "cuda" and not torch.cuda.is_available():
            logger.warning("CUDA not available, falling back to CPU for Whisper")
            device = "cpu"

        logger.info("Transcribing %s with whisper-%s on %s", path.name, self.model_name, device)

        try:
            load_kwargs = {"device": device, "in_memory": False}
            if self.cache_dir:
                Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
                load_kwargs["download_root"] = self.cache_dir
            model = whisper.load_model(self.model_name, **load_kwargs)
        except Exception as e:
            if device == "cuda" and ("out of memory" in str(e).lower() or "cuda" in str(e).lower()):
                logger.warning("Whisper CUDA load failed (%s), retrying on CPU", e)
                device = "cpu"
                load_kwargs["device"] = "cpu"
                model = whisper.load_model(self.model_name, **load_kwargs)
            else:
                raise

        options = {"task": "transcribe"}
        if self.language:
            options["language"] = self.language
        if device == "cpu":
            options["fp16"] = False

        try:
            result = model.transcribe(str(path), **options)
        except Exception as e:
            if device == "cuda" and ("out of memory" in str(e).lower() or "cuda" in str(e).lower()):
                logger.warning("Whisper CUDA transcribe failed (%s), retrying on CPU", e)
                model = model.to("cpu")
                torch.cuda.empty_cache()
                options["fp16"] = False
                result = model.transcribe(str(path), **options)
            else:
                raise

        del model
        if device == "cuda":
            torch.cuda.empty_cache()

        return TranscriptionResult(
            text=result["text"].strip(),
            language=result.get("language", "unknown"),
            duration=result.get("duration"),
            segments=result.get("segments", []),
        )

    async def health_check(self) -> bool:
        return True
