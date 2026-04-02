"""
Discord integration — bot watches specified channels for messages and files.

Setup:
1. Create bot at discord.com/developers/applications
2. Enable: Message Content Intent, Server Members Intent
3. Invite bot to your server with permissions: Read Messages, Read Message History
4. Copy Bot Token to config
5. Add channel IDs you want to watch
"""

import asyncio
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

CAPTURE_EXTENSIONS = {".mp3", ".ogg", ".m4a", ".wav", ".mp4", ".jpg", ".jpeg", ".png", ".pdf", ".txt"}


class DiscordWatcher:
    def __init__(self, cfg, enqueue_fn):
        self.cfg = cfg
        self._enqueue = enqueue_fn

    async def start(self):
        try:
            import discord
        except ImportError:
            logger.error("Discord.py not installed. Run: pip install discord.py")
            return

        ig = self.cfg.integrations
        intents = discord.Intents.default()
        intents.message_content = True

        client = discord.Client(intents=intents)

        @client.event
        async def on_ready():
            logger.info("Discord bot connected as %s", client.user)

        @client.event
        async def on_message(message):
            # Skip bot messages
            if message.author.bot:
                return

            # Filter by channel if configured
            if ig.discord_channel_ids and str(message.channel.id) not in ig.discord_channel_ids:
                return

            sender = message.author.display_name
            channel_name = getattr(message.channel, "name", str(message.channel.id))

            metadata = {
                "platform": "discord",
                "channel_id": str(message.channel.id),
                "channel_name": channel_name,
                "guild": message.guild.name if message.guild else "DM",
                "message_id": str(message.id),
            }

            # Text content
            if message.content:
                self._enqueue("ingest_text", {
                    "text": message.content,
                    "source_app": "discord",
                    "source_sender": sender,
                    "source_chat": f"#{channel_name}",
                    "metadata": metadata,
                })

            # Attachments
            for attachment in message.attachments:
                ext = Path(attachment.filename).suffix.lower()
                if ext not in CAPTURE_EXTENSIONS:
                    continue

                asyncio.create_task(
                    self._download_and_enqueue(
                        url=attachment.url,
                        filename=attachment.filename,
                        sender=sender,
                        channel_name=channel_name,
                        metadata={**metadata, "filename": attachment.filename},
                    )
                )

        await client.start(ig.discord_bot_token)

    async def _download_and_enqueue(self, url, filename, sender, channel_name, metadata):
        import httpx

        suffix = Path(filename).suffix or ".bin"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=30.0)
                resp.raise_for_status()

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
                f.write(resp.content)
                tmp_path = f.name

            self._enqueue("ingest_file", {
                "file_path": tmp_path,
                "source_app": "discord",
                "source_sender": sender,
                "source_chat": f"#{channel_name}",
                "metadata": metadata,
            })
        except Exception as e:
            logger.error("Failed to download Discord attachment: %s", e)
