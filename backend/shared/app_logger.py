"""Shared application logger — consistent format across all agents.

Usage:
    from shared.app_logger import get_logger
    logger = get_logger(__name__)
    logger.info("Processing listing", extra={"listing_id": 42})
"""

import logging
import sys


def get_logger(module_name: str) -> logging.Logger:
    """Get a configured logger for the given module."""
    logger = logging.getLogger(module_name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
