import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "cache.db"


def get_connection() -> sqlite3.Connection:
    """Return a connection to the SQLite cache database."""
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    """Create cache.db and the vin_cache table if they do not already exist."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vin_cache (
                vin TEXT PRIMARY KEY,
                make TEXT,
                model TEXT,
                model_year TEXT,
                body_class TEXT
            )
            """
        )

def get_cached_vin(vin: str) -> dict | None:
    """Return the cached record for a VIN, or None if not cached."""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT vin, make, model, model_year, body_class FROM vin_cache WHERE vin = ?",
            (vin,),
        )
        row = cursor.fetchone()

    if row is None:
        return None

    return {
        "vin": row[0],
        "make": row[1],
        "model": row[2],
        "model_year": row[3],
        "body_class": row[4],
    }


def insert_vin(vin: str, data: dict) -> None:
    """Insert a new row into vin_cache for the given VIN and decoded data."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO vin_cache (vin, make, model, model_year, body_class) VALUES (?, ?, ?, ?, ?)",
            (vin, data["make"], data["model"], data["model_year"], data["body_class"]),
        )
        conn.commit()

def delete_vin(vin: str) -> None:
    """Delete the row for the given VIN from vin_cache, if it exists."""
    with get_connection() as conn:
        conn.execute("DELETE FROM vin_cache WHERE vin = ?", (vin,))
        conn.commit()