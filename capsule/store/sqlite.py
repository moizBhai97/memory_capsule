"""
SQLite storage for capsule metadata.
Raw queries — no ORM. Fast, simple, zero extra dependencies.
Schema is append-only friendly — we never delete capsules, only mark them.
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from capsule.models import Capsule, CapsuleSource, CapsuleStatus, SourceApp, Reminder

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS capsules (
    id              TEXT PRIMARY KEY,
    source_type     TEXT NOT NULL DEFAULT 'unknown',
    source_app      TEXT NOT NULL DEFAULT 'unknown',
    source_file     TEXT,
    source_url      TEXT,
    source_sender   TEXT,
    source_chat     TEXT,
    raw_content     TEXT,
    summary         TEXT,
    tags            TEXT NOT NULL DEFAULT '[]',
    action_items    TEXT NOT NULL DEFAULT '[]',
    reminders       TEXT NOT NULL DEFAULT '[]',
    linked_capsules TEXT NOT NULL DEFAULT '[]',
    metadata        TEXT NOT NULL DEFAULT '{}',
    language        TEXT,
    duration_seconds REAL,
    status          TEXT NOT NULL DEFAULT 'pending',
    error           TEXT,
    timestamp       DATETIME NOT NULL,
    created_at      DATETIME NOT NULL,
    updated_at      DATETIME NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_capsules_timestamp   ON capsules(timestamp);
CREATE INDEX IF NOT EXISTS idx_capsules_status      ON capsules(status);
CREATE INDEX IF NOT EXISTS idx_capsules_source_app  ON capsules(source_app);
CREATE INDEX IF NOT EXISTS idx_capsules_source_type ON capsules(source_type);
CREATE INDEX IF NOT EXISTS idx_capsules_created_at  ON capsules(created_at);

-- Full-text search on raw_content + summary + tags
CREATE VIRTUAL TABLE IF NOT EXISTS capsules_fts USING fts5(
    id UNINDEXED,
    raw_content,
    summary,
    tags,
    source_sender,
    source_chat,
    content='capsules',
    content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS capsules_fts_insert AFTER INSERT ON capsules BEGIN
    INSERT INTO capsules_fts(rowid, id, raw_content, summary, tags, source_sender, source_chat)
    VALUES (new.rowid, new.id, new.raw_content, new.summary, new.tags, new.source_sender, new.source_chat);
END;

CREATE TRIGGER IF NOT EXISTS capsules_fts_update AFTER UPDATE ON capsules BEGIN
    INSERT INTO capsules_fts(capsules_fts, rowid, id, raw_content, summary, tags, source_sender, source_chat)
    VALUES ('delete', old.rowid, old.id, old.raw_content, old.summary, old.tags, old.source_sender, old.source_chat);
    INSERT INTO capsules_fts(rowid, id, raw_content, summary, tags, source_sender, source_chat)
    VALUES (new.rowid, new.id, new.raw_content, new.summary, new.tags, new.source_sender, new.source_chat);
END;
"""


class SQLiteStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript(SCHEMA)
            conn.commit()
        logger.info(f"SQLite store ready: {self.db_path}")

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")   # better concurrent read/write
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
        finally:
            conn.close()

    def save(self, capsule: Capsule) -> None:
        now = datetime.utcnow().isoformat()
        capsule.updated_at = datetime.utcnow()

        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO capsules
                (id, source_type, source_app, source_file, source_url,
                 source_sender, source_chat, raw_content, summary,
                 tags, action_items, reminders, linked_capsules, metadata,
                 language, duration_seconds, status, error,
                 timestamp, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                capsule.id,
                capsule.source_type.value,
                capsule.source_app.value,
                capsule.source_file,
                capsule.source_url,
                capsule.source_sender,
                capsule.source_chat,
                capsule.raw_content,
                capsule.summary,
                json.dumps(capsule.tags),
                json.dumps(capsule.action_items),
                json.dumps([r.__dict__ for r in capsule.reminders]),
                json.dumps(capsule.linked_capsules),
                json.dumps(capsule.metadata),
                capsule.language,
                capsule.duration_seconds,
                capsule.status.value,
                capsule.error,
                capsule.timestamp.isoformat(),
                capsule.created_at.isoformat(),
                capsule.updated_at.isoformat(),
            ))
            conn.commit()

    def get(self, capsule_id: str) -> Optional[Capsule]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM capsules WHERE id = ?", (capsule_id,)
            ).fetchone()
        return _row_to_capsule(row) if row else None

    def update_status(self, capsule_id: str, status: CapsuleStatus, error: str = None) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE capsules SET status=?, error=?, updated_at=? WHERE id=?",
                (status.value, error, datetime.utcnow().isoformat(), capsule_id),
            )
            conn.commit()

    def list(
        self,
        limit: int = 50,
        offset: int = 0,
        source_app: str = None,
        source_type: str = None,
        status: str = None,
        from_date: str = None,
        to_date: str = None,
    ) -> list[Capsule]:
        conditions = []
        params = []

        if source_app:
            conditions.append("source_app = ?")
            params.append(source_app)
        if source_type:
            conditions.append("source_type = ?")
            params.append(source_type)
        if status:
            conditions.append("status = ?")
            params.append(status)
        if from_date:
            conditions.append("timestamp >= ?")
            params.append(from_date)
        if to_date:
            conditions.append("timestamp <= ?")
            params.append(to_date)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params += [limit, offset]

        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM capsules {where} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                params,
            ).fetchall()

        return [_row_to_capsule(r) for r in rows]

    def keyword_search(
        self,
        query: str,
        limit: int = 20,
        from_date: str = None,
        to_date: str = None,
        source_app: str = None,
    ) -> list[tuple[Capsule, float]]:
        """FTS5 keyword search. Returns (capsule, rank) tuples."""
        date_filter = ""
        params = [query]

        if from_date or to_date or source_app:
            conditions = []
            if from_date:
                conditions.append("c.timestamp >= ?")
                params.append(from_date)
            if to_date:
                conditions.append("c.timestamp <= ?")
                params.append(to_date)
            if source_app:
                conditions.append("c.source_app = ?")
                params.append(source_app)
            date_filter = f"AND {' AND '.join(conditions)}"

        params.append(limit)

        with self._conn() as conn:
            rows = conn.execute(f"""
                SELECT c.*, fts.rank
                FROM capsules_fts fts
                JOIN capsules c ON c.id = fts.id
                WHERE capsules_fts MATCH ?
                {date_filter}
                ORDER BY fts.rank
                LIMIT ?
            """, params).fetchall()

        return [(_row_to_capsule(r), float(r["rank"])) for r in rows]

    def count(self) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM capsules").fetchone()[0]


def _row_to_capsule(row: sqlite3.Row) -> Capsule:
    c = Capsule()
    c.id = row["id"]
    c.source_type = CapsuleSource(row["source_type"])
    c.source_app = SourceApp(row["source_app"])
    c.source_file = row["source_file"]
    c.source_url = row["source_url"]
    c.source_sender = row["source_sender"]
    c.source_chat = row["source_chat"]
    c.raw_content = row["raw_content"]
    c.summary = row["summary"]
    c.tags = json.loads(row["tags"] or "[]")
    c.action_items = json.loads(row["action_items"] or "[]")
    c.reminders = [Reminder(**r) for r in json.loads(row["reminders"] or "[]")]
    c.linked_capsules = json.loads(row["linked_capsules"] or "[]")
    c.metadata = json.loads(row["metadata"] or "{}")
    c.language = row["language"]
    c.duration_seconds = row["duration_seconds"]
    c.status = CapsuleStatus(row["status"])
    c.error = row["error"]
    c.timestamp = datetime.fromisoformat(row["timestamp"])
    c.created_at = datetime.fromisoformat(row["created_at"])
    c.updated_at = datetime.fromisoformat(row["updated_at"])
    return c
