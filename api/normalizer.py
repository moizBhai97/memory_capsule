"""
Inbound webhook normalizer.
Different platforms (Zapier, n8n, Make, custom) send differently-shaped payloads.
This normalizes them all into a standard dict the pipeline understands.

Why here and not in api/routes/webhooks.py?
- api/routes/webhooks.py handles HTTP routing + auth
- This module handles payload understanding — separate concern
- Makes it easy to add new platform formats without touching the API layer
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def normalize(payload: dict, platform_hint: str = "") -> dict | None:
    """
    Normalize an inbound webhook payload to standard format.

    Returns dict with keys:
      text, source_app, source_sender, source_chat, source_url, metadata
    Returns None if payload has no usable content.
    """
    # Try platform-specific normalizers first
    if platform_hint == "zapier" or _looks_like_zapier(payload):
        return _normalize_zapier(payload)

    if platform_hint == "n8n" or _looks_like_n8n(payload):
        return _normalize_n8n(payload)

    if platform_hint == "make" or _looks_like_make(payload):
        return _normalize_make(payload)

    if platform_hint == "typeform" or "form_response" in payload:
        return _normalize_typeform(payload)

    if platform_hint == "github" or "repository" in payload:
        return _normalize_github(payload)

    if platform_hint == "linear" or "data" in payload and "type" in payload:
        return _normalize_linear(payload)

    # Generic fallback — works for any well-formed payload
    return _normalize_generic(payload)


def _normalize_generic(payload: dict) -> dict | None:
    text = (
        payload.get("text")
        or payload.get("body")
        or payload.get("content")
        or payload.get("message")
        or payload.get("description")
        or ""
    )
    url = payload.get("url") or payload.get("link")

    if not text and not url:
        return None

    return {
        "text": text,
        "source_url": url,
        "source_app": payload.get("source_app") or payload.get("source") or "webhook",
        "source_sender": payload.get("source_sender") or payload.get("sender") or payload.get("from") or payload.get("author"),
        "source_chat": payload.get("source_chat") or payload.get("subject") or payload.get("channel"),
        "metadata": payload.get("metadata") or {},
    }


def _normalize_zapier(payload: dict) -> dict | None:
    # Zapier typically sends flat key-value pairs from trigger data
    text = payload.get("text") or payload.get("body_plain") or payload.get("body") or ""
    subject = payload.get("subject") or payload.get("name") or ""
    sender = payload.get("from") or payload.get("from_email") or payload.get("sender_name") or ""

    if subject and text:
        full_text = f"{subject}\n\n{text}" if subject not in text else text
    else:
        full_text = text or subject

    if not full_text and not payload.get("url"):
        return None

    return {
        "text": full_text,
        "source_url": payload.get("url"),
        "source_app": "zapier",
        "source_sender": sender,
        "source_chat": subject,
        "metadata": {"platform": "zapier", "raw": payload},
    }


def _normalize_n8n(payload: dict) -> dict | None:
    # n8n passes data as-is from whatever node triggered it
    # Usually wrapped in a list or has a "data" key
    data = payload
    if isinstance(payload.get("body"), dict):
        data = payload["body"]
    elif isinstance(payload.get("data"), dict):
        data = payload["data"]

    text = data.get("text") or data.get("content") or data.get("message") or data.get("body") or ""
    if not text and not data.get("url"):
        return None

    return {
        "text": text,
        "source_url": data.get("url"),
        "source_app": "n8n",
        "source_sender": data.get("from") or data.get("sender") or data.get("author"),
        "source_chat": data.get("subject") or data.get("channel") or data.get("workflow"),
        "metadata": {"platform": "n8n", "workflow": payload.get("workflow_name", "")},
    }


def _normalize_make(payload: dict) -> dict | None:
    # Make.com (formerly Integromat) sends webhook data directly
    text = payload.get("text") or payload.get("message") or payload.get("content") or ""
    if not text and not payload.get("url"):
        return None

    return {
        "text": text,
        "source_url": payload.get("url"),
        "source_app": "make",
        "source_sender": payload.get("from") or payload.get("sender"),
        "source_chat": payload.get("subject") or payload.get("scenario"),
        "metadata": {"platform": "make"},
    }


def _normalize_typeform(payload: dict) -> dict | None:
    """Typeform form submissions."""
    form_response = payload.get("form_response", payload)
    answers = form_response.get("answers", [])

    # Build readable text from answers
    lines = []
    for answer in answers:
        field = answer.get("field", {}).get("title", "Field")
        value = (
            answer.get("text")
            or answer.get("choice", {}).get("label")
            or answer.get("email")
            or answer.get("number")
            or str(answer.get("boolean", ""))
        )
        if value:
            lines.append(f"{field}: {value}")

    text = "\n".join(lines)
    if not text:
        return None

    form_name = form_response.get("definition", {}).get("title", "Form")
    email = next((a.get("email") for a in answers if a.get("type") == "email"), None)

    return {
        "text": text,
        "source_url": None,
        "source_app": "typeform",
        "source_sender": email,
        "source_chat": form_name,
        "metadata": {"platform": "typeform", "form_name": form_name},
    }


def _normalize_github(payload: dict) -> dict | None:
    """GitHub webhooks — issues, PRs, comments."""
    action = payload.get("action", "")
    repo = payload.get("repository", {}).get("full_name", "")
    sender = payload.get("sender", {}).get("login", "")

    if "issue" in payload:
        item = payload["issue"]
        text = f"[GitHub Issue {action}] {item.get('title', '')}\n{item.get('body', '')}"
        chat = f"{repo} issues"
        url = item.get("html_url")
    elif "pull_request" in payload:
        item = payload["pull_request"]
        text = f"[GitHub PR {action}] {item.get('title', '')}\n{item.get('body', '')}"
        chat = f"{repo} PRs"
        url = item.get("html_url")
    elif "comment" in payload:
        item = payload["comment"]
        text = f"[GitHub Comment] {item.get('body', '')}"
        chat = repo
        url = item.get("html_url")
    else:
        return None

    if not text.strip():
        return None

    return {
        "text": text,
        "source_url": url,
        "source_app": "github",
        "source_sender": sender,
        "source_chat": chat,
        "metadata": {"platform": "github", "repo": repo, "action": action},
    }


def _normalize_linear(payload: dict) -> dict | None:
    """Linear issue tracker webhooks."""
    action = payload.get("action", "")
    data = payload.get("data", {})
    item_type = payload.get("type", "Issue")

    title = data.get("title", "")
    description = data.get("description", "")
    text = f"[Linear {item_type} {action}] {title}\n{description}".strip()

    if not text:
        return None

    return {
        "text": text,
        "source_url": data.get("url"),
        "source_app": "linear",
        "source_sender": data.get("creator", {}).get("name") if isinstance(data.get("creator"), dict) else None,
        "source_chat": data.get("team", {}).get("name") if isinstance(data.get("team"), dict) else "Linear",
        "metadata": {"platform": "linear", "action": action, "type": item_type},
    }


def _looks_like_zapier(payload: dict) -> bool:
    return any(k in payload for k in ("zap_id", "zap_name", "body_plain"))


def _looks_like_n8n(payload: dict) -> bool:
    return any(k in payload for k in ("workflow_id", "execution_id", "workflow_name"))


def _looks_like_make(payload: dict) -> bool:
    return any(k in payload for k in ("scenario_id", "blueprint", "make_token"))
