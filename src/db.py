import sqlite3
import hashlib
import difflib
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
            content_text TEXT,
            last_checked TEXT NOT NULL
        )
    """)
    try:
        conn.execute("ALTER TABLE source_state ADD COLUMN content_text TEXT")
    except sqlite3.OperationalError:
        pass  # la columna ya existe (ejecuciones posteriores a la migracion)

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


def get_previous_text(conn, source_id: str):
    """Devuelve (content_text, es_primera_vez)."""
    row = conn.execute(
        "SELECT content_text FROM source_state WHERE source_id = ?", (source_id,)
    ).fetchone()
    if row is None:
        return None, True
    return row[0], False


def similarity(old_text: str, new_text: str) -> float:
    """1.0 = idénticos, 0.0 = completamente distintos.
    Tolera banners rotatorios, fechas de sesion, contadores, etc."""
    if not old_text:
        return 0.0
    return difflib.SequenceMatcher(None, old_text, new_text).ratio()


def update_state(conn, source_id: str, new_hash: str, new_text: str):
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT INTO source_state (source_id, content_hash, content_text, last_checked)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(source_id) DO UPDATE SET
            content_hash=excluded.content_hash,
            content_text=excluded.content_text,
            last_checked=excluded.last_checked
    """, (source_id, new_hash, new_text, now))
    conn.commit()


def record_alert(conn, source_id, source_name, municipio, urgencia, resumen, url, h):
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT INTO alerts (source_id, source_name, municipio, urgencia, resumen, url, content_hash, detected_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (source_id, source_name, municipio, urgencia, resumen, url, h, now))
    conn.commit()
