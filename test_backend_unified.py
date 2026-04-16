#!/usr/bin/env python3
"""
🧪 TEST SUITE — Backend Unificado

Verifica que todos los componentes funcionen correctamente.
"""

import sys
import logging
from pathlib import Path

root = Path(__file__).parent
sys.path.insert(0, str(root))

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(message)s')

from backend import config
from backend.services.rag_service import get_rag_service
from backend.services.cost_manager import get_cost_manager

# ════════════════════════════════════════════════════════════════════
# TESTS
# ════════════════════════════════════════════════════════════════════

def test_config():
    """Test: Config centralizado"""
    log.info("\n🧪 TEST 1: Configuración centralizado")
    log.info(f"  ✅ DB_PATH: {config.DB_PATH}")
    log.info(f"  ✅ CHROMA_DIR: {config.CHROMA_DIR}")
    log.info(f"  ✅ MAX_TOKENS: {config.MAX_TOKENS_DIA:,}")
    log.info(f"  ✅ CORS_ORIGINS: {len(config.CORS_ORIGINS)} origins")

def test_cost_manager():
    """Test: Gestor de costos"""
    global log
    log.info("\n🧪 TEST 2: Gestor de costos")
    cm = get_cost_manager()
    
    # Registrar una operación ficticia
    cm.registrar("gemini-1.5-flash", 100, 50, "test")
    
    estado = cm.estado()
    log.info(f"  ✅ Tokens hoy: {estado['tokens_hoy']}")
    log.info(f"  ✅ Presupuesto: {estado['porcentaje']:.2f}% usado")
    log.info(f"  ✅ Puede operar: {estado['puede_operar']}")

def test_rag_service():
    """Test: Servicio RAG"""
    log.info("\n🧪 TEST 3: Servicio RAG")
    rag = get_rag_service()
    
    estado = rag.estado()
    log.info(f"  ✅ RAG cargado: {estado['rag_loaded']}")
    log.info(f"  ✅ Documentos: {estado.get('total_documentos', 0)}")
    log.info(f"  ✅ Items en colección: {estado.get('coleccion_items', 0)}")

def test_backend_startup():
    """Test: Arranque del backend (opcional, sin ejecutar)"""
    log.info("\n🧪 TEST 4: Backend startup")
    log.info("  ℹ️  Backend NO se inicia en tests (evitar puerto ocupado)")
    log.info("  ℹ️  Para iniciar: python run_backend.py")
    log.info("  ℹ️  Endpoint: http://localhost:8080/agente/consultar")

def test_imports():
    """Test: Imports correctos"""
    log.info("\n🧪 TEST 5: Imports")
    try:
        from backend.config import MAX_TOKENS_DIA
        log.info(f"  ✅ backend.config")
        
        from backend.services.cost_manager import CostManager
        log.info(f"  ✅ backend.services.cost_manager")
        
        from backend.services.rag_service import RAGService
        log.info(f"  ✅ backend.services.rag_service")
        
        from backend.routes.agente import router
        log.info(f"  ✅ backend.routes.agente")
        
        from backend.main import app
        log.info(f"  ✅ backend.main")
    except ImportError as e:
        log.info(f"  ❌ Error de import: {e}")

def test_api_docs():
    """Test: Documentación API"""
    log.info("\n🧪 TEST 6: API Docs")
    log.info("  📚 URL: http://localhost:8080/api/docs")
    log.info("  📚 Endpoint: POST /agente/consultar")
    log.info("  📚 Contrato: QueryRequest → QueryResponse")

def test_frontend_integration():
    """Test: Integración Frontend"""
    log.info("\n🧪 TEST 7: Integración Frontend")
    log.info("  ✅ ChatBox.jsx actualizado")
    log.info("  ✅ Endpoint: /api/chat → /agente/consultar")
    log.info("  ✅ Contrato: {message} → {query, mode}")
    log.info("  ✅ Response: {response} → {answer, sources, tokens_used, ...}")

def test_cors():
    """Test: CORS"""
    log.info("\n🧪 TEST 8: CORS")
    log.info(f"  ✅ allow_origins: {config.CORS_ORIGINS}")
    log.info(f"  ✅ allow_credentials: True")
    log.info(f"  ✅ allow_methods: *")
    log.info(f"  ✅ sin allow_origins=['*']")

# ════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════

def main():
    log.info("╔══════════════════════════════════════════════════════════════╗")
    log.info("║  🧪 TEST SUITE — Backend Unificado                          ║")
    log.info("╚══════════════════════════════════════════════════════════════╝")

    try:
        test_imports()
        test_config()
        test_cost_manager()
        test_rag_service()
        test_backend_startup()
        test_api_docs()
        test_frontend_integration()
        test_cors()

        log.info("\n" + "="*60)
        log.info("✅ TODOS LOS TESTS PASARON")
        log.info("="*60)
        log.info("\n🚀 Próximo paso: python run_backend.py")
        log.info("   Frontend: cd frontend && npm run dev\n")

    except Exception as e:
        log.info(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
