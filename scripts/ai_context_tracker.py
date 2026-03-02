from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.connectors.local_onedrive_connector import list_recent_local_onedrive_files, resolve_onedrive_local_root


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

DOC_PATH = ROOT / "documentos" / "ESTADO_CONTEXTO_IA.md"
JSON_PATH = ROOT / "logs" / "ai_context_status.json"
SYNC_LAST_PATH = ROOT / "logs" / "sync_unified_last.json"
SYNC_STATUS_PATH = ROOT / "logs" / "sync_unified_status.json"
DB_PATH = ROOT / "NEXO_SOBERANO" / "base_sqlite" / "boveda.db"


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _collect_db_stats() -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "total_documentos": 0,
        "vectorizados": 0,
    }
    if not DB_PATH.exists():
        return out
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        out["total_documentos"] = int(cur.execute("SELECT COUNT(*) FROM evidencia").fetchone()[0])
        out["vectorizados"] = int(cur.execute("SELECT COUNT(*) FROM evidencia WHERE vectorizado=1").fetchone()[0])
        conn.close()
    except Exception as exc:
        out["error"] = str(exc)
    return out


def _collect_rag_stats() -> Dict[str, Any]:
    try:
        from backend.services.rag_service import get_rag_service

        rag = get_rag_service()
        state = rag.estado() or {}
        return {
            "status": state.get("status", "unknown"),
            "rag_loaded": bool(state.get("rag_loaded", False)),
            "total_documentos": int(state.get("total_documentos", 0) or 0),
            "total_chunks": int(state.get("total_chunks", 0) or 0),
            "coleccion_items": int(state.get("coleccion_items", 0) or 0),
            "presupuesto": state.get("presupuesto", {}),
        }
    except Exception as exc:
        return {
            "status": "error",
            "rag_loaded": False,
            "error": str(exc),
        }


def _collect_onedrive_stats() -> Dict[str, Any]:
    root = resolve_onedrive_local_root()
    files = []
    error = None
    try:
        files = list_recent_local_onedrive_files(top=10)
    except Exception as exc:
        error = str(exc)
    return {
        "local_root": str(root) if root else "",
        "visible_recent": len(files),
        "error": error,
    }


def _collect_google_photos_status(sync_last: Dict[str, Any]) -> Dict[str, Any]:
    gp = (sync_last.get("summary") or {}).get("google_photos") or {}
    alerts = (sync_last.get("result") or {}).get("alerts") or []
    gp_error = ""
    for item in alerts:
        if (item or {}).get("source") == "google_photos":
            gp_error = str((item or {}).get("error") or "")
            break
    return {
        "imported": int(gp.get("imported", 0) or 0),
        "skipped": int(gp.get("skipped", 0) or 0),
        "errors": int(gp.get("errors", 0) or 0),
        "last_error": gp_error,
    }


def collect_status() -> Dict[str, Any]:
    sync_last = _read_json(SYNC_LAST_PATH)
    sync_status = _read_json(SYNC_STATUS_PATH)
    db_stats = _collect_db_stats()
    rag_stats = _collect_rag_stats()
    onedrive = _collect_onedrive_stats()
    photos = _collect_google_photos_status(sync_last)

    return {
        "timestamp": _now_iso(),
        "sync": {
            "last": sync_last,
            "status": sync_status,
        },
        "db": db_stats,
        "rag": rag_stats,
        "onedrive": onedrive,
        "google_photos": photos,
    }


def _render_markdown(status: Dict[str, Any]) -> str:
    rag = status.get("rag") or {}
    db = status.get("db") or {}
    onedrive = status.get("onedrive") or {}
    photos = status.get("google_photos") or {}
    sync_summary = (((status.get("sync") or {}).get("last") or {}).get("summary") or {})

    lines = [
        "# Estado de contexto IA (auto-actualizado)",
        "",
        f"Fecha: {status.get('timestamp', '')}",
        "",
        "## Resumen operativo",
        f"- RAG backend: {'OK' if rag.get('rag_loaded') else 'DEGRADED'}",
        f"- Total documentos (RAG): {rag.get('total_documentos', 0)}",
        f"- Chunks indexados: {rag.get('total_chunks', 0)}",
        f"- SQLite evidencia: total={db.get('total_documentos', 0)} vectorizados={db.get('vectorizados', 0)}",
        "",
        "## Fuentes",
        f"- Google Drive: analyzed={((sync_summary.get('google_drive') or {}).get('analyzed', 0))} classified={((sync_summary.get('google_drive') or {}).get('classified', 0))} errors={((sync_summary.get('google_drive') or {}).get('errors', 0))}",
        f"- OneDrive local: root='{onedrive.get('local_root', '')}' visibles={onedrive.get('visible_recent', 0)} error={onedrive.get('error') or 'none'}",
        f"- Google Photos: imported={photos.get('imported', 0)} skipped={photos.get('skipped', 0)} errors={photos.get('errors', 0)}",
    ]

    if photos.get("last_error"):
        lines.append(f"- Google Photos último error: {photos.get('last_error')}")

    lines.extend([
        "",
        "## Uso con asistentes (Gemini/Copilot)",
        "- Referencia este archivo al iniciar sesión de chat para contexto vivo del sistema.",
        "- Recomendación de prompt: 'Usa el estado de ESTADO_CONTEXTO_IA.md y responde con base en RAG actual'.",
    ])
    return "\n".join(lines) + "\n"


def update_ai_context_state() -> Dict[str, Any]:
    status = collect_status()

    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)

    JSON_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    DOC_PATH.write_text(_render_markdown(status), encoding="utf-8")

    return status


def main() -> int:
    parser = argparse.ArgumentParser(description="NEXO - Seguimiento activo de contexto IA")
    parser.add_argument("--watch", action="store_true", help="Ejecuta en modo continuo")
    parser.add_argument("--interval", type=int, default=180, help="Intervalo segundos en modo watch")
    args = parser.parse_args()

    if not args.watch:
        status = update_ai_context_state()
        log.info("Contexto IA actualizado | rag_loaded=%s | total_docs=%s", (status.get("rag") or {}).get("rag_loaded"), (status.get("rag") or {}).get("total_documentos"))
        return 0

    interval = max(30, int(args.interval))
    log.info("Iniciando seguimiento IA activo cada %ss", interval)
    while True:
        try:
            status = update_ai_context_state()
            log.info("Contexto IA actualizado | rag_loaded=%s | total_docs=%s", (status.get("rag") or {}).get("rag_loaded"), (status.get("rag") or {}).get("total_documentos"))
        except Exception as exc:
            log.error("Error actualizando contexto IA: %s", exc)
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
