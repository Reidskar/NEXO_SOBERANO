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
from urllib.request import urlopen
from urllib.error import URLError
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
        health_urls = [
            f"http://127.0.0.1:{config.PORT}/api/health/",
            f"http://127.0.0.1:{config.PORT}/api/health",
            f"http://127.0.0.1:{config.PORT}/health",
        ]
        for health_url in health_urls:
            try:
                with urlopen(health_url, timeout=3) as response:
                    status = response.status
                    body = response.read().decode("utf-8", errors="ignore")
                    if status == 200:
                        log.info(f"⚠️ Puerto {config.PORT} ya está en uso y {health_url} respondió 200.")
                        log.info("✅ Backend ya operativo; no se inicia una segunda instancia.")
                        sys.exit(0)
                    log.info(f"❌ Puerto {config.PORT} en uso, pero {health_url} devolvió status {status}.")
                    log.info(f"Detalle health: {body[:200]}")
                    sys.exit(1)
            except (URLError, TimeoutError, ConnectionError, OSError):
                continue

        log.info(f"❌ Puerto {config.PORT} en uso, pero no hubo respuesta válida en endpoints de health.")
        log.info("🛠️ Libera el puerto o detén el proceso colgado antes de reiniciar backend.")
        sys.exit(1)
    finally:
        sock.close()

    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        reload=False,  # Desactivado para mejor estabilidad
        log_level="info",
    )
