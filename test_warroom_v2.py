#!/usr/bin/env python3
"""
Script de prueba completo para War Room v2
Verifica que todos los endpoints y servicios funcionen correctamente
"""

import requests
import json
import sys
import time
from pathlib import Path

# ════════════════════════════════════════════════════════════════════
# COLOREO DE SALIDA
# ════════════════════════════════════════════════════════════════════

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def print_ok(msg):
    log.info(f"{GREEN}✓ {msg}{RESET}")

def print_err(msg):
    log.info(f"{RED}✗ {msg}{RESET}")

def print_warn(msg):
    log.info(f"{YELLOW}⚠ {msg}{RESET}")

def print_info(msg):
    log.info(f"{BLUE}ℹ {msg}{RESET}")

# ════════════════════════════════════════════════════════════════════
# TESTING
# ════════════════════════════════════════════════════════════════════

API_BASE = "http://localhost:8000"

def test_health():
    """Prueba que el backend está arriba"""
    print_info("Probando /agente/health...")
    try:
        resp = requests.get(f"{API_BASE}/agente/health", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            print_ok(f"Backend UP | Status: {data.get('status', 'ok')}")
            print_info(f"  └─ RAG loaded: {data.get('rag_loaded')}")
            print_info(f"  └─ Documentos indexados: {data.get('total_documentos')}")
            presupuesto = data.get('presupuesto', {})
            print_info(f"  └─ Presupuesto: {presupuesto.get('tokens_usados_hoy', 0)} / {presupuesto.get('limite_diario', 0)} tokens")
            return True
        else:
            print_err(f"Health check falló: {resp.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_err(f"No se puede conectar a {API_BASE}")
        print_warn("¿Está ejecutándose 'python run_backend.py'?")
        return False
    except Exception as e:
        print_err(f"Error en health check: {e}")
        return False

def test_consultar():
    """Prueba consulta RAG"""
    print_info("Probando POST /agente/consultar...")
    try:
        payload = {
            "query": "¿Qué es NEXO SOBERANO?",
            "mode": "normal",
            "categoria": None
        }
        resp = requests.post(
            f"{API_BASE}/agente/consultar",
            json=payload,
            timeout=15
        )
        
        if resp.status_code == 200:
            data = resp.json()
            print_ok("Consulta procesada")
            print_info(f"  └─ Respuesta: {data.get('answer', '')[:80]}...")
            print_info(f"  └─ Fuentes: {len(data.get('sources', []))} encontradas")
            print_info(f"  └─ Tiempo: {data.get('execution_time_ms', '?')}ms")
            print_info(f"  └─ Tokens: {data.get('tokens_used', 0)}")
            return True
        else:
            print_err(f"Consulta falló: {resp.status_code} - {resp.text[:100]}")
            return False
    except requests.exceptions.Timeout:
        print_warn("Consulta tarda mucho (timeout). Bóveda podría estar vacía.")
        return None  # No es error crítico
    except Exception as e:
        print_err(f"Error en consulta: {e}")
        return False

def test_presupuesto():
    """Prueba endpoint de presupuesto"""
    print_info("Probando GET /agente/presupuesto...")
    try:
        resp = requests.get(f"{API_BASE}/agente/presupuesto", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            print_ok("Presupuesto obtenido")
            print_info(f"  └─ Tokens hoy: {data.get('tokens_usados_hoy', 0)}")
            print_info(f"  └─ Máximo: {data.get('limite_diario', 0)}")
            print_info(f"  └─ Disponible: {data.get('disponible', 0)}")
            return True
        else:
            print_err(f"Presupuesto falló: {resp.status_code}")
            return False
    except Exception as e:
        print_err(f"Error obteniendo presupuesto: {e}")
        return False

def test_drive():
    """Prueba Google Drive connector"""
    print_info("Probando GET /agente/drive/recent...")
    try:
        resp = requests.get(f"{API_BASE}/agente/drive/recent", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if "error" in data and data["error"]:
                print_warn(f"Google Drive no autorizado: {data['error']}")
                print_warn("  └─ Usa la pestaña 'Setup' en warroom_v2.html para autorizar")
                return None  # Warning, no error
            else:
                files = data.get('files', [])
                print_ok(f"Drive connector OK - {len(files)} archivos")
                if files:
                    print_info(f"  └─ Recientes: {', '.join([f['name'] for f in files[:3]])}")
                return True
        else:
            print_err(f"Drive falló: {resp.status_code}")
            return False
    except Exception as e:
        print_warn(f"Google Drive no disponible: {e}")
        return None

def test_historial_costos():
    """Prueba historial de costos"""
    print_info("Probando GET /agente/historial-costos...")
    try:
        resp = requests.get(f"{API_BASE}/agente/historial-costos", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            historial = data.get('historial', {})
            print_ok(f"Historial de costos: {len(historial)} días registrados")
            return True
        else:
            print_err(f"Historial falló: {resp.status_code}")
            return False
    except Exception as e:
        print_warn(f"Historial no disponible: {e}")
        return None

def test_database():
    """Verifica que la base de datos exista y tenga tablas"""
    print_info("Verificando base de datos...")
    try:
        import sqlite3
        db_path = Path(__file__).parent / "NEXO_SOBERANO" / "base_sqlite" / "boveda.db"
        
        if not db_path.exists():
            print_warn(f"Base de datos no existe en {db_path}")
            return None
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Verificar tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tablas = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        print_ok(f"Base de datos OK - {len(tablas)} tablas")
        print_info(f"  └─ Tablas: {', '.join(tablas)}")
        
        if 'evidencia' not in tablas:
            print_warn("Falta tabla 'evidencia' - ejecuta: python nexo_v2.py setup")
            return False
        
        if 'consultas' not in tablas:
            print_warn("Falta tabla 'consultas' - será creada automáticamente")
        
        return True
    except Exception as e:
        print_err(f"Error verificando BD: {e}")
        return False

def test_warroom_file():
    """Verifica que warroom_v2.html exista"""
    print_info("Verificando archivos...")
    try:
        warroom = Path(__file__).parent / "warroom_v2.html"
        if warroom.exists():
            size = warroom.stat().st_size
            print_ok(f"warroom_v2.html existe ({size / 1024:.1f} KB)")
            return True
        else:
            print_err(f"warroom_v2.html no encontrado en {warroom}")
            return False
    except Exception as e:
        print_err(f"Error verificando archivos: {e}")
        return False

# ════════════════════════════════════════════════════════════════════
# EJECUCIÓN
# ════════════════════════════════════════════════════════════════════

def main():
    log.info(f"\n{BLUE}{'='*60}")
    log.info(f"NEXO SOBERANO — War Room v2 — Test Suite")
    log.info(f"{'='*60}{RESET}\n")
    
    resultados = {}
    
    # Test 1: Archivo
    resultados['warroom_file'] = test_warroom_file()
    print()
    
    # Test 2: Base de datos
    resultados['database'] = test_database()
    print()
    
    # Test 3: Health
    health_ok = test_health()
    resultados['health'] = health_ok
    print()
    
    if not health_ok:
        print_err("Backend no está corriendo. Inicia con: python run_backend.py")
        return 1
    
    # Test 4: Presupuesto
    resultados['presupuesto'] = test_presupuesto()
    print()
    
    # Test 5: Historial de costos
    resultados['historial'] = test_historial_costos()
    print()
    
    # Test 6: Consultar (puede fallar si bóveda vacía - no es crítico)
    resultados['consultar'] = test_consultar()
    print()
    
    # Test 7: Google Drive (opcional)
    resultados['drive'] = test_drive()
    print()
    
    # Resumen
    log.info(f"\n{BLUE}{'='*60}")
    log.info("RESUMEN")
    log.info(f"{'='*60}{RESET}")
    
    críticos = {k: v for k, v in resultados.items() if k in ['health', 'database']}
    opcionales = {k: v for k, v in resultados.items() if k in ['drive', 'consultar']}
    normales = {k: v for k, v in resultados.items() if k not in críticos and k not in opcionales}
    
    ok = sum(1 for v in críticos.values() if v is True)
    total_criticos = len([v for v in críticos.values() if v is not None])
    
    for k, v in normales.items():
        estado = "✓" if v is True else ("⚠" if v is None else "✗")
        log.info(f"  {estado} {k}")
    
    for k, v in críticos.items():
        estado = "✓" if v is True else ("⚠" if v is None else "✗")
        log.info(f"  {estado} {k}")
    
    for k, v in opcionales.items():
        estado = "✓" if v is True else ("⚠" if v is None else "✗")
        log.info(f"  {estado} {k} (opcional)")
    
    print()
    
    if ok == total_criticos:
        print_ok("Todos los servicios críticos están OK")
        log.info(f"\n{BLUE}Próximos pasos:{RESET}")
        log.info(f"  1. Abre warroom_v2.html en tu navegador")
        log.info(f"  2. Usa la pestaña 'Chat' para hacer preguntas")
        log.info(f"  3. Usa 'Setup' para autorizar Google Drive (opcional)")
        return 0
    else:
        print_err(f"Faltan {total_criticos - ok} servicios críticos")
        return 1

if __name__ == "__main__":
    sys.exit(main())
