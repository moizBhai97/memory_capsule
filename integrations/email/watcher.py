"""
Email watcher — IMAP IDLE push connection.
Works with Gmail, Outlook, Yahoo, ProtonMail bridge, any IMAP provider.
User sets up once with email credentials. New emails captured automatically.

For Gmail: use App Password (not main password)
For Outlook: enable IMAP in settings
"""

import asyncio
import email
import logging
import os
import tempfile
from email.header import decode_header
from pathlib import Path

logger = logging.getLogger(__name__)

# File types we capture from email attachments
CAPTURE_ATTACHMENTS = {
    "application/pdf",
    "audio/ogg", "audio/mpeg", "audio/mp4", "audio/wav",
    "image/jpeg", "image/png", "image/gif",
    "video/mp4",
    "text/plain",
}


class EmailWatcher:
    def __init__(self, cfg, enqueue_fn):
        self.cfg = cfg
        self._enqueue = enqueue_fn
        self._running = False

    async def start(self):
        ig = self.cfg.integrations
        self._running = True
        logger.info("Email watcher starting: %s@%s", ig.email_username, ig.email_host)

        while self._running:
            try:
                await self._watch()
            except Exception as e:
                logger.error("Email watcher error: %s. Retrying in 30s...", e)
                await asyncio.sleep(30)

    async def _watch(self):
        """Open IMAP connection and poll for new messages."""
        import imaplib

        ig = self.cfg.integrations

        if ig.email_use_ssl:
            mail = imaplib.IMAP4_SSL(ig.email_host, ig.email_port)
        else:
            mail = imaplib.IMAP4(ig.email_host, ig.email_port)

        mail.login(ig.email_username, ig.email_password)
        mail.select(ig.email_folder)
        logger.info("Email connected: %s", ig.email_username)

        # Get all unseen emails on startup
        await self._fetch_unseen(mail)

        # Poll every 60 seconds for new emails
        # Production improvement: use IMAP IDLE for true push
        while self._running:
            await asyncio.sleep(60)
            try:
                mail.noop()  # keep connection alive
                await self._fetch_unseen(mail)
            except Exception as e:
                logger.warning("Email poll error: %s", e)
                break

        mail.logout()

    async def _fetch_unseen(self, mail):
        """Fetch and process all unseen emails."""
        import imaplib

        _, messages = mail.search(None, "UNSEEN")
        if not messages[0]:
            return

        ids = messages[0].split()
        logger.info("Found %s new email(s)", len(ids))

        for msg_id in ids:
            try:
                _, msg_data = mail.fetch(msg_id, "(RFC822)")
                raw = msg_data[0][1]
                await self._process_email(raw)
                # Mark as seen
                mail.store(msg_id, "+FLAGS", "\\Seen")
            except Exception as e:
                logger.error("Failed to process email %s: %s", msg_id, e)

    async def _process_email(self, raw: bytes):
        msg = email.message_from_bytes(raw)

        subject = _decode_header_value(msg.get("Subject", ""))
        from_addr = _decode_header_value(msg.get("From", ""))
        date_str = msg.get("Date", "")

        logger.info("Processing email: '%s' from %s", subject, from_addr)

        metadata = {
            "platform": "email",
            "subject": subject,
            "from": from_addr,
            "date": date_str,
        }

        # Extract body text
        body = _extract_body(msg)
        if body:
            self._enqueue("ingest_text", {
                "text": f"Subject: {subject}\nFrom: {from_addr}\n\n{body}",
                "source_app": "email",
                "source_sender": from_addr,
                "source_chat": subject,
                "metadata": metadata,
            })

        # Process attachments
        for part in msg.walk():
            content_type = part.get_content_type()
            filename = part.get_filename()

            if not filename:
                continue

            if content_type not in CAPTURE_ATTACHMENTS:
                continue

            payload = part.get_payload(decode=True)
            if not payload:
                continue

            suffix = Path(filename).suffix or _mime_to_ext(content_type)
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
                f.write(payload)
                tmp_path = f.name

            self._enqueue("ingest_file", {
                "file_path": tmp_path,
                "source_app": "email",
                "source_sender": from_addr,
                "source_chat": subject,
                "metadata": {**metadata, "filename": filename},
            })


def _decode_header_value(value: str) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    decoded = []
    for text, charset in parts:
        if isinstance(text, bytes):
            decoded.append(text.decode(charset or "utf-8", errors="ignore"))
        else:
            decoded.append(text)
    return " ".join(decoded).strip()


def _extract_body(msg) -> str:
    """Extract plain text body from email."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body += payload.decode(part.get_content_charset() or "utf-8", errors="ignore")
    else:
        if msg.get_content_type() == "text/plain":
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode(msg.get_content_charset() or "utf-8", errors="ignore")
    return body.strip()


def _mime_to_ext(mime: str) -> str:
    mapping = {
        "application/pdf": ".pdf",
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "audio/ogg": ".ogg",
        "audio/mpeg": ".mp3",
        "video/mp4": ".mp4",
    }
    return mapping.get(mime, ".bin")
