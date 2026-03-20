# ============================================================
# NEXO SOBERANO — Inter-Agent Bus Garbage Collector
# © 2026 elanarcocapital.com
# Limpia mensajes leídos o viejos del bus cada 24h
# ============================================================
from __future__ import annotations
import json
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Tuple

logger = logging.getLogger("NEXO.inter_agent_bus.gc")

MESSAGES_DIR = Path("inter_agent/mensajes")
ARCHIVE_DIR  = Path("inter_agent/archivo")
MAX_AGE_HOURS = 48

def run_gc() -> Tuple[int, int]:
    """
    Limpia mensajes leídos o con más de 48h.
    Mueve a archivo/ los críticos antes de borrar.
    
    Returns:
        (eliminados, archivados)
    """
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    eliminados = archivados = 0
    ahora = datetime.now()

    for f in MESSAGES_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            ts = datetime.fromisoformat(
                data.get("timestamp", ahora.isoformat())
            )
            edad_horas = (ahora - ts).total_seconds() / 3600
            es_viejo = edad_horas > MAX_AGE_HOURS
            es_leido = data.get("leido", False)

            if es_viejo or es_leido:
                # Archivar si es crítico antes de borrar
                if data.get("urgencia") == "critical":
                    shutil.copy2(f, ARCHIVE_DIR / f.name)
                    archivados += 1
                f.unlink()
                eliminados += 1

        except Exception as e:
            logger.error(f"GC error en {f.name}: {e}")

    logger.info(
        f"Bus GC completado: {eliminados} eliminados, "
        f"{archivados} archivados"
    )
    return eliminados, archivados


if __name__ == "__main__":
    e, a = run_gc()
    print(f"[OK] GC: {e} eliminados, {a} archivados")
