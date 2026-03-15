from __future__ import annotations

import logging
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from NEXO_CORE import config


class PersonalDataFilter(logging.Filter):
    PATTERNS = [
        r'\b[\w.-]+@[\w.-]+\.\w+\b',       # emails
        r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',  # IPs
        r'\bsk-[a-zA-Z0-9]{20,}\b',          # API keys OpenAI
        r'\bAIza[a-zA-Z0-9_-]{35}\b',        # Google API keys
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
    pii_filter = PersonalDataFilter()

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(pii_filter)

    log_file_path = Path(config.LOG_DIR) / config.LOG_FILE_NAME
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        str(log_file_path), maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(pii_filter)

    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)
