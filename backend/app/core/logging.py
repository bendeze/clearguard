"""Centralized structured logging configuration."""

import logging
import sys

from app.core.config import get_settings


def setup_logging() -> None:
    """Configure application-wide logging."""
    settings = get_settings()
    log_level = logging.DEBUG if settings.debug else logging.INFO

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid duplicate handlers during reloads
    if not root_logger.handlers:
        root_logger.addHandler(handler)
    else:
        root_logger.handlers = [handler]

    # Quiet overly verbose external loggers if needed
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
