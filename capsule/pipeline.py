"""
The core pipeline. Every capsule goes through this regardless of source.

Ingest → Extract text → LLM process → Embed → Store
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path

from capsule.models import Capsule, CapsuleSource, CapsuleStatus, SourceApp, Reminder
from capsule.ingest import ingest_file, ingest_url, ingest_text
from capsule.store.sqlite import SQLiteStore
from capsule.store.vector import VectorStore
from config import get_config
from providers import get_llm, get_embed

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, sqlite: SQLiteStore, vector: VectorStore):
        self.sqlite = sqlite
        self.vector = vector
        self.cfg = get_config()

    async def process_file(
        self,
        file_path: str,
        source_app: SourceApp = SourceApp.UNKNOWN,
        source_sender: str | None = None,
        source_chat: str | None = None,
        timestamp: datetime | None = None,
        metadata: dict | None = None,
    ) -> Capsule:
        """
        Full pipeline for a file.
        Saves file to uploads directory, extracts, processes, stores.
        Returns the completed Capsule.
        """
        # Save original file to uploads
        saved_path = self._save_file(file_path)

        capsule = Capsule(
            source_app=source_app,
            source_file=saved_path,
            source_sender=source_sender,
            source_chat=source_chat,
            timestamp=timestamp or datetime.utcnow(),
            metadata=metadata or {},
            status=CapsuleStatus.PROCESSING,
        )

        # Save immediately so it shows as "processing" in the UI
        self.sqlite.save(capsule)

        try:
            await self._run(capsule, file_path=file_path)
        except Exception as e:
            logger.error("Pipeline failed for %s: %s", file_path, e)
            capsule.status = CapsuleStatus.FAILED
            capsule.error = str(e)
            self.sqlite.save(capsule)
            raise

        return capsule

    async def process_text(
        self,
        text: str,
        source_app: SourceApp = SourceApp.UNKNOWN,
        source_sender: str | None = None,
        source_chat: str | None = None,
        source_url: str | None = None,
        timestamp: datetime | None = None,
        metadata: dict | None = None,
    ) -> Capsule:
        """Full pipeline for raw text or URL."""
        capsule = Capsule(
            source_app=source_app,
            source_url=source_url,
            source_sender=source_sender,
            source_chat=source_chat,
            timestamp=timestamp or datetime.utcnow(),
            metadata=metadata or {},
            status=CapsuleStatus.PROCESSING,
        )
        self.sqlite.save(capsule)

        try:
            if source_url and not text:
                await self._run(capsule, url=source_url)
            else:
                await self._run(capsule, raw_text=text)
        except Exception as e:
            logger.error("Pipeline failed for text: %s", e)
            capsule.status = CapsuleStatus.FAILED
            capsule.error = str(e)
            self.sqlite.save(capsule)
            raise

        return capsule

    async def _run(
        self,
        capsule: Capsule,
        file_path: str = None,
        url: str = None,
        raw_text: str = None,
    ) -> None:
        """Internal pipeline execution."""

        # --- Step 1: Extract raw content ---
        if file_path:
            source_type, extracted = await ingest_file(file_path)
            capsule.source_type = source_type
            capsule.raw_content = extracted.get("text", "")
            capsule.language = extracted.get("language")
            capsule.duration_seconds = extracted.get("duration")

        elif url:
            source_type, extracted = await ingest_url(url)
            capsule.source_type = source_type
            capsule.source_url = url
            capsule.raw_content = extracted.get("text", "")

        elif raw_text:
            source_type, extracted = await ingest_text(raw_text)
            capsule.source_type = source_type
            capsule.raw_content = extracted.get("text", "")

        if not capsule.raw_content:
            logger.warning("No content extracted for capsule %s", capsule.id)
            capsule.status = CapsuleStatus.READY
            self.sqlite.save(capsule)
            return

        # --- Step 2: LLM extraction (summary, tags, action items) ---
        llm = get_llm()
        result = await llm.extract_capsule_info(
            raw_content=capsule.raw_content,
            source_app=capsule.source_app.value,
            source_sender=capsule.source_sender,
            source_type=capsule.source_type.value,
        )

        capsule.summary = result.summary
        capsule.tags = result.tags
        capsule.action_items = result.action_items
        capsule.language = capsule.language or result.language
        capsule.reminders = [
            Reminder(date=r.get("date", ""), note=r.get("note", ""))
            for r in result.reminders
        ]

        # --- Step 3: Embed for semantic search ---
        embed = get_embed()
        # Embed summary + tags — more signal-dense than raw content
        embed_text = f"{capsule.summary}\n{' '.join(capsule.tags)}\n{capsule.raw_content[:500]}"
        embedding = await embed.embed(embed_text)

        # --- Step 4: Store ---
        capsule.status = CapsuleStatus.READY
        self.sqlite.save(capsule)
        self.vector.upsert(
            capsule_id=capsule.id,
            embedding=embedding,
            metadata={
                "source_app": capsule.source_app.value,
                "source_type": capsule.source_type.value,
                "source_sender": capsule.source_sender or "",
                "tags": capsule.tags,
                "timestamp": capsule.timestamp.isoformat(),
            },
        )

        logger.info("Capsule ready: %s | %s | tags: %s", capsule.id, capsule.source_app.value, capsule.tags)

    def _save_file(self, original_path: str) -> str:
        """Copy original file to uploads directory. Preserves original."""
        uploads_dir = Path(self.cfg.storage.uploads_path)
        uploads_dir.mkdir(parents=True, exist_ok=True)

        src = Path(original_path)
        dest = uploads_dir / src.name

        # Avoid overwriting if same name exists
        if dest.exists():
            stem = src.stem
            suffix = src.suffix
            dest = uploads_dir / f"{stem}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}{suffix}"

        shutil.copy2(str(src), str(dest))
        return str(dest)
