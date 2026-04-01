"""Tests for Capsule model serialization."""

import pytest
from datetime import datetime
from capsule.models import Capsule, CapsuleSource, CapsuleStatus, SourceApp, Reminder


def test_capsule_to_dict():
    c = Capsule(
        source_type=CapsuleSource.AUDIO,
        source_app=SourceApp.WHATSAPP_PERSONAL,
        source_sender="Ahmed",
        summary="Client confirmed $15k budget",
        tags=["ahmed", "budget", "15k"],
        action_items=["Follow up by Friday"],
    )
    d = c.to_dict()
    assert d["source_type"] == "audio"
    assert d["source_app"] == "whatsapp_personal"
    assert d["source_sender"] == "Ahmed"
    assert d["tags"] == ["ahmed", "budget", "15k"]
    assert d["action_items"] == ["Follow up by Friday"]


def test_capsule_roundtrip():
    original = Capsule(
        source_type=CapsuleSource.PDF,
        source_app=SourceApp.EMAIL,
        source_sender="client@example.com",
        summary="Quote for website",
        tags=["quote", "website"],
        reminders=[Reminder(date="2024-04-20", note="Follow up on quote")],
    )
    restored = Capsule.from_dict(original.to_dict())
    assert restored.id == original.id
    assert restored.source_type == original.source_type
    assert restored.source_app == original.source_app
    assert restored.tags == original.tags
    assert len(restored.reminders) == 1
    assert restored.reminders[0].note == "Follow up on quote"


def test_capsule_default_status():
    c = Capsule()
    assert c.status == CapsuleStatus.PENDING
