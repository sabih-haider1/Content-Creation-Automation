from loguru import logger
import sys

logger.configure(handlers=[{"sink": sys.stdout, "format": "{time} - {level} - {message}"}])\n