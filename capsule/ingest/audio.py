"""
Audio ingestion — transcribes any audio/video file using Whisper.
Supports: ogg, mp3, mp4, wav, m4a, webm, flac (anything ffmpeg handles)

whisper-small chosen for best quality/speed/VRAM balance on 4GB GPU.
Auto-detects language — works for Arabic, English, French, Urdu, etc.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".ogg", ".mp3", ".mp4", ".wav", ".m4a", ".webm", ".flac", ".mpeg", ".mpga"}


def is_audio(file_path: str) -> bool:
    return Path(file_path).suffix.lower() in SUPPORTED_EXTENSIONS


async def transcribe(file_path: str, model_name: str = "small", device: str = "cuda", language: str = None) -> dict:
    """
    Transcribe audio file using Whisper.
    Returns: {"text": str, "language": str, "duration": float, "segments": list}
    """
    import whisper
    import torch

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    # Fall back to CPU if CUDA not available
    if device == "cuda" and not torch.cuda.is_available():
        logger.warning("CUDA not available, falling back to CPU for Whisper")
        device = "cpu"

    logger.info(f"Transcribing {path.name} with whisper-{model_name} on {device}")

    model = whisper.load_model(model_name, device=device)

    options = {"task": "transcribe"}
    if language:
        options["language"] = language

    result = model.transcribe(str(path), **options)

    # Free VRAM after transcription — we need it for the LLM next
    del model
    if device == "cuda":
        import torch
        torch.cuda.empty_cache()

    return {
        "text": result["text"].strip(),
        "language": result.get("language", "unknown"),
        "duration": result.get("duration", None),
        "segments": result.get("segments", []),
    }
