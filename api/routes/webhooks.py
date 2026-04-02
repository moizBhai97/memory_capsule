"""
Webhook receivers — for Zapier, n8n, Make.com, WhatsApp Business, and custom integrations.
Any platform that can send an HTTP POST can push content here.
"""

import hashlib
import hmac
import logging

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse

from api.state import get_pipeline
from api.normalizer import normalize
from capsule.models import SourceApp
from config import get_config

router = APIRouter()
logger = logging.getLogger(__name__)


# --- Generic webhook (Zapier, n8n, Make, custom) ---

@router.post("/ingest")
async def generic_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Universal webhook endpoint.
    Any platform can POST here with text content.

    Body:
    {
        "text": "content to capture",
        "source_app": "zapier",       # optional
        "source_sender": "Ahmed",      # optional
        "source_chat": "Project Chat", # optional
        "url": "https://...",          # optional
        "metadata": {}                 # optional platform-specific data
    }
    """
    cfg = get_config()
    body = await request.json()

    # Verify webhook signature if secret is configured
    if cfg.integrations.webhook_secret:
        signature = request.headers.get("X-Signature", "")
        if not _verify_signature(await request.body(), cfg.integrations.webhook_secret, signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    pipeline = get_pipeline()
    platform_hint = request.headers.get("X-Platform", "")
    normalized = normalize(body, platform_hint)

    if not normalized:
        raise HTTPException(status_code=400, detail="Either 'text' or 'url' required")

    try:
        app_enum = SourceApp(normalized["source_app"])
    except ValueError:
        app_enum = SourceApp.UNKNOWN

    async def _process():
        await pipeline.process_text(
            text=normalized["text"],
            source_app=app_enum,
            source_sender=normalized["source_sender"],
            source_chat=normalized["source_chat"],
            source_url=normalized["source_url"],
            metadata=normalized["metadata"],
        )

    background_tasks.add_task(_process)
    return {"status": "received"}


# --- WhatsApp Business API webhook ---

@router.get("/whatsapp-business")
async def whatsapp_business_verify(
    hub_mode: str = None,
    hub_challenge: str = None,
    hub_verify_token: str = None,
):
    """Meta webhook verification challenge."""
    cfg = get_config()
    verify_token = cfg.integrations.whatsapp_business_verify_token

    if hub_mode == "subscribe" and hub_challenge and hub_verify_token == verify_token:
        logger.info("WhatsApp Business webhook verified")
        return PlainTextResponse(hub_challenge)

    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/whatsapp-business")
async def whatsapp_business_message(request: Request, background_tasks: BackgroundTasks):
    """Receive WhatsApp Business messages and media."""
    cfg = get_config()
    body = await request.json()

    # Verify Meta signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    raw_body = await request.body()
    if not _verify_meta_signature(raw_body, cfg.integrations.whatsapp_business_token, signature):
        raise HTTPException(status_code=401, detail="Invalid Meta signature")

    pipeline = get_pipeline()

    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})

            for message in value.get("messages", []):
                msg_type = message.get("type")
                sender = message.get("from", "")
                contact_name = _get_contact_name(value, sender)
                msg_id = message.get("id", "")
                timestamp_unix = int(message.get("timestamp", 0))

                from datetime import datetime
                timestamp = datetime.utcfromtimestamp(timestamp_unix) if timestamp_unix else None

                metadata = {
                    "platform": "whatsapp_business",
                    "message_id": msg_id,
                    "from_number": sender,
                }

                if msg_type == "text":
                    text = message.get("text", {}).get("body", "")
                    if text:
                        async def _process_text(t=text, s=contact_name, ts=timestamp, m=metadata):
                            await pipeline.process_text(
                                text=t,
                                source_app=SourceApp.WHATSAPP_BUSINESS,
                                source_sender=s,
                                timestamp=ts,
                                metadata=m,
                            )
                        background_tasks.add_task(_process_text)

                elif msg_type in ("audio", "image", "document", "video"):
                    media_id = message.get(msg_type, {}).get("id")
                    if media_id:
                        async def _process_media(mid=media_id, s=contact_name, mt=msg_type, ts=timestamp, m=metadata):
                            await _download_and_process_wa_media(pipeline, cfg, mid, s, mt, ts, m)
                        background_tasks.add_task(_process_media)

    return {"status": "ok"}


async def _download_and_process_wa_media(pipeline, cfg, media_id, sender, media_type, timestamp, metadata):
    """Download media from WhatsApp Business API and process it."""
    import httpx
    import tempfile
    import os

    headers = {"Authorization": f"Bearer {cfg.integrations.whatsapp_business_token}"}

    async with httpx.AsyncClient() as client:
        # Get media URL
        url_resp = await client.get(
            f"https://graph.facebook.com/v18.0/{media_id}",
            headers=headers,
        )
        url_resp.raise_for_status()
        media_url = url_resp.json().get("url")
        mime_type = url_resp.json().get("mime_type", "")

        # Download media
        media_resp = await client.get(media_url, headers=headers)
        media_resp.raise_for_status()

    ext = _mime_to_ext(mime_type) or f".{media_type}"
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as f:
        f.write(media_resp.content)
        tmp_path = f.name

    try:
        await pipeline.process_file(
            file_path=tmp_path,
            source_app=SourceApp.WHATSAPP_BUSINESS,
            source_sender=sender,
            timestamp=timestamp,
            metadata=metadata,
        )
    finally:
        os.unlink(tmp_path)


def _get_contact_name(value: dict, phone: str) -> str:
    for contact in value.get("contacts", []):
        if contact.get("wa_id") == phone:
            return contact.get("profile", {}).get("name", phone)
    return phone


def _verify_signature(body: bytes, secret: str, signature: str) -> bool:
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


def _verify_meta_signature(body: bytes, token: str, signature: str) -> bool:
    if not signature.startswith("sha256="):
        return False
    expected = hmac.new(token.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature[7:])


def _mime_to_ext(mime: str) -> str | None:
    mapping = {
        "audio/ogg": ".ogg",
        "audio/mpeg": ".mp3",
        "audio/mp4": ".m4a",
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "application/pdf": ".pdf",
        "video/mp4": ".mp4",
    }
    return mapping.get(mime)
