from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS trips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS travelers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_id INTEGER NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    display_name TEXT NOT NULL,
    english_name TEXT NOT NULL DEFAULT '',
    aliases TEXT NOT NULL DEFAULT '',
    affiliation TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_id INTEGER NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    traveler_id INTEGER REFERENCES travelers(id) ON DELETE SET NULL,
    uploaded_by TEXT NOT NULL DEFAULT '',
    original_filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    mime_type TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT 'misc',
    status TEXT NOT NULL DEFAULT 'needs_review',
    extracted_text TEXT NOT NULL DEFAULT '',
    date_hint TEXT NOT NULL DEFAULT '',
    amount_hint TEXT NOT NULL DEFAULT '',
    match_confidence REAL NOT NULL DEFAULT 0,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def list_trips(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT trips.*,
               COUNT(DISTINCT travelers.id) AS traveler_count,
               COUNT(DISTINCT documents.id) AS document_count
        FROM trips
        LEFT JOIN travelers ON travelers.trip_id = trips.id
        LEFT JOIN documents ON documents.trip_id = trips.id
        GROUP BY trips.id
        ORDER BY trips.created_at DESC, trips.id DESC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def create_trip(conn: sqlite3.Connection, name: str, description: str = "") -> int:
    cur = conn.execute(
        "INSERT INTO trips (name, description) VALUES (?, ?)",
        (name.strip(), description.strip()),
    )
    conn.commit()
    return int(cur.lastrowid)


def get_trip(conn: sqlite3.Connection, trip_id: int) -> dict[str, Any] | None:
    return row_to_dict(conn.execute("SELECT * FROM trips WHERE id = ?", (trip_id,)).fetchone())


def add_traveler(
    conn: sqlite3.Connection,
    trip_id: int,
    display_name: str,
    english_name: str = "",
    aliases: str = "",
    affiliation: str = "",
) -> int:
    cur = conn.execute(
        """
        INSERT INTO travelers (trip_id, display_name, english_name, aliases, affiliation)
        VALUES (?, ?, ?, ?, ?)
        """,
        (trip_id, display_name.strip(), english_name.strip(), aliases.strip(), affiliation.strip()),
    )
    conn.commit()
    return int(cur.lastrowid)


def clear_travelers(conn: sqlite3.Connection, trip_id: int) -> None:
    conn.execute("DELETE FROM travelers WHERE trip_id = ?", (trip_id,))
    conn.commit()


def list_travelers(conn: sqlite3.Connection, trip_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM travelers WHERE trip_id = ? ORDER BY display_name",
        (trip_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def add_document(conn: sqlite3.Connection, **values: Any) -> int:
    cur = conn.execute(
        """
        INSERT INTO documents (
            trip_id, traveler_id, uploaded_by, original_filename, stored_path,
            mime_type, category, status, extracted_text, date_hint, amount_hint,
            match_confidence, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            values["trip_id"],
            values.get("traveler_id"),
            values.get("uploaded_by", ""),
            values["original_filename"],
            values["stored_path"],
            values.get("mime_type", ""),
            values.get("category", "misc"),
            values.get("status", "needs_review"),
            values.get("extracted_text", ""),
            values.get("date_hint", ""),
            values.get("amount_hint", ""),
            values.get("match_confidence", 0.0),
            values.get("notes", ""),
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def list_documents(conn: sqlite3.Connection, trip_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT documents.*, travelers.display_name AS traveler_name
        FROM documents
        LEFT JOIN travelers ON travelers.id = documents.traveler_id
        WHERE documents.trip_id = ?
        ORDER BY documents.created_at DESC, documents.id DESC
        """,
        (trip_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_document(conn: sqlite3.Connection, document_id: int) -> dict[str, Any] | None:
    return row_to_dict(
        conn.execute(
            """
            SELECT documents.*, travelers.display_name AS traveler_name
            FROM documents
            LEFT JOIN travelers ON travelers.id = documents.traveler_id
            WHERE documents.id = ?
            """,
            (document_id,),
        ).fetchone()
    )


def update_document_review(
    conn: sqlite3.Connection,
    document_id: int,
    traveler_id: int | None,
    category: str,
    status: str,
    notes: str,
) -> None:
    conn.execute(
        """
        UPDATE documents
        SET traveler_id = ?, category = ?, status = ?, notes = ?
        WHERE id = ?
        """,
        (traveler_id, category, status, notes, document_id),
    )
    conn.commit()

