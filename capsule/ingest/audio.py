from pathlib import Path

SUPPORTED_EXTENSIONS = {".ogg", ".mp3", ".mp4", ".wav", ".m4a", ".webm", ".flac", ".mpeg", ".mpga"}


def is_audio(file_path: str) -> bool:
    return Path(file_path).suffix.lower() in SUPPORTED_EXTENSIONS
