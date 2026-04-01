"""
Core data models for Memory Capsule.
Every piece of captured content becomes a Capsule — regardless of source.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class CapsuleSource(str, Enum):
    AUDIO = "audio"
    IMAGE = "image"
    SCREENSHOT = "screenshot"
    PDF = "pdf"
    TEXT = "text"
    URL = "url"
    VIDEO = "video"
    EMAIL = "email"
    UNKNOWN = "unknown"


class CapsuleStatus(str, Enum):
    PENDING = "pending"        # received, not yet processed
    PROCESSING = "processing"  # currently being processed
    READY = "ready"            # fully processed, searchable
    FAILED = "failed"          # processing failed


class SourceApp(str, Enum):
    WHATSAPP_PERSONAL = "whatsapp_personal"
    WHATSAPP_BUSINESS = "whatsapp_business"
    TELEGRAM = "telegram"
    GMAIL = "gmail"
    OUTLOOK = "outlook"
    EMAIL = "email"
    ZOOM = "zoom"
    GOOGLE_MEET = "google_meet"
    SLACK = "slack"
    DISCORD = "discord"
    WATCH_FOLDER = "watch_folder"
    BROWSER = "browser"
    CLI = "cli"
    API = "api"
    UNKNOWN = "unknown"


@dataclass
class Reminder:
    date: str          # ISO8601
    note: str
    sent: bool = False


@dataclass
class Capsule:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # --- Source info ---
    source_type: CapsuleSource = CapsuleSource.UNKNOWN
    source_app: SourceApp = SourceApp.UNKNOWN
    source_file: Optional[str] = None       # local path to original file
    source_url: Optional[str] = None        # original URL if applicable
    source_sender: Optional[str] = None     # who sent it (name or identifier)
    source_chat: Optional[str] = None       # chat name / email subject / channel

    # --- Content ---
    raw_content: Optional[str] = None       # transcription / OCR / extracted text
    summary: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    reminders: list[Reminder] = field(default_factory=list)
    linked_capsules: list[str] = field(default_factory=list)

    # --- Metadata ---
    metadata: dict = field(default_factory=dict)   # platform-specific extras
    language: Optional[str] = None                 # detected language
    duration_seconds: Optional[float] = None       # for audio/video

    # --- State ---
    status: CapsuleStatus = CapsuleStatus.PENDING
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)   # when content was created
    created_at: datetime = field(default_factory=datetime.utcnow)  # when capsule was created
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_type": self.source_type.value,
            "source_app": self.source_app.value,
            "source_file": self.source_file,
            "source_url": self.source_url,
            "source_sender": self.source_sender,
            "source_chat": self.source_chat,
            "raw_content": self.raw_content,
            "summary": self.summary,
            "tags": self.tags,
            "action_items": self.action_items,
            "reminders": [r.__dict__ for r in self.reminders],
            "linked_capsules": self.linked_capsules,
            "metadata": self.metadata,
            "language": self.language,
            "duration_seconds": self.duration_seconds,
            "status": self.status.value,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Capsule":
        c = cls()
        c.id = d.get("id", c.id)
        c.source_type = CapsuleSource(d.get("source_type", "unknown"))
        c.source_app = SourceApp(d.get("source_app", "unknown"))
        c.source_file = d.get("source_file")
        c.source_url = d.get("source_url")
        c.source_sender = d.get("source_sender")
        c.source_chat = d.get("source_chat")
        c.raw_content = d.get("raw_content")
        c.summary = d.get("summary")
        c.tags = d.get("tags", [])
        c.action_items = d.get("action_items", [])
        c.reminders = [Reminder(**r) for r in d.get("reminders", [])]
        c.linked_capsules = d.get("linked_capsules", [])
        c.metadata = d.get("metadata", {})
        c.language = d.get("language")
        c.duration_seconds = d.get("duration_seconds")
        c.status = CapsuleStatus(d.get("status", "pending"))
        c.error = d.get("error")
        if "timestamp" in d:
            c.timestamp = datetime.fromisoformat(d["timestamp"])
        if "created_at" in d:
            c.created_at = datetime.fromisoformat(d["created_at"])
        if "updated_at" in d:
            c.updated_at = datetime.fromisoformat(d["updated_at"])
        return c
