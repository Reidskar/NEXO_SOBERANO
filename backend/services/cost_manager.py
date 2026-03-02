"""
Gestor de costos real — Registra TOKENS REALES de cada llamada a Gemini
"""

import sqlite3
from datetime import datetime, date
from typing import Optional
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend import config

logger = logging.getLogger(__name__)

class CostManager:
    """
    Registra y monitorea costos reales de API.
    Tabla: costos_api (fecha, modelo, tokens_in, tokens_out, operacion)
    """

    def __init__(self):
        self.db_path = config.DB_PATH
        self._ensure_table()

    def _get_conn(self) -> sqlite3.Connection:
        """Retorna conexión a SQLite"""
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_table(self):
        """Crea tabla si no existe"""
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS costos_api (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha       TEXT,
                modelo      TEXT,
                tokens_in   INTEGER,
                tokens_out  INTEGER,
                operacion   TEXT
            )
        """)
        conn.commit()
        conn.close()

    def registrar(self, modelo: str, tokens_in: int, tokens_out: int, operacion: str = ""):
        """
        Registra token usage real de una llamada a Gemini.
        
        Args:
            modelo: "gemini-1.5-flash" o "gemini-1.5-pro"
            tokens_in: Tokens en input
            tokens_out: Tokens en output
            operacion: "clasificacion", "rag_consulta", "embedding", etc.
        """
        try:
            conn = self._get_conn()
            conn.execute(
                "INSERT INTO costos_api (fecha, modelo, tokens_in, tokens_out, operacion) VALUES (?, ?, ?, ?, ?)",
                (datetime.now().isoformat(), modelo, tokens_in, tokens_out, operacion)
            )
            conn.commit()
            conn.close()
            logger.debug(f"Registrado: {modelo} | {tokens_in}→{tokens_out} | {operacion}")
        except Exception as e:
            logger.error(f"Error registrando costo: {e}")

    def tokens_hoy(self) -> int:
        """Retorna tokens consumidos hoy"""
        try:
            conn = self._get_conn()
            hoy = date.today().isoformat()
            row = conn.execute(
                "SELECT COALESCE(SUM(tokens_in + tokens_out), 0) FROM costos_api WHERE fecha LIKE ?",
                (hoy + "%",)
            ).fetchone()
            conn.close()
            return row[0] if row else 0
        except Exception as e:
            logger.error(f"Error obteniendo tokens_hoy: {e}")
            return 0

    def puede_operar(self) -> bool:
        """¿Tenemos presupuesto para hoy?"""
        return self.tokens_hoy() < config.MAX_TOKENS_DIA

    def porcentaje_usado(self) -> float:
        """% del presupuesto usado hoy"""
        consumo = self.tokens_hoy()
        if config.MAX_TOKENS_DIA <= 0:
            return 0.0
        return (consumo / config.MAX_TOKENS_DIA) * 100

    def estado(self) -> dict:
        """Estado actual del presupuesto"""
        hoy = self.tokens_hoy()
        maximo = config.MAX_TOKENS_DIA
        return {
            "tokens_usados_hoy": hoy,
            "limite_diario": maximo,
            "porcentaje": self.porcentaje_usado(),
            "disponible": maximo - hoy,
            "puede_operar": self.puede_operar(),
        }

    def historial_7_dias(self) -> dict:
        """Consumo de los últimos 7 días"""
        try:
            conn = self._get_conn()
            rows = conn.execute("""
                SELECT 
                    DATE(fecha) as dia,
                    SUM(tokens_in + tokens_out) as total
                FROM costos_api
                WHERE fecha >= datetime('now', '-7 days')
                GROUP BY DATE(fecha)
                ORDER BY dia DESC
            """).fetchall()
            conn.close()
            return {row["dia"]: row["total"] for row in rows}
        except Exception as e:
            logger.error(f"Error obteniendo historial: {e}")
            return {}


# Instancia global
_cost_manager: Optional[CostManager] = None

def get_cost_manager() -> CostManager:
    """Obtiene o crea gestor de costos"""
    global _cost_manager
    if _cost_manager is None:
        _cost_manager = CostManager()
    return _cost_manager
