import sqlite3
import hashlib
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "radar.db"


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS source_state (
            source_id TEXT PRIMARY KEY,
            content_hash TEXT NOT NULL,
            last_checked TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL,
            source_name TEXT NOT NULL,
            municipio TEXT,
            urgencia TEXT NOT NULL,
            resumen TEXT NOT NULL,
            url TEXT,
            content_hash TEXT NOT NULL,
            detected_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def has_changed(conn, source_id: str, new_hash: str) -> bool:
    row = conn.execute(
        "SELECT content_hash FROM source_state WHERE source_id = ?", (source_id,)
    ).fetchone()
    if row is None:
        return True  # primera vez que se ve esta fuente -> tratamos como "nuevo"
    return row[0] != new_hash


def update_state(conn, source_id: str, new_hash: str):
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT INTO source_state (source_id, content_hash, last_checked)
        VALUES (?, ?, ?)
        ON CONFLICT(source_id) DO UPDATE SET content_hash=excluded.content_hash, last_checked=excluded.last_checked
    """, (source_id, new_hash, now))
    conn.commit()


def record_alert(conn, source_id, source_name, municipio, urgencia, resumen, url, h):
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT INTO alerts (source_id, source_name, municipio, urgencia, resumen, url, content_hash, detected_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (source_id, source_name, municipio, urgencia, resumen, url, h, now))
    conn.commit()
