import subprocess
import time
import logging
import sys
import os
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
        logging.FileHandler(LOG_DIR / "discord_supervisor.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger("nexo.discord_supervisor")

BOT_PATH = BASE_DIR / "discord_bot" / "bot.js"

def run_supervisor():
    """Monitorea y reinicia el bot de Discord si se cae."""
    logger.info("Starting Discord Bot Supervisor...")
    
    while True:
        try:
            logger.info(f"Yeti-launching Discord bot: {BOT_PATH}")
            # Usar 'node' directamente asumiendo que está en el PATH
            process = subprocess.Popen(
                ["node", str(BOT_PATH)],
                cwd=str(BASE_DIR / "discord_bot"),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8"
            )

            # Leer salida en tiempo real
            for line in process.stdout:
                log.info(f"[DISCORD] {line.strip()}")
            
            process.wait()
            rc = process.returncode
            logger.warning(f"Discord bot process exited with code {rc}. Restarting in 5s...")
            time.sleep(5)

        except Exception as e:
            logger.error(f"Supervisor encountered an error: {e}. Restarting loop in 10s...")
            time.sleep(10)

if __name__ == "__main__":
    run_supervisor()
