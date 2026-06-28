"""
Flora OS — Logging Configuration
Structured logging with per-module loggers.
"""

import logging
import sys
from app.config import settings


def setup_logging() -> None:
    level = logging.DEBUG if settings.is_development else logging.INFO
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    logging.basicConfig(
        level=level,
        format=fmt,
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # Silence noisy third-party loggers
    for noisy in ("httpx", "httpcore", "urllib3", "googleapiclient"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"flora.{name}")
