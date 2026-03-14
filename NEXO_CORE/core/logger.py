import logging
import sys
from pathlib import Path
from NEXO_CORE import config

def setup_logging() -> None:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_dir / getattr(config, "LOG_FILE_NAME", "nexo.log"), encoding="utf-8"),
    ]
    logging.basicConfig(level=getattr(logging, getattr(config, "LOG_LEVEL", "INFO"), logging.INFO),
                        format=fmt, handlers=handlers, force=True)
