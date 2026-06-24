"""Loguru-based logger. Import `log` everywhere."""

import sys
from loguru import logger as log

log.remove()
log.add(sys.stderr, level="INFO", colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - {message}")
log.add("data/app.log", rotation="10 MB", retention="7 days", level="DEBUG")

__all__ = ["log"]
