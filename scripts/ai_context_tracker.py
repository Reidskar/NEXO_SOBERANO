"""
scripts/ai_context_tracker.py
===============================
Actualiza y retorna el estado del contexto IA del sistema NEXO SOBERANO.
Importado por WebAISupervisor como: from scripts.ai_context_tracker import update_ai_context_state
"""
from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)


def _get_rag_state() -> dict[str, Any]:
    """Retorna el estado del servicio RAG."""
    try:
        from backend.services.rag_service import get_rag_service
        rag = get_rag_service()

        if hasattr(rag, "estado"):
            state = rag.estado()
            return {
                "rag_loaded": bool(state.get("rag_loaded", False)),
                "total_documentos": int(state.get("total_documentos", 0) or 0),
                "total_chunks": int(state.get("total_chunks", 0) or 0),
                "checked_at": time.time(),
            }

        total_docs = 0
        total_chunks = 0
        rag_loaded = False

        # Intentar obtener métricas del servicio RAG
        if hasattr(rag, "total_docs"):
            total_docs = int(rag.total_docs or 0)
        if hasattr(rag, "total_chunks"):
            total_chunks = int(rag.total_chunks or 0)
        if hasattr(rag, "_loaded"):
            rag_loaded = bool(rag._loaded)
        elif total_chunks > 0:
            rag_loaded = True

        # Fallback: consultar directamente la base de datos
        if total_docs == 0:
            try:
                db_path = ROOT / "NEXO_SOBERANO" / "base_sqlite" / "boveda.db"
                if not db_path.exists():
                    db_path = ROOT / "base_sqlite" / "boveda.db"
                if db_path.exists():
                    import sqlite3
                    conn = sqlite3.connect(str(db_path))
                    cur = conn.cursor()
                    try:
                        cur.execute("SELECT COUNT(*) FROM documentos")
                        total_docs = cur.fetchone()[0] or 0
                    except Exception:
                        pass
                    try:
                        cur.execute("SELECT COUNT(*) FROM chunks")
                        total_chunks = cur.fetchone()[0] or 0
                    except Exception:
                        pass
                    conn.close()
                    rag_loaded = total_chunks > 0
            except Exception as e:
                logger.debug("RAG DB fallback failed: %s", e)

        return {
            "rag_loaded": rag_loaded,
            "total_documentos": total_docs,
            "total_chunks": total_chunks,
            "checked_at": time.time(),
        }
    except Exception as e:
        logger.warning("RAG state check failed: %s", e)
        return {
            "rag_loaded": False,
            "total_documentos": 0,
            "total_chunks": 0,
            "error": str(e),
            "checked_at": time.time(),
        }


def _get_google_photos_state() -> dict[str, Any]:
    """Retorna el estado de la integración Google Photos."""
    try:
        # Buscar logs de sync recientes
        logs_dir = ROOT / "logs"
        sync_log = logs_dir / "ai_context" / "google_photos_last.json"

        if sync_log.exists():
            import json
            data = json.loads(sync_log.read_text(encoding="utf-8"))
            return {
                "imported": int(data.get("imported", 0)),
                "last_sync_at": data.get("last_sync_at"),
                "error": data.get("error"),
            }

        # Fallback: contar imágenes en el directorio local
        photos_dir = ROOT / "documentos" / "google_photos"
        if not photos_dir.exists():
            photos_dir = ROOT / "media" / "photos"
        imported = len(list(photos_dir.glob("*.*"))) if photos_dir.exists() else 0

        return {
            "imported": imported,
            "last_sync_at": None,
            "error": None,
        }
    except Exception as e:
        logger.debug("Google Photos state check failed: %s", e)
        return {"imported": 0, "last_sync_at": None, "error": str(e)}


def update_ai_context_state() -> dict[str, Any]:
    """
    Función principal llamada por WebAISupervisor.
    Retorna el estado completo del contexto IA.
    """
    return {
        "rag": _get_rag_state(),
        "google_photos": _get_google_photos_state(),
        "updated_at": time.time(),
    }


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)
    state = update_ai_context_state()
    log.info(json.dumps(state, ensure_ascii=False, indent=2))
