import logging
from logging.handlers import RotatingFileHandler
from os import getenv
import os

from dotenv import load_dotenv


class Logger:
    def __init__(self, name: str, log_file: str = None, level=logging.INFO):
        """
        A simple logger class that wraps Python's logging module.
        :param name: Name of the logger.
        :param log_file: Path to the log file.
        :param level: Logging level.
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        if not self.logger.hasHandlers():
            log_file = log_file or f"{name}.log"

            # Ensure the log directory exists if a directory is specified
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                try:
                    os.makedirs(log_dir, exist_ok=True)
                except Exception:
                    # Fallback to current working directory if directory creation fails
                    log_file = f"{name}.log"

            handler = RotatingFileHandler(
                log_file, maxBytes=5 * 1024 * 1024, backupCount=3
            )
            formatter = logging.Formatter(
                "[%(asctime)s] [%(name)s] %(levelname)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def info(self, message: str):
        self.logger.info(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str):
        self.logger.error(message)

    def debug(self, message: str):
        self.logger.debug(message)

    def set_level(self, level):
        self.logger.setLevel(level)


# Load the env
load_dotenv()

# Init the logger.
# Default to a relative logs directory to avoid permission issues on import.
log_file_path = getenv("LOG_PATH") or "./logs/jscp.log"
Logs = Logger("jscp", log_file=log_file_path)
