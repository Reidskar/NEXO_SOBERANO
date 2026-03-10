"""
🚀 INICIO RÁPIDO NEXO
Script de lanzamiento automático del sistema completo
"""
import subprocess
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

def main():
    log.info("=" * 70)
    log.info("  🚀 NEXO SOBERANO - INICIO AUTOMÁTICO")
    log.info("=" * 70)
    print()
    log.info("Iniciando sistema integrado OBS + Discord + Backend...")
    print()
    log.info("Componentes que se iniciarán:")
    log.info("  ✓ OBS Studio (con WebSocket)")
    log.info("  ✓ Backend NEXO (FastAPI)")
    log.info("  ✓ Discord Supervisor (monitoreo automático)")
    print()
    log.info("=" * 70)
    print()
    
    # Ejecutar el orquestador
    orchestrator_path = Path(__file__).parent / "nexo_orchestrator.py"
    python_exe = sys.executable
    
    try:
        subprocess.run([python_exe, str(orchestrator_path)], check=False)
    except KeyboardInterrupt:
        log.info("\n\n✅ Sistema detenido por el usuario")
    except Exception as exc:
        log.info(f"\n❌ Error: {exc}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
