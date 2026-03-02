#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NEXO SOBERANO - Arranque maestro

Uso:
  python nexo_start.py              # setup + diagnóstico + run
  python nexo_start.py --check      # solo diagnóstico
  python nexo_start.py --run        # solo run
  python nexo_start.py --install    # instalar requirements
  python nexo_start.py --setup      # indexar con nexo_v2.py setup
  python nexo_start.py --reset      # borrar índice y re-indexar
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _print(msg: str) -> None:
    log.info(msg)


def check_python() -> None:
    if sys.version_info < (3, 10):
        raise SystemExit("Python 3.10+ requerido")
    _print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")


def setup_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        env_path.write_text(
            "GEMINI_API_KEY=PEGA-AQUI-TU-KEY\n"
            "HOST=0.0.0.0\n"
            "PORT=8000\n"
            "LOG_LEVEL=INFO\n"
            "GOOGLE_CLIENT_ID=\n"
            "GOOGLE_CLIENT_SECRET=\n"
            "DRIVE_CLIENT_ID=\n"
            "DRIVE_CLIENT_SECRET=\n"
            "YOUTUBE_CLIENT_ID=\n"
            "YOUTUBE_CLIENT_SECRET=\n"
            "MICROSOFT_CLIENT_ID=\n"
            "MICROSOFT_CLIENT_SECRET=\n"
            "MICROSOFT_TENANT_ID=\n",
            encoding="utf-8",
        )
        raise SystemExit("Se creó .env. Configura GEMINI_API_KEY y vuelve a ejecutar.")

    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())

    key = os.environ.get("GEMINI_API_KEY", "")
    if not key or "PEGA-AQUI" in key:
        raise SystemExit("GEMINI_API_KEY no configurada en .env")

    _print("✓ .env cargado")


def create_dirs() -> None:
    dirs = [
        "documentos",
        "frontend_public",
        "logs",
        "backend/auth",
        "backend/routes",
        "backend/services",
        "scripts",
        "workers",
        "NEXO_SOBERANO/memoria_vectorial",
        "NEXO_SOBERANO/base_sqlite",
    ]
    for d in dirs:
        (ROOT / d).mkdir(parents=True, exist_ok=True)
    _print(f"✓ {len(dirs)} carpetas verificadas")


def install_deps() -> None:
    req = ROOT / "requirements.txt"
    if not req.exists():
        _print("⚠ requirements.txt no encontrado, se omite instalación")
        return
    _print("→ Instalando requirements...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req)], cwd=str(ROOT), check=False)


def check_nexo_v2() -> bool:
    exists = (ROOT / "nexo_v2.py").exists()
    if exists:
        _print("✓ nexo_v2.py presente")
    else:
        _print("⚠ nexo_v2.py no encontrado (RAG puede degradarse)")
    return exists


def maybe_reindex(force_reset: bool = False, force_setup: bool = False) -> None:
    chroma = ROOT / "NEXO_SOBERANO" / "memoria_vectorial"
    if force_reset and chroma.exists():
        shutil.rmtree(chroma)
        chroma.mkdir(parents=True, exist_ok=True)
        _print("✓ índice ChromaDB reiniciado")

    if not force_setup:
        return

    nexo = ROOT / "nexo_v2.py"
    if not nexo.exists():
        _print("⚠ no se indexa porque falta nexo_v2.py")
        return

    _print("→ Ejecutando indexado: python nexo_v2.py setup")
    subprocess.run([sys.executable, str(nexo), "setup"], cwd=str(ROOT), check=False)


def diagnostico() -> bool:
    checks = [
        ("backend/main.py", (ROOT / "backend" / "main.py").exists(), True),
        ("backend/config.py", (ROOT / "backend" / "config.py").exists(), True),
        ("backend/routes/agente.py", (ROOT / "backend" / "routes" / "agente.py").exists(), True),
        ("backend/services/rag_service.py", (ROOT / "backend" / "services" / "rag_service.py").exists(), True),
        ("run_backend.py", (ROOT / "run_backend.py").exists(), True),
        ("warroom_v2.html", (ROOT / "warroom_v2.html").exists(), False),
        ("frontend_public/control_center.html", (ROOT / "frontend_public" / "control_center.html").exists(), False),
    ]
    ok = True
    for name, present, critical in checks:
        if present:
            _print(f"✓ {name}")
        else:
            prefix = "✗" if critical else "⚠"
            _print(f"{prefix} {name}")
            if critical:
                ok = False
    return ok


def run_server() -> None:
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))

    def _open() -> None:
        time.sleep(2)
        webbrowser.open(f"http://localhost:{port}/control-center")

    threading.Thread(target=_open, daemon=True).start()

    _print("\nNEXO levantando...")
    _print(f"- Control Center: http://localhost:{port}/control-center")
    _print(f"- Warroom:        http://localhost:{port}/warroom_v2.html")
    _print(f"- Admin:          http://localhost:{port}/admin_dashboard.html")
    _print(f"- API Docs:       http://localhost:{port}/api/docs")
    _print("\nCtrl+C para detener\n")

    subprocess.run([sys.executable, str(ROOT / "run_backend.py")], cwd=str(ROOT), check=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="NEXO SOBERANO arranque maestro")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--setup", action="store_true")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    check_python()
    setup_env()

    if args.install:
        install_deps()
        return 0

    if args.check:
        return 0 if diagnostico() else 1

    if args.run:
        if not diagnostico():
            return 1
        run_server()
        return 0

    create_dirs()
    install_deps()
    check_nexo_v2()
    maybe_reindex(force_reset=args.reset, force_setup=args.setup)

    if not diagnostico():
        return 1

    run_server()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
