"""
scripts/ai_context_tracker.py
===============================
Actualiza y retorna el estado del contexto IA del sistema NEXO SOBERANO.
Importado por WebAISupervisor como: from scripts.ai_context_tracker import update_ai_context_state
"""
from __future__ import annotations

from utils.ai_core import get_logger
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logger = get_logger("ai_context_tracker")


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
                "coleccion_items": int(state.get("coleccion_items", 0) or 0),
                "checked_at": time.time(),
            }
        else:
            return {
                "rag_loaded": False,
                "total_documentos": 0,
                "total_chunks": 0,
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
    state = update_ai_context_state()
    logger.info(json.dumps(state, ensure_ascii=False, indent=2))
