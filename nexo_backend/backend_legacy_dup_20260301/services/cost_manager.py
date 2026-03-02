import sqlite3
from datetime import datetime, timedelta

class CostManager:

    def __init__(self, db_path="costos.db"):
        self.db_path = db_path
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._conn() as con:
            con.execute("""
            CREATE TABLE IF NOT EXISTS registros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT,
                tokens INTEGER,
                modelo TEXT
            )
            """)

    def registrar(self, tokens, modelo="flash"):
        with self._conn() as con:
            con.execute(
                "INSERT INTO registros (fecha, tokens, modelo) VALUES (?, ?, ?)",
                (datetime.utcnow().isoformat(), tokens, modelo)
            )

    def obtener_presupuesto(self):
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("SELECT SUM(tokens) FROM registros")
            total = cur.fetchone()[0] or 0

        return {
            "tokens_totales": total,
            "estimacion_costo_usd": round(total * 0.000002, 4)
        }

    def historial_7_dias(self):
        limite = datetime.utcnow() - timedelta(days=7)
        with self._conn() as con:
            cur = con.cursor()
            cur.execute(
                "SELECT fecha, tokens FROM registros WHERE fecha >= ?",
                (limite.isoformat(),)
            )
            rows = cur.fetchall()

        total = sum(r[1] for r in rows)
        promedio = total / 7

        return {
            "total_7_dias": total,
            "promedio_diario": promedio,
            "registros": rows
        }
