import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.getenv("DB_PATH", "/app/data/habitaciones.db")


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS habitaciones (
                id TEXT PRIMARY KEY,
                tipo TEXT NOT NULL,
                capacidad INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ocupaciones (
                habitacion_id TEXT NOT NULL,
                fecha TEXT NOT NULL,
                reserva_id TEXT NOT NULL,
                PRIMARY KEY (habitacion_id, fecha)
            );
            CREATE INDEX IF NOT EXISTS idx_ocupaciones_fecha ON ocupaciones(fecha);
        """)


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=5, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def habitaciones_libres(fecha):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT h.id FROM habitaciones h
            WHERE h.id NOT IN (SELECT habitacion_id FROM ocupaciones WHERE fecha = ?)
            ORDER BY h.id
        """, (fecha,)).fetchall()
    return [r["id"] for r in rows]


def reservar_habitacion(fecha, reserva_id):
    with get_conn() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute("""
                SELECT h.id FROM habitaciones h
                WHERE h.id NOT IN (SELECT habitacion_id FROM ocupaciones WHERE fecha = ?)
                ORDER BY h.id LIMIT 1
            """, (fecha,)).fetchone()
            if row is None:
                conn.execute("ROLLBACK")
                return None
            conn.execute(
                "INSERT INTO ocupaciones (habitacion_id, fecha, reserva_id) VALUES (?, ?, ?)",
                (row["id"], fecha, reserva_id),
            )
            conn.execute("COMMIT")
            return row["id"]
        except Exception:
            conn.execute("ROLLBACK")
            raise


def liberar_habitacion(fecha, reserva_id):
    with get_conn() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute(
                "SELECT habitacion_id FROM ocupaciones WHERE fecha = ? AND reserva_id = ?",
                (fecha, reserva_id),
            ).fetchone()
            if row is None:
                conn.execute("ROLLBACK")
                return None
            conn.execute(
                "DELETE FROM ocupaciones WHERE fecha = ? AND reserva_id = ?",
                (fecha, reserva_id),
            )
            conn.execute("COMMIT")
            return row["habitacion_id"]
        except Exception:
            conn.execute("ROLLBACK")
            raise


def disponibilidad_rango(inicio, fin):
    from datetime import date, timedelta
    d1, d2 = date.fromisoformat(inicio), date.fromisoformat(fin)
    if d2 < d1:
        return []
    resultado, d = [], d1
    while d <= d2:
        f = d.isoformat()
        resultado.append((f, len(habitaciones_libres(f))))
        d += timedelta(days=1)
    return resultado