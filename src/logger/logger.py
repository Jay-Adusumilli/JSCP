import logging
from logging.handlers import RotatingFileHandler
from os import getenv

from dotenv import load_dotenv

class Logger:
    def __init__(self, name: str, log_file: str = None, level=logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        if not self.logger.hasHandlers():
            log_file = log_file or f"{name}.log"
            handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)
            formatter = logging.Formatter(
                '[%(asctime)s] [%(name)s] %(levelname)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
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
Logs = Logger("jscp", log_file=getenv("LOG_PATH"))