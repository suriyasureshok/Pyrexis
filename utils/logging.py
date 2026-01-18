"""
utils/logging.py

Logging utility for standardized log formatting.

This module sets up a logger with a consistent format that includes
timestamps, log levels, thread names, and process IDs.
"""

import logging
import sys


def setup_logging(level=logging.INFO):
    logger = logging.getLogger()
    logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] "
        "[%(threadName)s] [%(process)d] "
        "%(message)s"
    )
    handler.setFormatter(formatter)

    logger.handlers.clear()
    logger.addHandler(handler)
