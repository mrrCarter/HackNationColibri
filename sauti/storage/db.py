"""SQLite access. Parameterized queries only."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from sauti.farm_sheet import FarmSheet

_SCHEMA = Path(__file__).with_name("schema.sql")


def connect(path: Path | str) -> sqlite3.Connection:
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(_SCHEMA.read_text(encoding="utf-8"))
    return conn


def save_farm_sheet(conn: sqlite3.Connection, sheet: FarmSheet, source: str, transcript: str | None) -> int:
    """Store a confirmed farm sheet as a new version and return its version number."""
    with conn:
        cursor = conn.execute(
            "INSERT INTO farm_sheet_versions (data, content_hash, source, transcript, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                sheet.model_dump_json(),
                sheet.content_hash(),
                source,
                transcript,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
    return int(cursor.lastrowid)


def get_current_farm_sheet(conn: sqlite3.Connection) -> tuple[int, FarmSheet] | None:
    row = conn.execute(
        "SELECT version, data FROM farm_sheet_versions ORDER BY version DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return None
    return row[0], FarmSheet.model_validate_json(row[1])
