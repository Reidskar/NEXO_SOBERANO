from __future__ import annotations

import logging
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from NEXO_CORE import config


class _WinSafeRotatingHandler(RotatingFileHandler):
    """RotatingFileHandler que no crashea en Windows si el archivo está bloqueado."""
    def doRollover(self):
        try:
            super().doRollover()
        except PermissionError:
            pass  # Windows file lock — seguir sin rotar



class PrivacyFilter(logging.Filter):
    PATTERNS = [
        r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',  # IPs
        r'\bsk-[a-zA-Z0-9]{20,}\b',          # OpenAI API keys
        r'\bMTQ[a-zA-Z0-9._]{50,}\b',        # Discord tokens
        r'\bAIza[a-zA-Z0-9_-]{35}\b',        # Google API keys
        r'\b[\w.-]+@[\w.-]+\.\w+\b',     # emails
    ]

    def filter(self, record):
        for pattern in self.PATTERNS:
            record.msg = re.sub(pattern, '[REDACTED]', str(record.msg))
        return True


def _build_formatter() -> logging.Formatter:
    return logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")


def setup_logging() -> None:
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    level = getattr(logging, config.LOG_LEVEL, logging.INFO)
    root_logger.setLevel(level)

    formatter = _build_formatter()
    privacy_filter = PrivacyFilter()

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(privacy_filter)

    log_file_path = Path(config.LOG_DIR) / config.LOG_FILE_NAME
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = _WinSafeRotatingHandler(
        str(log_file_path), maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8", delay=True
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(privacy_filter)

    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)

    # Silenciar spam de librerías externas
    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.WARNING)
    logging.getLogger("googleapiclient.discovery").setLevel(logging.WARNING)
