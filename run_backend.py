#!/usr/bin/env python3
"""
🔧 EJECUTAR BACKEND UNIFICADO

Punto de entrada para el backend refactorizado.
Reemplaza completamente a api/main.py (mock antiguo).

USO:
    python -m NEXO_CORE.main
    O
    uvicorn NEXO_CORE.main:app --reload
"""

import sys
import socket
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

# Asegurar imports correctos
root = Path(__file__).parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

if __name__ == "__main__":
    from NEXO_CORE.main import app
    import uvicorn
    from NEXO_CORE import config

    log.info("╔══════════════════════════════════════════════════════════════╗")
    log.info("║  🚀 NEXO CORE v3.0 — BACKEND CONSOLIDADO                    ║")
    log.info("╚══════════════════════════════════════════════════════════════╝")
    log.info(f"\n📍 Escuchando en: http://{config.HOST}:{config.PORT}")
    log.info(f"📚 Documentación API: http://localhost:{config.PORT}/api/docs")
    log.info(f"💰 Presupuesto: {config.MAX_TOKENS_DIA:,} tokens/día")
    log.info(f"🔐 CORS permitido: {config.CORS_ORIGINS}")
    log.info("\n[Ctrl+C para detener]\n")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((config.HOST, config.PORT))
    except OSError:
        log.info(f"⚠️ Puerto {config.PORT} ya está en uso. Backend probablemente ya está en ejecución.")
        log.info("✅ No se inicia una segunda instancia para evitar conflicto.")
        sys.exit(0)
    finally:
        sock.close()

    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        reload=False,  # Desactivado para mejor estabilidad
        log_level="info",
    )
