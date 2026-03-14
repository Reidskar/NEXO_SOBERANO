import subprocess
import time
import logging
import sys
from pathlib import Path

# --- CONFIGURATION ---
BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs" / "supervisors"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "web_ai_supervisor.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger("nexo.web_ai_supervisor")

# Comando para iniciar FastAPI
API_COMMAND = [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

def run_supervisor():
    """Monitorea y reinicia el backend FastAPI (Web/AI) si se cae."""
    logger.info("Starting Web/AI Backend Supervisor...")
    
    while True:
        try:
            logger.info(f"Launching FastAPI backend: {' '.join(API_COMMAND)}")
            process = subprocess.Popen(
                API_COMMAND,
                cwd=str(BASE_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace"
            )

            # Leer salida en tiempo real
            for line in process.stdout:
                print(f"[BACKEND] {line.strip()}")
            
            process.wait()
            rc = process.returncode
            logger.warning(f"FastAPI backend process exited with code {rc}. Restarting in 5s...")
            time.sleep(5)

        except Exception as e:
            logger.error(f"Supervisor encountered an error: {e}. Restarting loop in 10s...")
            time.sleep(10)

if __name__ == "__main__":
    run_supervisor()
