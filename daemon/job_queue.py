"""
Simple SQLite-backed job queue.
No Redis, no Celery — just a jobs table in SQLite.
Good enough for local single-user use. Handles restarts gracefully.
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_type    TEXT NOT NULL,
    payload     TEXT NOT NULL DEFAULT '{}',
    status      TEXT NOT NULL DEFAULT 'pending',
    attempts    INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    error       TEXT,
    created_at  DATETIME NOT NULL,
    updated_at  DATETIME NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at);
"""


class JobQueue:
    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        with self._conn() as conn:
            conn.executescript(SCHEMA)
            conn.commit()
        # Reset any jobs stuck in "processing" from a previous crashed run
        self._reset_stuck_jobs()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
        finally:
            conn.close()

    def enqueue(self, job_type: str, payload: dict) -> int:
        now = datetime.utcnow().isoformat()
        with self._conn() as conn:
            cursor = conn.execute(
                "INSERT INTO jobs (job_type, payload, status, created_at, updated_at) VALUES (?,?,?,?,?)",
                (job_type, json.dumps(payload), "pending", now, now),
            )
            conn.commit()
            job_id = cursor.lastrowid
        logger.debug("Enqueued job %s: %s", job_id, job_type)
        return job_id

    def dequeue(self) -> dict | None:
        """Get next pending job and mark it as processing. Returns None if queue empty."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE status='pending' AND attempts < max_attempts ORDER BY id LIMIT 1"
            ).fetchone()

            if not row:
                return None

            conn.execute(
                "UPDATE jobs SET status='processing', attempts=attempts+1, updated_at=? WHERE id=?",
                (datetime.utcnow().isoformat(), row["id"]),
            )
            conn.commit()

        return {
            "id": row["id"],
            "job_type": row["job_type"],
            "payload": json.loads(row["payload"]),
            "attempts": row["attempts"] + 1,
        }

    def complete(self, job_id: int) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE jobs SET status='done', updated_at=? WHERE id=?",
                (datetime.utcnow().isoformat(), job_id),
            )
            conn.commit()

    def fail(self, job_id: int, error: str) -> None:
        with self._conn() as conn:
            row = conn.execute("SELECT attempts, max_attempts FROM jobs WHERE id=?", (job_id,)).fetchone()
            status = "failed" if row["attempts"] >= row["max_attempts"] else "pending"
            conn.execute(
                "UPDATE jobs SET status=?, error=?, updated_at=? WHERE id=?",
                (status, error[:500], datetime.utcnow().isoformat(), job_id),
            )
            conn.commit()
        logger.warning("Job %s failed: %s", job_id, error[:100])

    def pending_count(self) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM jobs WHERE status='pending'").fetchone()[0]

    def _reset_stuck_jobs(self):
        """Reset jobs that were processing when the daemon last crashed."""
        with self._conn() as conn:
            count = conn.execute(
                "UPDATE jobs SET status='pending', updated_at=? WHERE status='processing'",
                (datetime.utcnow().isoformat(),),
            ).rowcount
            conn.commit()
        if count:
            logger.info("Reset %s stuck jobs from previous run", count)
