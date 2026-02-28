# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
import logging
import os

# Cache to track if logging has been configured
_logging_configured = False


def setup_logger(name: str = None):
    """
    Set up logging configuration.

    Environment variables:
        LOG_LEVEL: Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                   Default: INFO for development, WARNING recommended for production
        LOG_FORMAT: "simple" for minimal output, "detailed" for full timestamps

    For production deployment, set:
        LOG_LEVEL=WARNING (or ERROR for minimal output)
    """
    global _logging_configured

    # Get log level from environment (default: INFO)
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Get format preference
    log_format = os.getenv("LOG_FORMAT", "detailed")

    if log_format == "simple":
        fmt = "%(levelname)s: %(message)s"
    else:
        fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Only configure once to avoid duplicate handlers
    if not _logging_configured:
        logging.basicConfig(level=log_level, format=fmt)
        _logging_configured = True

        # Suppress noisy third-party loggers
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("openai").setLevel(logging.WARNING)
        logging.getLogger("langchain").setLevel(logging.WARNING)
        logging.getLogger("langchain_core").setLevel(logging.WARNING)
        logging.getLogger("langsmith").setLevel(logging.WARNING)
        logging.getLogger("chromadb").setLevel(logging.WARNING)
        logging.getLogger("google").setLevel(logging.WARNING)
        logging.getLogger("grpc").setLevel(logging.WARNING)
        logging.getLogger("absl").setLevel(logging.WARNING)

    logger_name = name or __name__
    return logging.getLogger(logger_name)