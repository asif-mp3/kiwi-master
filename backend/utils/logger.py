"""
Centralized logging configuration for Thara AI backend.
Replaces all print() calls with structured logging.
"""
import logging
import sys


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure and return the application root logger."""
    logger = logging.getLogger("thara")

    if logger.handlers:
        return logger  # Already configured

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Console handler with UTF-8 support
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def get_logger(name: str = "thara") -> logging.Logger:
    """Get a child logger for a specific module."""
    return logging.getLogger(f"thara.{name}")
