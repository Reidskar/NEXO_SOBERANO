from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from NEXO_CORE import config


def _build_formatter() -> logging.Formatter:
    return logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")


def setup_logging() -> None:
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    level = getattr(logging, config.LOG_LEVEL, logging.INFO)
    root_logger.setLevel(level)

    formatter = _build_formatter()

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    log_file_path = Path(config.LOG_DIR) / config.LOG_FILE_NAME
    file_handler = RotatingFileHandler(str(log_file_path), maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)
