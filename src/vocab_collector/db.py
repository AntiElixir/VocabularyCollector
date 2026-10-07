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


def search_words(
    conn: sqlite3.Connection,
    query: str = "",
    offset: int = 0,
    limit: int = 20,
) -> list[tuple[int, str, str, str, str]]:
    """Search words with pagination. Returns (id, english, chinese, domain, created_at)."""
    if query.strip():
        pattern = f"%{query}%"
        cursor = conn.execute(
            "SELECT id, english, chinese, domain, created_at FROM vocabulary "
            "WHERE english LIKE ? OR chinese LIKE ? OR domain LIKE ? "
            "ORDER BY created_at DESC, id DESC "
            "LIMIT ? OFFSET ?",
            (pattern, pattern, pattern, limit, offset),
        )
    else:
        cursor = conn.execute(
            "SELECT id, english, chinese, domain, created_at FROM vocabulary "
            "ORDER BY created_at DESC, id DESC "
            "LIMIT ? OFFSET ?",
            (limit, offset),
        )
    return cursor.fetchall()


def count_words(conn: sqlite3.Connection, query: str = "") -> int:
    """Count total words matching the query."""
    if query.strip():
        pattern = f"%{query}%"
        cursor = conn.execute(
            "SELECT COUNT(*) FROM vocabulary "
            "WHERE english LIKE ? OR chinese LIKE ? OR domain LIKE ?",
            (pattern, pattern, pattern),
        )
    else:
        cursor = conn.execute("SELECT COUNT(*) FROM vocabulary")
    return cursor.fetchone()[0]


def delete_word(conn: sqlite3.Connection, word_id: int) -> bool:
    """Delete a word by ID. Returns True if a row was deleted."""
    cursor = conn.execute("DELETE FROM vocabulary WHERE id = ?", (word_id,))
    conn.commit()
    return cursor.rowcount > 0


def get_weekly_count(conn: sqlite3.Connection) -> int:
    """Count words added in the last 7 days."""
    cursor = conn.execute(
        "SELECT COUNT(*) FROM vocabulary "
        "WHERE created_at >= datetime('now', '-7 days')"
    )
    return cursor.fetchone()[0]


def get_domain_count(conn: sqlite3.Connection) -> int:
    """Count distinct domains."""
    cursor = conn.execute("SELECT COUNT(DISTINCT domain) FROM vocabulary")
    return cursor.fetchone()[0]