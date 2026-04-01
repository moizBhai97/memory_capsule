"""
Open Memory Capsule — Python SDK.
Simple, clean interface for capturing and searching memories programmatically.

Usage:
    from memory_capsule import MemoryCapsule

    mc = MemoryCapsule(base_url="http://localhost:8000")

    # Capture
    mc.add(file="voice_note.ogg", sender="Ahmed")
    mc.add(text="Project budget confirmed at 15k", source="meeting")
    mc.add(url="https://example.com/article")

    # Search
    results = mc.search("quote from Ahmed last week")
    for r in results:
        print(r.summary, r.tags)
"""

import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import httpx


@dataclass
class CapsuleResult:
    id: str
    summary: str
    tags: list[str]
    action_items: list[str]
    source_app: str
    source_sender: Optional[str]
    source_chat: Optional[str]
    timestamp: str
    snippet: str
    score: float
    raw_content: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict, score: float = 1.0, snippet: str = "") -> "CapsuleResult":
        return cls(
            id=d.get("id", ""),
            summary=d.get("summary", ""),
            tags=d.get("tags", []),
            action_items=d.get("action_items", []),
            source_app=d.get("source_app", ""),
            source_sender=d.get("source_sender"),
            source_chat=d.get("source_chat"),
            timestamp=d.get("timestamp", ""),
            snippet=snippet or d.get("summary", ""),
            score=score,
            raw_content=d.get("raw_content"),
        )

    def __repr__(self):
        return f"CapsuleResult(source={self.source_app}, sender={self.source_sender}, summary={self.summary[:60]!r})"


class MemoryCapsule:
    """
    Python client for Open Memory Capsule API.

    Args:
        base_url: URL of your running Memory Capsule instance
        api_key: Optional API key if you secured your instance
        timeout: Request timeout in seconds
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str = "",
        timeout: float = 60.0,
    ):
        self.base_url = base_url.rstrip("/")
        self._headers = {"X-Api-Key": api_key} if api_key else {}
        self._client = httpx.Client(timeout=timeout, headers=self._headers)

    def add(
        self,
        file: Optional[str] = None,
        text: Optional[str] = None,
        url: Optional[str] = None,
        source: str = "sdk",
        sender: Optional[str] = None,
        chat: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """
        Capture content into memory.

        Args:
            file: Path to file (audio, image, PDF, text)
            text: Raw text to capture
            url: URL to fetch and capture
            source: Source app name (e.g. "whatsapp", "meeting", "manual")
            sender: Who sent/created this content
            chat: Chat name, email subject, or context label
            metadata: Any extra platform-specific data

        Returns:
            Dict with status and message
        """
        if file:
            return self._upload_file(file, source, sender, chat, metadata)
        elif text or url:
            return self._post_text(text, url, source, sender, chat, metadata)
        else:
            raise ValueError("Provide file, text, or url")

    def search(
        self,
        query: str,
        limit: int = 10,
        source: Optional[str] = None,
        source_type: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> list[CapsuleResult]:
        """
        Search your memory with natural language.

        Args:
            query: Natural language query e.g. "quote from Ahmed last week"
            limit: Max results to return
            source: Filter by source app e.g. "whatsapp", "telegram", "email"
            source_type: Filter by content type e.g. "audio", "image", "pdf"
            from_date: ISO date string e.g. "2024-03-01"
            to_date: ISO date string e.g. "2024-03-31"

        Returns:
            List of CapsuleResult objects, ranked by relevance
        """
        params = {"q": query, "limit": limit}
        if source:
            params["source_app"] = source
        if source_type:
            params["source_type"] = source_type
        if from_date:
            params["from_date"] = from_date
        if to_date:
            params["to_date"] = to_date

        resp = self._client.get(f"{self.base_url}/api/search", params=params)
        resp.raise_for_status()
        data = resp.json()

        return [
            CapsuleResult.from_dict(
                r["capsule"],
                score=r.get("score", 1.0),
                snippet=r.get("snippet", ""),
            )
            for r in data.get("results", [])
        ]

    def list(
        self,
        limit: int = 20,
        source: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> list[CapsuleResult]:
        """List recent capsules."""
        params = {"limit": limit}
        if source:
            params["source_app"] = source
        if from_date:
            params["from_date"] = from_date
        if to_date:
            params["to_date"] = to_date

        resp = self._client.get(f"{self.base_url}/api/capsules", params=params)
        resp.raise_for_status()
        data = resp.json()
        return [CapsuleResult.from_dict(c) for c in data.get("capsules", [])]

    def get(self, capsule_id: str) -> Optional[CapsuleResult]:
        """Get a specific capsule by ID."""
        resp = self._client.get(f"{self.base_url}/api/capsules/{capsule_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return CapsuleResult.from_dict(resp.json())

    def health(self) -> dict:
        """Check if the API and AI providers are healthy."""
        resp = self._client.get(f"{self.base_url}/health/providers")
        resp.raise_for_status()
        return resp.json()

    def _upload_file(self, file_path, source, sender, chat, metadata):
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        data = {"source_app": source}
        if sender:
            data["source_sender"] = sender
        if chat:
            data["source_chat"] = chat

        with open(path, "rb") as f:
            resp = self._client.post(
                f"{self.base_url}/api/capsules/upload",
                data=data,
                files={"file": (path.name, f, mime)},
            )
        resp.raise_for_status()
        return resp.json()

    def _post_text(self, text, url, source, sender, chat, metadata):
        body = {"source_app": source}
        if text:
            body["text"] = text
        if url:
            body["url"] = url
        if sender:
            body["source_sender"] = sender
        if chat:
            body["source_chat"] = chat
        if metadata:
            body["metadata"] = metadata

        resp = self._client.post(f"{self.base_url}/api/capsules", json=body)
        resp.raise_for_status()
        return resp.json()

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
