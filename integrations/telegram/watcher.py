"""
Telegram userbot — watches ALL your chats automatically using Telethon.
User authenticates once with phone + OTP. Then runs forever in background.
Captures: text messages, voice notes, images, documents, videos from all chats.
"""

import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class TelegramWatcher:
    def __init__(self, cfg, enqueue_fn):
        self.cfg = cfg
        self._enqueue = enqueue_fn

    async def start(self):
        try:
            from telethon import TelegramClient, events
            from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto
        except ImportError:
            logger.error("Telethon not installed. Run: pip install telethon")
            return

        ig = self.cfg.integrations
        session_path = ig.telegram_session_path

        Path(session_path).parent.mkdir(parents=True, exist_ok=True)

        client = TelegramClient(
            session_path,
            int(ig.telegram_api_id),
            ig.telegram_api_hash,
        )

        @client.on(events.NewMessage)
        async def handler(event):
            message = event.message
            chat = await event.get_chat()
            sender = await event.get_sender()

            chat_name = getattr(chat, "title", None) or getattr(chat, "username", None) or str(chat.id)
            sender_name = (
                getattr(sender, "first_name", "") + " " + getattr(sender, "last_name", "")
            ).strip() or getattr(sender, "username", str(sender.id))

            metadata = {
                "platform": "telegram",
                "chat_id": str(chat.id),
                "message_id": str(message.id),
                "chat_name": chat_name,
            }

            # Text message
            if message.text and not message.media:
                self._enqueue("ingest_text", {
                    "text": message.text,
                    "source_app": "telegram",
                    "source_sender": sender_name,
                    "source_chat": chat_name,
                    "metadata": metadata,
                })
                return

            # Media message
            if message.media:
                tmp_path = await self._download_media(client, message)
                if tmp_path:
                    self._enqueue("ingest_file", {
                        "file_path": tmp_path,
                        "source_app": "telegram",
                        "source_sender": sender_name,
                        "source_chat": chat_name,
                        "metadata": {**metadata, "caption": message.text or ""},
                    })

        logger.info("Connecting to Telegram...")
        await client.start(phone=ig.telegram_phone)
        logger.info(f"Telegram userbot active — watching all chats")
        await client.run_until_disconnected()

    async def _download_media(self, client, message) -> str | None:
        """Download media to temp file. Returns path or None."""
        try:
            suffix = self._get_suffix(message)
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
                tmp_path = f.name
            await client.download_media(message, file=tmp_path)
            return tmp_path
        except Exception as e:
            logger.warning(f"Failed to download Telegram media: {e}")
            return None

    def _get_suffix(self, message) -> str:
        from telethon.tl.types import (
            MessageMediaDocument, MessageMediaPhoto,
            DocumentAttributeAudio, DocumentAttributeVideo
        )

        if isinstance(message.media, MessageMediaPhoto):
            return ".jpg"

        if isinstance(message.media, MessageMediaDocument):
            doc = message.media.document
            for attr in doc.attributes:
                if isinstance(attr, DocumentAttributeAudio):
                    return ".ogg" if getattr(attr, "voice", False) else ".mp3"
                if isinstance(attr, DocumentAttributeVideo):
                    return ".mp4"
            # Try mime type
            mime = getattr(doc, "mime_type", "")
            mime_map = {
                "application/pdf": ".pdf",
                "image/jpeg": ".jpg",
                "image/png": ".png",
                "audio/ogg": ".ogg",
                "audio/mpeg": ".mp3",
            }
            return mime_map.get(mime, ".bin")

        return ".bin"
