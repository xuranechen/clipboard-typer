from __future__ import annotations

import logging
from pathlib import Path

LOG_PATH = Path("clipboard-typer.log")


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("clipboard_typer")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger
