"""
Slack integration — bot watches specified channels for messages and files.
Uses Slack Bolt framework (official Slack SDK).

Setup:
1. Create Slack app at api.slack.com/apps
2. Add Bot Token Scopes: channels:history, files:read, users:read
3. Install to workspace
4. Copy Bot Token to config
5. Add bot to channels you want to watch
"""

import asyncio
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

CAPTURE_FILE_TYPES = {"mp3", "ogg", "m4a", "wav", "mp4", "jpg", "jpeg", "png", "pdf", "txt"}


class SlackWatcher:
    def __init__(self, cfg, enqueue_fn):
        self.cfg = cfg
        self._enqueue = enqueue_fn

    async def start(self):
        try:
            from slack_bolt.async_app import AsyncApp
            from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
        except ImportError:
            logger.error("Slack SDK not installed. Run: pip install slack-bolt")
            return

        ig = self.cfg.integrations
        app = AsyncApp(token=ig.slack_bot_token)

        @app.event("message")
        async def handle_message(event, say, client):
            # Skip bot messages and edits
            if event.get("bot_id") or event.get("subtype") == "message_changed":
                return

            channel_id = event.get("channel")
            if ig.slack_channel_ids and channel_id not in ig.slack_channel_ids:
                return

            user_id = event.get("user", "")
            text = event.get("text", "")
            ts = event.get("ts", "")

            # Get user display name
            sender = await _get_user_name(client, user_id)

            # Get channel name
            try:
                ch_info = await client.conversations_info(channel=channel_id)
                channel_name = ch_info["channel"].get("name", channel_id)
            except Exception:
                channel_name = channel_id

            metadata = {
                "platform": "slack",
                "channel_id": channel_id,
                "channel_name": channel_name,
                "ts": ts,
            }

            # Text message
            if text:
                self._enqueue("ingest_text", {
                    "text": text,
                    "source_app": "slack",
                    "source_sender": sender,
                    "source_chat": f"#{channel_name}",
                    "metadata": metadata,
                })

            # File attachments
            for file_info in event.get("files", []):
                filetype = file_info.get("filetype", "").lower()
                if filetype not in CAPTURE_FILE_TYPES:
                    continue

                url = file_info.get("url_private_download")
                if not url:
                    continue

                asyncio.create_task(
                    self._download_and_enqueue(
                        url=url,
                        filename=file_info.get("name", f"slack_file.{filetype}"),
                        token=ig.slack_bot_token,
                        sender=sender,
                        channel_name=channel_name,
                        metadata={**metadata, "filename": file_info.get("name")},
                    )
                )

        handler = AsyncSocketModeHandler(app, ig.slack_bot_token)
        logger.info("Slack bot started")
        await handler.start_async()

    async def _download_and_enqueue(self, url, filename, token, sender, channel_name, metadata):
        import httpx

        suffix = Path(filename).suffix or ".bin"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=30.0,
                )
                resp.raise_for_status()

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
                f.write(resp.content)
                tmp_path = f.name

            self._enqueue("ingest_file", {
                "file_path": tmp_path,
                "source_app": "slack",
                "source_sender": sender,
                "source_chat": f"#{channel_name}",
                "metadata": metadata,
            })
        except Exception as e:
            logger.error(f"Failed to download Slack file: {e}")


async def _get_user_name(client, user_id: str) -> str:
    if not user_id:
        return "Unknown"
    try:
        info = await client.users_info(user=user_id)
        profile = info["user"].get("profile", {})
        return profile.get("display_name") or profile.get("real_name") or user_id
    except Exception:
        return user_id
