import os
import subprocess
import sys
import shutil

BASE_PATH = os.path.dirname(os.path.abspath(__file__))


def resolve_npm() -> str | None:
    npm_cmd = shutil.which("npm")
    if npm_cmd:
        return npm_cmd
    windows_npm = r"C:\Program Files\nodejs\npm.cmd"
    if os.path.exists(windows_npm):
        return windows_npm
    return None

log.info("\n════════════════════════════════════════════════════════════════════")
log.info(" NEXO SOBERANO - INSTALACIÓN Y ARRANQUE AUTOMÁTICO")
log.info("════════════════════════════════════════════════════════════════════\n")


def run_step(command, cwd=None, required=True, step_name=""):
    try:
        result = subprocess.run(command, cwd=cwd, check=False)
        if result.returncode != 0 and required:
            raise RuntimeError(f"{step_name} falló con código {result.returncode}")
        return result.returncode == 0
    except FileNotFoundError:
        if required:
            raise
        return False

# 1. Instalar dependencias
log.info("[1/5] Instalando dependencias Python...")
run_step([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], cwd=BASE_PATH, required=True, step_name="Instalación Python")

# 2. Inicializar infraestructura y bitácoras
log.info("[2/5] Inicializando infraestructura y bitácoras...")
run_step([sys.executable, "nexo_soberano.py"], cwd=BASE_PATH, required=True, step_name="Inicialización base")

# 3. Instalar dependencias frontend
frontend_path = os.path.join(BASE_PATH, "frontend")
if os.path.exists(frontend_path):
    npm_cmd = resolve_npm()
    if npm_cmd:
        log.info("[3/5] Instalando dependencias Frontend (npm)...")
        ok_frontend_install = run_step([npm_cmd, "install"], cwd=frontend_path, required=False, step_name="Instalación Frontend")
        if not ok_frontend_install:
            log.info("⚠️ npm install falló. El backend seguirá iniciando.")
    else:
        log.info("[3/5] npm no está disponible en PATH. Se omite instalación frontend.")
else:
    log.info("[3/5] Carpeta frontend no encontrada, omitiendo instalación npm.")

# 4. Lanzar backend y frontend
log.info("[4/5] Lanzando Backend (FastAPI) y Frontend (React)...")
backend_proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "api.main:app", "--reload", "--port", "8000"], cwd=BASE_PATH)
frontend_proc = None
if os.path.exists(frontend_path):
    npm_cmd = resolve_npm()
    if npm_cmd:
        try:
            frontend_proc = subprocess.Popen([npm_cmd, "run", "dev", "--", "--host", "0.0.0.0"], cwd=frontend_path)
        except FileNotFoundError:
            log.info("⚠️ No se pudo iniciar frontend (npm no encontrado).")
    else:
        log.info("⚠️ Frontend no iniciado: npm no encontrado en PATH.")

log.info("[5/5] Sistema en marcha. Accede a:")
log.info("  - Backend: http://localhost:8000/docs")
log.info("  - Frontend: URL mostrada por Vite al iniciar")
log.info("  - GUI Evolutiva: Ejecuta extractor_codigo.py para control inteligente")
log.info("\n✅ Instalación y arranque completos. NEXO SOBERANO está activo.")

# Espera a que los procesos terminen
try:
    backend_proc.wait()
    if frontend_proc:
        frontend_proc.wait()
except KeyboardInterrupt:
    log.info("\n⏹️ Deteniendo servicios...")
    backend_proc.terminate()
    if frontend_proc:
        frontend_proc.terminate()
    log.info("✅ Servicios detenidos.")
