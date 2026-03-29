"""
backend/routes/sesiones.py
===========================
Gestión de sesiones de análisis con memoria semántica acumulativa.
Cada sesión queda indexada en Qdrant para recuperación futura.
"""
from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sesiones", tags=["sesiones"])

DB_PATH = Path("sesiones.db")

# ─── DB init ──────────────────────────────────────────────────────────────────
def _ensure_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sesiones (
            id TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            tema TEXT,
            estado TEXT DEFAULT 'activa',
            resumen TEXT,
            created_at TEXT,
            closed_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mensajes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sesion_id TEXT NOT NULL,
            rol TEXT NOT NULL,
            contenido TEXT NOT NULL,
            fuentes TEXT,
            ts TEXT,
            FOREIGN KEY(sesion_id) REFERENCES sesiones(id)
        )
    """)
    conn.commit()
    conn.close()

_ensure_db()

# ─── Schemas ──────────────────────────────────────────────────────────────────
class IniciarSesionReq(BaseModel):
    nombre: str
    tema: Optional[str] = None

class GuardarMensajeReq(BaseModel):
    sesion_id: str
    rol: str                    # "usuario" | "nexo"
    contenido: str
    fuentes: Optional[List[str]] = None

class CerrarSesionReq(BaseModel):
    sesion_id: str
    resumen: Optional[str] = None

class BuscarSesionesReq(BaseModel):
    query: str
    limit: int = 10

# ─── Endpoints ────────────────────────────────────────────────────────────────
@router.post("/iniciar")
async def iniciar_sesion(req: IniciarSesionReq):
    """Crea una nueva sesión de análisis."""
    sesion_id = str(uuid.uuid4())[:12]
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO sesiones (id, nombre, tema, estado, created_at) VALUES (?,?,?,?,?)",
        (sesion_id, req.nombre, req.tema, "activa", now)
    )
    conn.commit()
    conn.close()
    logger.info(f"[SESION] Iniciada: {sesion_id} — {req.nombre}")
    return {"ok": True, "sesion_id": sesion_id, "nombre": req.nombre, "created_at": now}


@router.post("/guardar-mensaje")
async def guardar_mensaje(req: GuardarMensajeReq):
    """Persiste un intercambio de la sesión y trata de indexarlo en Qdrant."""
    now = datetime.now(timezone.utc).isoformat()
    fuentes_str = ",".join(req.fuentes or [])

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO mensajes (sesion_id, rol, contenido, fuentes, ts) VALUES (?,?,?,?,?)",
        (req.sesion_id, req.rol, req.contenido, fuentes_str, now)
    )
    conn.commit()
    conn.close()

    # Intentar push a Qdrant si está disponible
    if req.rol == "nexo":
        try:
            from NEXO_CORE.services.qdrant_service import indexar_fragmento
            await indexar_fragmento(
                texto=req.contenido,
                metadata={
                    "tipo": "sesion_analisis",
                    "sesion_id": req.sesion_id,
                    "ts": now,
                    "fuentes": fuentes_str,
                }
            )
        except Exception as e:
            logger.debug(f"[SESION] Qdrant no disponible: {e}")

    return {"ok": True, "ts": now}


@router.post("/cerrar")
async def cerrar_sesion(req: CerrarSesionReq):
    """Cierra una sesión y guarda el resumen generado."""
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)

    # Generar resumen automático si no se proporcionó
    resumen = req.resumen
    if not resumen:
        conn2 = sqlite3.connect(DB_PATH)
        msgs = conn2.execute(
            "SELECT rol, contenido FROM mensajes WHERE sesion_id=? ORDER BY id",
            (req.sesion_id,)
        ).fetchall()
        conn2.close()
        if msgs:
            transcript = "\n".join(f"[{r}] {c[:200]}" for r, c in msgs)
            try:
                from NEXO_CORE.services.multi_ai_service import consultar_ia
                resumen = consultar_ia(
                    f"Resume en máximo 3 párrafos esta sesión de análisis:\n{transcript[:3000]}"
                )
            except Exception:
                resumen = f"Sesión con {len(msgs)} intercambios."

    conn.execute(
        "UPDATE sesiones SET estado='cerrada', resumen=?, closed_at=? WHERE id=?",
        (resumen, now, req.sesion_id)
    )
    conn.commit()
    conn.close()

    # Indexar resumen en Qdrant
    try:
        from NEXO_CORE.services.qdrant_service import indexar_fragmento
        await indexar_fragmento(
            texto=resumen,
            metadata={"tipo": "resumen_sesion", "sesion_id": req.sesion_id, "ts": now}
        )
    except Exception as e:
        logger.debug(f"[SESION] Qdrant resumen: {e}")

    logger.info(f"[SESION] Cerrada: {req.sesion_id}")
    return {"ok": True, "resumen": resumen, "closed_at": now}


@router.get("/listar")
async def listar_sesiones(limite: int = 30):
    """Lista sesiones recientes."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, nombre, tema, estado, resumen, created_at, closed_at FROM sesiones ORDER BY created_at DESC LIMIT ?",
        (limite,)
    ).fetchall()
    conn.close()
    return {"sesiones": [dict(r) for r in rows]}


@router.get("/mensajes/{sesion_id}")
async def mensajes_sesion(sesion_id: str):
    """Obtiene todos los mensajes de una sesión."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT rol, contenido, fuentes, ts FROM mensajes WHERE sesion_id=? ORDER BY id",
        (sesion_id,)
    ).fetchall()
    conn.close()
    return {"mensajes": [dict(r) for r in rows]}


@router.post("/buscar")
async def buscar_sesiones(req: BuscarSesionesReq):
    """Búsqueda semántica en la memoria de sesiones vía Qdrant."""
    try:
        from NEXO_CORE.services.qdrant_service import buscar_similares
        resultados = await buscar_similares(req.query, limit=req.limit, filtro={"tipo": "sesion_analisis"})
        return {"resultados": resultados}
    except Exception as e:
        # Fallback: búsqueda textual en SQLite
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT sesion_id, rol, contenido, ts FROM mensajes WHERE contenido LIKE ? LIMIT ?",
            (f"%{req.query}%", req.limit)
        ).fetchall()
        conn.close()
        return {"resultados": [dict(r) for r in rows], "modo": "sqlite_fallback"}
