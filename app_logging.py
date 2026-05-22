import logging
import os
from logging.handlers import RotatingFileHandler


APP_FOLDER = os.path.dirname(os.path.abspath(__file__))
LOG_FOLDER = APP_FOLDER
LOG_FILE = os.path.join(APP_FOLDER, "retrotap_debug.log")
LOGGER_NAME = "retrotap"


def _logging_enabled():
    """Read the toggle from config.json each time so the GUI/site switch works live."""
    try:
        from app_config import logging_enabled
        return bool(logging_enabled())
    except Exception:
        return False


def setup_logging():
    os.makedirs(LOG_FOLDER, exist_ok=True)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5_000_000,
        backupCount=5,
        encoding="utf-8",
        delay=True
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger = setup_logging()


def get_log_file():
    return LOG_FILE


def log_info(message):
    if not _logging_enabled():
        return

    logger.info(message)
    try:
        for handler in logger.handlers:
            handler.flush()
    except Exception:
        pass


def log_error(message):
    if not _logging_enabled():
        return

    logger.error(message)
    try:
        for handler in logger.handlers:
            handler.flush()
    except Exception:
        pass
