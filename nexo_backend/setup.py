#!/usr/bin/env python3
"""
Quick Setup para Nexo Backend
Instala dependencias, verifica configuración, inicia el sistema.
"""

import os
import sys
import subprocess
import json
from pathlib import Path

COLORS = {
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "RED": "\033[91m",
    "CYAN": "\033[96m",
    "END": "\033[0m"
}

def log(msg, level="INFO"):
    colors = {"INFO": COLORS["CYAN"], "SUCCESS": COLORS["GREEN"], "ERROR": COLORS["RED"], "WARN": COLORS["YELLOW"]}
    log.info(f"{colors.get(level, '')}[{level}]{COLORS['END']} {msg}")

def check_python():
    log("Verificando Python...", "INFO")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        log(f"Python {version.major}.{version.minor}.{version.micro} ✓", "SUCCESS")
        return True
    log("Python 3.8+ requerido", "ERROR")
    return False

def install_requirements():
    log("Instalando dependencias...", "INFO")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True, capture_output=True)
        log("Dependencias instaladas ✓", "SUCCESS")
        return True
    except Exception as e:
        log(f"Error: {e}", "ERROR")
        return False

def check_env_vars():
    log("Verificando variables de entorno...", "INFO")
    vars_needed = {
        "OPENAI_API_KEY": "OpenAI API Key (Copilot)",
        "GEMINI_API_KEY": "Google Gemini API Key",
    }
    
    missing = []
    for var, desc in vars_needed.items():
        if os.getenv(var):
            log(f"  ✓ {var}", "SUCCESS")
        else:
            log(f"  ✗ {var} (ausente)", "WARN")
            missing.append((var, desc))
    
    if missing:
        log("\nConfigura estas variables de entorno:", "WARN")
        for var, desc in missing:
            log.info(f"  export {var}='tu_clave_aqui'  # {desc}")
        return False
    return True

def check_ports():
    log("Verificando puertos disponibles...", "INFO")
    import socket
    
    ports = {8000: "Backend", 8080: "Frontend"}
    for port, name in ports.items():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("127.0.0.1", port))
            s.close()
            log(f"  ✓ Puerto {port} ({name}) disponible", "SUCCESS")
        except OSError:
            log(f"  ✗ Puerto {port} ({name}) en uso", "ERROR")
            return False
    return True

def create_config():
    log("Creando archivo de configuración...", "INFO")
    config = {
        "backend": {
            "host": "0.0.0.0",
            "port": 8000,
            "reload": True
        },
        "frontend": {
            "port": 8080
        },
        "ai": {
            "default_provider": "auto",
            "openai_model": "gpt-4",
            "gemini_model": "gemini-pro"
        }
    }
    
    config_path = Path("config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    log(f"  ✓ Configuración guardada en {config_path}", "SUCCESS")
    return config

def show_instructions():
    log("\n" + "="*60, "INFO")
    log("CONFIGURACION COMPLETADA ✓", "SUCCESS")
    log("="*60 + "\n", "INFO")
    
    print("""
┌─ PRÓXIMOS PASOS ─────────────────────────────────────┐
│                                                       │
│ 1. Terminal 1 - Backend:                            │
│    cd nexo_backend                                   │
│    uvicorn main:app --reload                         │
│                                                       │
│ 2. Terminal 2 - Frontend:                           │
│    cd obs_control                                    │
│    python -m http.server 8080                        │
│                                                       │
│ 3. Abrir en navegador:                              │
│    http://localhost:8080/chat.html                    │
│                                                       │
│ ⚙️  IMPORTANTE - Variables de entorno:              │
│    Asegúrate de tener OPENAI_API_KEY y GEMINI_API_KEY
│    configuradas ANTES de iniciar.                    │
│                                                       │
└───────────────────────────────────────────────────────┘
""")
    
    log("Documentación: OPERATION_GUIDE.md", "INFO")

def main():
    log("╔═════════════════════════════════════════╗", "CYAN")
    log("║  NEXO SOBERANO - Setup Asistido        ║", "CYAN")
    log("╚═════════════════════════════════════════╝\n", "CYAN")
    
    steps = [
        ("Python", check_python),
        ("Puertos", check_ports),
        ("Variables de entorno", check_env_vars),
        ("Requisitos", install_requirements),
    ]
    
    for name, check_fn in steps:
        if not check_fn():
            log(f"\n⚠️  Detén y soluciona el problema de {name}", "ERROR")
            if name != "Variables de entorno":  # este es opcional
                sys.exit(1)
    
    create_config()
    show_instructions()

if __name__ == "__main__":
    main()
