"""Rotating file logger for DevPilot."""

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

LOG_DIR: Path = Path.home() / ".local" / "share" / "devpilot" / "logs"
LOG_FORMAT = "[%(asctime)s][%(levelname)s][%(module)s] %(message)s"


def setup_logger(name: str = "devpilot") -> logging.Logger:
    """Create and configure the DevPilot application logger.

    Uses a TimedRotatingFileHandler with daily rotation and 7-day retention.
    Logs are written to ~/.local/share/devpilot/logs/devpilot.log.

    Args:
        name: Logger name, defaults to "devpilot".

    Returns:
        Configured logger instance.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    handler = TimedRotatingFileHandler(
        filename=str(LOG_DIR / "devpilot.log"),
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S"))

    logger.addHandler(handler)
    return logger
