"""
Structured logging for CloudRAG Lambda functions.

Deliberately does NOT log full document contents or question text at INFO
level (only lengths/counts), to avoid dumping potentially sensitive policy
content into CloudWatch.
"""

import logging
import os
import sys

_LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | request_id=%(request_id)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(_LOG_LEVEL)
        logger.propagate = False
    return logger


class RequestContext:
    """Small helper to inject a request_id into every log line for a request."""

    def __init__(self, logger: logging.Logger, request_id: str):
        self.logger = logger
        self.request_id = request_id

    def _extra(self):
        return {"request_id": self.request_id}

    def info(self, msg, *args):
        self.logger.info(msg, *args, extra=self._extra())

    def warning(self, msg, *args):
        self.logger.warning(msg, *args, extra=self._extra())

    def error(self, msg, *args):
        self.logger.error(msg, *args, extra=self._extra())

    def exception(self, msg, *args):
        self.logger.exception(msg, *args, extra=self._extra())
