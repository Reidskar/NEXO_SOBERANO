#!/usr/bin/env python3
"""
NEXO SOBERANO - Diagnóstico Completo del Sistema
Genera un reporte detallado del estado arquitectónico
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent

def check_file_exists(path):
    """Verifica si un archivo existe"""
    return "✅" if Path(path).exists() else "❌"

def get_file_size(path):
    """Obtiene el tamaño de un archivo en KB"""
    if Path(path).exists():
        return f"{Path(path).stat().st_size / 1024:.1f} KB"
    return "N/A"

def count_lines(filepath):
    """Cuenta líneas de código"""
    if not Path(filepath).exists():
        return 0
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return len(f.readlines())
    except:
        return 0

print("""
╔══════════════════════════════════════════════════════════════╗
║          NEXO SOBERANO - DIAGNÓSTICO DEL SISTEMA            ║
╚══════════════════════════════════════════════════════════════╝
""")

log.info(f"📅 Timestamp: {datetime.now().isoformat()}")
log.info(f"📍 Workspace: {ROOT}")
log.info(f"🐍 Python: {sys.version.split()[0]}")
print()

# ========== BACKEND MODULES ==========
log.info("=" * 60)
log.info("MÓDULOS BACKEND (Python)")
log.info("=" * 60)

backend_modules = {
    "Core - Orquestador": ("core/orquestador.py", "Orchestración central + Gestión de costos"),
    "Core - Auth Manager": ("core/auth_manager.py", "OAuth2 (Google + Microsoft)"),
    "Services - Google Connector": ("services/connectors/google_connector.py", "Google Drive + Photos"),
    "Services - Microsoft Connector": ("services/connectors/microsoft_connector.py", "OneDrive + Graph API"),
    "API - FastAPI Main": ("api/main.py", "Servidor REST con endpoints RAG"),
    "Motor de Ingesta": ("motor_ingesta.py", "Escaneo de documentos + análisis"),
    "Memoria Semántica": ("memoria_semantica.py", "Vectorización ChromaDB"),
}

for name, (filepath, description) in backend_modules.items():
    status = check_file_exists(filepath)
    if Path(filepath).exists():
        lines = count_lines(filepath)
        size = get_file_size(filepath)
        log.info(f"{status} {name:<30} | {lines:>5} líneas | {size:>10} | {description}")
    else:
        log.info(f"{status} {name:<30} | ---  líneas | N/A        | {description}")

# ========== FRONTEND COMPONENTS ==========
log.info("\n" + "=" * 60)
log.info("COMPONENTES FRONTEND (React)")
log.info("=" * 60)

frontend_components = {
    "App (Root)": "frontend/src/App.jsx",
    "Header (Status)": "frontend/src/components/Header.jsx",
    "Sidebar (Nav)": "frontend/src/components/Sidebar.jsx", 
    "ChatBox (Input)": "frontend/src/components/ChatBox.jsx",
    "Dashboard (Stats)": "frontend/src/pages/Dashboard.jsx",
}

for name, filepath in frontend_components.items():
    status = check_file_exists(filepath)
    if Path(filepath).exists():
        lines = count_lines(filepath)
        size = get_file_size(filepath)
        log.info(f"{status} {name:<25} | {lines:>5} líneas | {size:>10}")
    else:
        log.info(f"{status} {name:<25} | ---  líneas | N/A")

frontend_config = {
    "package.json": "frontend/package.json",
    "vite.config.js": "frontend/vite.config.js",
    "tailwind.config.js": "frontend/tailwind.config.js",
}

log.info("\n  Config Files:")
for name, filepath in frontend_config.items():
    status = check_file_exists(filepath)
    log.info(f"  {status} {name:<20}")

# ========== DATABASE ==========
log.info("\n" + "=" * 60)
log.info("BASE DE DATOS")
log.info("=" * 60)

db_path = ROOT / "base_sqlite" / "boveda.db"
if db_path.exists():
    size = get_file_size(db_path)
    log.info(f"✅ SQLite Vault")
    log.info(f"   Ubicación: {db_path}")
    log.info(f"   Tamaño: {size}")
    log.info(f"   Tablas: evidencia, vectorizados_log (+ ChromaDB)")
else:
    log.info(f"❌ SQLite Vault - No existe")

# ========== ENVIRONMENT ==========
log.info("\n" + "=" * 60)
log.info("CONFIGURACIÓN")
log.info("=" * 60)

env_files = {
    ".env": ".env",
    "requirements.txt": "requirements.txt",
    "SETUP.md": "SETUP.md",
    "STATUS.md": "STATUS.md",
    "go.py (Launcher)": "go.py",
    "setup_credentials.py": "setup_credentials.py",
}

for name, filepath in env_files.items():
    status = check_file_exists(filepath)
    log.info(f"{status} {name:<25}")

# ========== VIRTUAL ENVIRONMENT ==========
log.info("\n" + "=" * 60)
log.info("VIRTUAL ENVIRONMENT")
log.info("=" * 60)

venv_path = ROOT / ".venv" / "Scripts" / "python.exe"
if venv_path.exists():
    log.info(f"✅ Virtual Environment Activo")
    log.info(f"   Python: {venv_path}")
    try:
        import subprocess
        result = subprocess.run(
            [str(venv_path), "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        log.info(f"   {result.stdout.strip()}")
    except:
        pass
else:
    log.info(f"❌ Virtual Environment - No encontrado")

# ========== API ENDPOINTS ==========
log.info("\n" + "=" * 60)
log.info("API ENDPOINTS (FastAPI)")
log.info("=" * 60)

endpoints = [
    ("GET", "/", "Root info"),
    ("GET", "/docs", "Swagger UI"),
    ("GET", "/openapi.json", "OpenAPI schema"),
    ("GET", "/api/health", "Health check status"),
    ("GET", "/api/status", "System status (connectors)"),
    ("POST", "/api/chat", "Chat RAG endpoint"),
    ("GET", "/api/chat/history", "Chat history"),
]

for method, path, desc in endpoints:
    log.info(f"  {method:<6} {path:<20} → {desc}")

# ========== CARGA DE MÓDULOS CRÍTICOS ==========
log.info("\n" + "=" * 60)
log.info("VERIFICACIÓN DE IMPORTS CRÍTICOS")
log.info("=" * 60)

critical_imports = {
    "FastAPI": "fastapi",
    "ChromaDB": "chromadb",
    "sentence-transformers": "sentence_transformers",
    "Google Generative AI": "google.generativeai",
    "google-api-python-client": "googleapiclient",
    "requests": "requests",
}

for lib_name, import_name in critical_imports.items():
    try:
        __import__(import_name)
        log.info(f"✅ {lib_name:<30} importable")
    except ImportError:
        log.info(f"❌ {lib_name:<30} NO DISPONIBLE")

# ========== ESTADÍSTICAS ==========
log.info("\n" + "=" * 60)
log.info("ESTADÍSTICAS")
log.info("=" * 60)

total_py_files = len(list(ROOT.glob("**/*.py")))
total_lines = sum(count_lines(str(f)) for f in ROOT.glob("**/*.py"))
total_react_files = len(list(ROOT.glob("frontend/src/**/*.jsx")))

log.info(f"📁 Archivos Python: {total_py_files}")
log.info(f"📝 Líneas de código Python: {total_lines:,}")
log.info(f"⚛️  Componentes React: {total_react_files}")
log.info(f"💾 Espacio total workspace: {sum(f.stat().st_size for f in ROOT.rglob('*') if f.is_file()) / 1024 / 1024:.1f} MB")

# ========== ROADMAP ==========
log.info("\n" + "=" * 60)
log.info("ROADMAP - PRÓXIMAS FASES")
log.info("=" * 60)

roadmap = [
    ("✅", "COMPLETA", "Backend APIoperacional + ChromaDB + Authenticación"),
    ("✅", "COMPLETA", "Motor de ingenta + Memoria semántica"),
    ("✅", "COMPLETA", "Orquestador con gestión de costos"),
    ("✅", "COMPLETA", "Conectores modulares (Google + Microsoft)"),
    ("✅", "COMPLETA", "Componentes React scaffolding"),
    ("⏳", "EN PROGRESO", "Instalar Node.js + npm install frontend"),
    ("⏳", "EN PROGRESO", "Frontend dev server (http://localhost:3000)"),
    ("🔄", "PENDIENTE", "Obtener credenciales Google/Microsoft"),
    ("🔄", "PENDIENTE", "Discord connector implementation"),
    ("🔄", "PENDIENTE", "YouTube API integration"),
    ("🔄", "PENDIENTE", "Production deployment (Vercel)"),
]

for status, phase, description in roadmap:
    log.info(f"{status} {phase:<15} → {description}")

# ========== COMANDOS ÚTILES ==========
log.info("\n" + "=" * 60)
log.info("COMANDOS ÚTILES")
log.info("=" * 60)

commands = [
    {
        "descripción": "Revisar estado del API",
        "comando": "python test_api.py"
    },
    {
        "descripción": "Iniciar backend (si stopped)",
        "comando": ".venv\\Scripts\\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000"
    },
    {
        "descripción": "Instalar dependencias frontend",
        "comando": "cd frontend && npm install && npm run dev"
    },
    {
        "descripción": "Setup cloud credentials",
        "comando": "python setup_credentials.py"
    },
]

for i, cmd in enumerate(commands, 1):
    log.info(f"\n{i}. {cmd['descripción']}")
    log.info(f"   $ {cmd['comando']}")

log.info("\n" + "=" * 60)
log.info("✨ SISTEMA LISTO PARA FASE 2: FRONTEND + CLOUD CONNECTORS")
log.info("=" * 60)
print()
