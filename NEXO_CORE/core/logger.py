import re
import logging
import sys
from pathlib import Path
from NEXO_CORE import config

class PersonalDataFilter(logging.Filter):
    PATTERNS = [
        r'\b[\w.-]+@[\w.-]+\.\w+\b',  # emails
        r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',  # IPs
        r'\bsk-[a-zA-Z0-9]{20,}\b',  # API keys OpenAI
        r'\bAIza[a-zA-Z0-9_-]{35}\b',  # Google API keys
    ]
    def filter(self, record):
        for pattern in self.PATTERNS:
            record.msg = re.sub(pattern, '[REDACTED]', str(record.msg))
        return True

def setup_logging() -> None:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_dir / getattr(config, "LOG_FILE_NAME", "nexo.log"), encoding="utf-8"),
    ]
    
    # Aplicar el filtro a todos los handlers
    pdf_filter = PersonalDataFilter()
    for h in handlers:
        h.addFilter(pdf_filter)
        
    logging.basicConfig(level=getattr(logging, getattr(config, "LOG_LEVEL", "INFO"), logging.INFO),
                        format=fmt, handlers=handlers, force=True)
