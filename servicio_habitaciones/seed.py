from db import init_db, get_conn


def seed():
    init_db()
    with get_conn() as conn:
        if conn.execute("SELECT COUNT(*) AS c FROM habitaciones").fetchone()["c"] > 0:
            return
        conn.executemany(
            "INSERT INTO habitaciones (id, tipo, capacidad) VALUES (?, ?, ?)",
            [("H-101", "Simple", 1), ("H-102", "Simple", 1),
             ("H-201", "Doble", 2), ("H-202", "Doble", 2),
             ("H-301", "Suite", 4)],
        )
        print("[seed] 5 habitaciones insertadas")


if __name__ == "__main__":
    seed()