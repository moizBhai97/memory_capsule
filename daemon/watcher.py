"""
File system watcher. Watches configured folders and enqueues new files.
Uses watchdog library — cross-platform (Windows, Mac, Linux).

Automatically watches:
- Downloads folder
- Screenshots folder
- Any custom folders from config
- Zoom recordings folder (if enabled)
"""

import logging
import platform
from pathlib import Path

from watchdog.events import FileSystemEventHandler, FileCreatedEvent
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

# File extensions we care about
WATCHABLE_EXTENSIONS = {
    ".ogg", ".mp3", ".mp4", ".wav", ".m4a", ".webm", ".flac",  # audio
    ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp",          # images
    ".pdf",                                                       # documents
    ".txt", ".md",                                               # text
}


def get_default_folders() -> list[str]:
    """Auto-detect OS default folders for screenshots and downloads."""
    system = platform.system()
    home = Path.home()
    folders = []

    if system == "Windows":
        downloads = home / "Downloads"
        screenshots = home / "Pictures" / "Screenshots"
        onedrive_screenshots = home / "OneDrive" / "Pictures" / "Screenshots"
        for p in [downloads, screenshots, onedrive_screenshots]:
            if p.exists():
                folders.append(str(p))

    elif system == "Darwin":  # macOS
        downloads = home / "Downloads"
        desktop = home / "Desktop"
        screenshots = home / "Desktop"  # macOS default screenshot location
        for p in [downloads, desktop]:
            if p.exists():
                folders.append(str(p))

    else:  # Linux
        downloads = home / "Downloads"
        pictures = home / "Pictures"
        for p in [downloads, pictures]:
            if p.exists():
                folders.append(str(p))

    return list(set(folders))


class CapsuleEventHandler(FileSystemEventHandler):
    def __init__(self, enqueue_fn):
        self._enqueue = enqueue_fn

    def on_created(self, event: FileCreatedEvent):
        if event.is_directory:
            return

        path = Path(event.src_path)
        if path.suffix.lower() not in WATCHABLE_EXTENSIONS:
            return

        # Skip temp/hidden files
        if path.name.startswith(".") or path.name.startswith("~"):
            return

        logger.info("New file detected: %s", path.name)
        self._enqueue("ingest_file", {
            "file_path": str(path),
            "source_app": "watch_folder",
            "source_chat": str(path.parent),
        })


class FolderWatcher:
    def __init__(self, folders: list[str], enqueue_fn):
        self._enqueue = enqueue_fn
        self._observer = Observer()
        self._folders = folders

    def start(self):
        handler = CapsuleEventHandler(self._enqueue)
        started = []

        for folder in self._folders:
            path = Path(folder)
            if not path.exists():
                logger.warning("Watch folder does not exist, skipping: %s", folder)
                continue
            self._observer.schedule(handler, str(path), recursive=False)
            started.append(folder)
            logger.info("Watching folder: %s", folder)

        if started:
            self._observer.start()
            logger.info("File watcher started — watching %s folder(s)", len(started))
        else:
            logger.warning("No valid folders to watch")

    def stop(self):
        self._observer.stop()
        self._observer.join()
        logger.info("File watcher stopped")
