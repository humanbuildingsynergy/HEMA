# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# api/dependencies.py
"""Shared dependencies for FastAPI application."""
from functools import lru_cache
from agents.graph.builder import HEMAGraphRunner
from utils.logger import setup_logger

logger = setup_logger()


@lru_cache()
def get_graph_runner() -> HEMAGraphRunner:
    """
    Get a singleton instance of the HEMAGraphRunner.

    Uses lru_cache to ensure only one instance is created
    and reused across all requests.
    """
    logger.info("Creating HEMAGraphRunner singleton")
    return HEMAGraphRunner(use_persistence=True)
