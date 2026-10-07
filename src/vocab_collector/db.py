"""SQLite storage: schema, case-insensitive dedup insert, listing."""

from __future__ import annotations

import sqlite3
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS vocabulary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    english TEXT NOT NULL COLLATE NOCASE UNIQUE,
    chinese TEXT NOT NULL,
    domain TEXT NOT NULL,
    created_at TEXT NOT NULL,
    fsrs_state INTEGER,
    fsrs_step INTEGER,
    fsrs_stability REAL,
    fsrs_difficulty REAL,
    fsrs_due TEXT,
    fsrs_last_review TEXT
);
"""


def connect(path: Path | str) -> sqlite3.Connection:
    """Open (and create, if needed) the vocabulary database."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: the app opens the database on the main thread to
    # build the initial HTML page, then hands the connection to the single
    # collector worker thread. Only one thread ever touches it at a time.
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    conn.commit()


def insert_word(
    conn: sqlite3.Connection,
    english: str,
    chinese: str,
    domain: str,
    created_at: str,
) -> bool:
    """Insert unless the word already exists (case-insensitive).

    Returns True when a new row was written, False for a duplicate.
    """
    cursor = conn.execute(
        "INSERT INTO vocabulary (english, chinese, domain, created_at) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(english) DO NOTHING",
        (english, chinese, domain, created_at),
    )
    conn.commit()
    return cursor.rowcount > 0


def list_all(conn: sqlite3.Connection) -> list[tuple[str, str, str, str]]:
    """All rows, newest first."""
    cursor = conn.execute(
        "SELECT english, chinese, domain, created_at FROM vocabulary "
        "ORDER BY created_at DESC, id DESC"
    )
    return cursor.fetchall()