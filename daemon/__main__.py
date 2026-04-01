"""
Memory Capsule Daemon — run with: python -m daemon

This is the background service that runs silently.
It starts all watchers and processes the job queue.
User never needs to interact with this directly after setup.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

from config import get_config
from capsule.pipeline import Pipeline
from capsule.store.sqlite import SQLiteStore
from capsule.store.vector import VectorStore
from capsule.models import SourceApp
from daemon.job_queue import JobQueue
from daemon.watcher import FolderWatcher, get_default_folders

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("daemon")


class MemoryCapsuleDaemon:
    def __init__(self):
        self.cfg = get_config()
        self._running = False

        # Core components
        self.sqlite = SQLiteStore(self.cfg.storage.sqlite_path)
        self.vector = VectorStore(self.cfg.storage.chroma_path)
        self.pipeline = Pipeline(self.sqlite, self.vector)
        self.queue = JobQueue(self.cfg.storage.sqlite_path.replace(".db", "_jobs.db"))

        # Watchers
        self._folder_watcher = None
        self._integration_tasks = []

    async def start(self):
        self._running = True
        logger.info("=" * 50)
        logger.info("  Memory Capsule Daemon starting...")
        logger.info("=" * 50)

        # Start folder watchers
        await self._start_folder_watchers()

        # Start integration watchers (Telegram, Email, etc.)
        await self._start_integrations()

        # Start job processor
        logger.info("Daemon ready. Processing jobs...")
        await self._process_loop()

    async def _start_folder_watchers(self):
        ig = self.cfg.integrations
        folders = list(ig.watch_folders)

        if ig.watch_downloads or ig.watch_screenshots:
            default_folders = get_default_folders()
            folders.extend(default_folders)

        if ig.zoom_enabled and ig.zoom_recordings_path:
            folders.append(ig.zoom_recordings_path)

        if folders:
            self._folder_watcher = FolderWatcher(
                folders=list(set(folders)),
                enqueue_fn=self.queue.enqueue,
            )
            self._folder_watcher.start()

    async def _start_integrations(self):
        ig = self.cfg.integrations

        if ig.telegram_enabled:
            try:
                from integrations.telegram.watcher import TelegramWatcher
                task = asyncio.create_task(
                    TelegramWatcher(self.cfg, self.queue.enqueue).start()
                )
                self._integration_tasks.append(task)
                logger.info("Telegram watcher started")
            except Exception as e:
                logger.error(f"Telegram watcher failed to start: {e}")

        if ig.email_enabled:
            try:
                from integrations.email.watcher import EmailWatcher
                task = asyncio.create_task(
                    EmailWatcher(self.cfg, self.queue.enqueue).start()
                )
                self._integration_tasks.append(task)
                logger.info("Email watcher started")
            except Exception as e:
                logger.error(f"Email watcher failed to start: {e}")

        if ig.slack_enabled:
            try:
                from integrations.slack.watcher import SlackWatcher
                task = asyncio.create_task(
                    SlackWatcher(self.cfg, self.queue.enqueue).start()
                )
                self._integration_tasks.append(task)
                logger.info("Slack watcher started")
            except Exception as e:
                logger.error(f"Slack watcher failed to start: {e}")

        if ig.discord_enabled:
            try:
                from integrations.discord.watcher import DiscordWatcher
                task = asyncio.create_task(
                    DiscordWatcher(self.cfg, self.queue.enqueue).start()
                )
                self._integration_tasks.append(task)
                logger.info("Discord watcher started")
            except Exception as e:
                logger.error(f"Discord watcher failed to start: {e}")

        if ig.whatsapp_enabled:
            logger.info("WhatsApp watcher: start the Node.js bridge separately")
            logger.info("  cd integrations/whatsapp && node bridge.js")

    async def _process_loop(self):
        """Main loop — dequeues and processes jobs one at a time."""
        while self._running:
            job = self.queue.dequeue()

            if not job:
                # No jobs — wait before checking again
                await asyncio.sleep(1)
                continue

            try:
                await self._process_job(job)
                self.queue.complete(job["id"])
            except Exception as e:
                logger.error(f"Job {job['id']} failed: {e}")
                self.queue.fail(job["id"], str(e))

    async def _process_job(self, job: dict):
        job_type = job["job_type"]
        payload = job["payload"]

        if job_type == "ingest_file":
            source_app_str = payload.get("source_app", "unknown")
            try:
                source_app = SourceApp(source_app_str)
            except ValueError:
                source_app = SourceApp.UNKNOWN

            await self.pipeline.process_file(
                file_path=payload["file_path"],
                source_app=source_app,
                source_sender=payload.get("source_sender"),
                source_chat=payload.get("source_chat"),
                metadata=payload.get("metadata", {}),
            )

        elif job_type == "ingest_text":
            source_app_str = payload.get("source_app", "unknown")
            try:
                source_app = SourceApp(source_app_str)
            except ValueError:
                source_app = SourceApp.UNKNOWN

            await self.pipeline.process_text(
                text=payload.get("text", ""),
                source_app=source_app,
                source_sender=payload.get("source_sender"),
                source_chat=payload.get("source_chat"),
                source_url=payload.get("source_url"),
                metadata=payload.get("metadata", {}),
            )

        else:
            logger.warning(f"Unknown job type: {job_type}")

    async def stop(self):
        logger.info("Daemon stopping...")
        self._running = False

        if self._folder_watcher:
            self._folder_watcher.stop()

        for task in self._integration_tasks:
            task.cancel()

        logger.info("Daemon stopped")


async def main():
    daemon = MemoryCapsuleDaemon()

    # Graceful shutdown on Ctrl+C or SIGTERM
    loop = asyncio.get_event_loop()

    def _shutdown():
        logger.info("Shutdown signal received")
        asyncio.create_task(daemon.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown)
        except NotImplementedError:
            pass  # Windows doesn't support add_signal_handler for all signals

    await daemon.start()


if __name__ == "__main__":
    asyncio.run(main())
