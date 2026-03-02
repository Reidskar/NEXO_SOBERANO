#!/usr/bin/env python3
"""
NEXO SOBERANO v2.0 — Migration Helper
Herramienta para limpiar estructura vieja y verificar integración.
"""

import os
import shutil
from pathlib import Path

ROOT = Path(__file__).parent

print("""
╔══════════════════════════════════════════════════════════════╗
║    NEXO SOBERANO v2.0 — Herramienta de Migración           ║
╚══════════════════════════════════════════════════════════════╝
""")

# Archivos a limpiar
OBSOLETOS = [
    "motor_ingesta.py",
    "memoria_semantica.py",
    "api_puente.py",
    "arquitecto_v2.py",
    "core/orchestrator.py",
]

# Archivos a mantener
MANTENER = [
    "core/auth_manager.py",
    "core/orquestador.py",
    "services/connectors/google_connector.py",
    "services/connectors/microsoft_connector.py",
]

def main():
    log.info("📊 ANÁLISIS DE MIGRABILIDAD\n")
    
    # Verificar que nexo_v2.py existe
    if not (ROOT / "nexo_v2.py").exists():
        log.info("❌ ERROR: nexo_v2.py no encontrado")
        return
    log.info("✅ nexo_v2.py presente")
    
    # Verificar archivos a mantener
    log.info("\n🔒 Archivos CRÍTICOS (no tocar):")
    for f in MANTENER:
        ruta = ROOT / f
        if ruta.exists():
            size = ruta.stat().st_size / 1024
            log.info(f"  ✅ {f:<45} ({size:.1f} KB)")
        else:
            log.info(f"  ⚠️  {f:<45} (FALTA)")
    
    # Archivos obsoletos
    log.info("\n🗑️  Archivos OBSOLETOS (seguros para borrar):")
    obsoletos_encontrados = []
    for f in OBSOLETOS:
        ruta = ROOT / f
        if ruta.exists():
            size = ruta.stat().st_size / 1024
            obsoletos_encontrados.append(f)
            log.info(f"  ❌ {f:<45} ({size:.1f} KB)")
        else:
            log.info(f"  ℹ️  {f:<45} (ya borrado)")
    
    if not obsoletos_encontrados:
        log.info("\n✅ Sistema ya está limpio. No hay archivos obsoletos.")
        return
    
    # Preguntar si borrar
    log.info(f"\n⚠️  Se encontraron {len(obsoletos_encontrados)} archivo(s) obsoleto(s)")
    log.info("Estos se pueden borrar de forma segura porque nexo_v2.py reemplaza su funcionalidad.\n")
    
    respuesta = input("¿Deseas borrar los archivos obsoletos? (sí/no): ").strip().lower()
    
    if respuesta in ("sí", "si", "yes", "y"):
        log.info("\n🗑️  Borrando...")
        borrados = 0
        for f in obsoletos_encontrados:
            ruta = ROOT / f
            try:
                ruta.unlink()
                log.info(f"  ✅ Borrado: {f}")
                borrados += 1
            except Exception as e:
                log.info(f"  ❌ Error borrando {f}: {e}")
        
        log.info(f"\n✅ {borrados} archivo(s) borrado(s) exitosamente")
        
        # Crear backup reference
        log.info("\n📋 Archivos que fueron reemplazados por nexo_v2.py:")
        log.info("  • motor_ingesta.py      → procesar_archivo()")
        log.info("  • memoria_semantica.py  → get_coleccion()")
        log.info("  • api_puente.py         → crear_app()")
        log.info("  • core/orquestador.py   → Integrado en módules 1-12")
    else:
        log.info("\n❌ Operación cancelada. Los archivos obsoletos siguen presentes.")
        log.info("Puedes borrarlos manualmente cuando estés listo.")
    
    # Verificar setup
    log.info("\n" + "="*60)
    log.info("🚀 PRÓXIMOS PASOS")
    log.info("="*60)
    log.info("\n1. Copiar documentos a: documentos/")
    log.info("2. Ejecutar indexación: python nexo_v2.py setup")
    log.info("3. Iniciar servidor:    python nexo_v2.py run")
    log.info("4. Ir a:                http://localhost:8000")

if __name__ == "__main__":
    main()
