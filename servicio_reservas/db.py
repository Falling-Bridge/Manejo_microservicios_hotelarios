import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.getenv("DB_PATH", "/app/data/reservas.db")


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS huespedes (
                id TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                telefono TEXT
            );
            CREATE TABLE IF NOT EXISTS reservas (
                id TEXT PRIMARY KEY,
                huesped_id TEXT NOT NULL,
                fecha TEXT NOT NULL,
                estado TEXT NOT NULL,
                habitacion_id TEXT,
                creada_en TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS idempotency (
                key TEXT PRIMARY KEY,
                respuesta TEXT NOT NULL,
                creada_en TEXT NOT NULL
            );
        """)


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=5, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()