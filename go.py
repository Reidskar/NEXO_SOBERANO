#!/usr/bin/env python
"""
🚀 NEXO SOBERANO - LAUNCH SEQUENCE
Ejecuta esta orden para arrancar el sistema completo.
"""
import os
import sys

# Asegurar que podemos importar desde la raíz
ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

def check_requirements():
    """Verify all key files exist or are in acceptable state."""
    log.info("\n" + "="*70)
    log.info("🔍 NEXO SOBERANO - VERIFICACIÓN PRE-VUELO")
    log.info("="*70 + "\n")
    
    checks = {
        ".venv": "Entorno Virtual",
        "core/orquestador.py": "Orquestador Central",
        "core/auth_manager.py": "Gestor de Autenticación",
        "services/connectors/google_connector.py": "Conector Google",
        "services/connectors/microsoft_connector.py": "Conector Microsoft",
        "api_puente.py": "Puente API",
        "memoria_semantica.py": "Motor Vectorial",
        "motor_ingesta.py": "Motor de Ingesta",
    }
    
    all_ok = True
    for filepath, label in checks.items():
        exists = os.path.exists(filepath)
        status = "✅" if exists else "⚠️"
        log.info(f"{status} {label:30} ({filepath})")
        if not exists and "conector" not in label.lower():
            all_ok = False
    
    log.info("\n" + "="*70)
    
    # Check for credentials
    has_google_creds = os.path.exists("credenciales_google.json")
    if not has_google_creds:
        log.info("\n⚠️  SIN CREDENCIALES GOOGLE")
        log.info("   El sistema arrancará en MODO DEMO.")
        log.info("   Para conectar tu Google Drive, ejecuta primero:")
        log.info("   > python setup_credentials.py\n")
    else:
        log.info("\n✅ Credenciales Google disponibles\n")
    
    return all_ok

def main():
    """Launch the orchestrator."""
    if not check_requirements():
        log.info("❌ PREFLIGHT CHECK FALLÓ")
        return 1
    
    log.info("🤖 Iniciando NEXO SOBERANO...\n")
    
    # Import and run orchestrator
    from core.orquestador import OrquestadorCentral
    
    log.info("="*70)
    try:
        jarvis = OrquestadorCentral()
        log.info("\n🤖 JARVIS: Orquestador Central en línea. Esperando órdenes, Director.\n")
        
        # Sincronizar conectores
        log.info("📡 Iniciando sincronización con servicios cloud...\n")
        jarvis.sincronizar_conectores()
        
        log.info("\n" + "="*70)
        log.info("✅ NEXO SOBERANO ACTIVO")
        log.info("="*70)
        log.info("\n📊 Estado actual:")
        log.info(f"   Presupuesto de tokens hoy: {jarvis.finanzas.presupuesto_diario}")
        log.info(f"   Tokens consumidos: {jarvis.finanzas.tokens_usados_hoy}")
        log.info(f"   Saldo disponible: {jarvis.finanzas.presupuesto_diario - jarvis.finanzas.tokens_usados_hoy}")
        log.info("\n💡 Próximos pasos:")
        log.info("   1. Los archivos se procesan automáticamente")
        log.info("   2. El API Puente está disponible en http://127.0.0.1:8000/docs")
        log.info("   3. Monitora la bitácora en NEXO_SOBERANO/bitacora/")
        log.info("\n")
        
        return 0
        
    except Exception as e:
        log.info(f"\n❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
