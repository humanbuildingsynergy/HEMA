#!/usr/bin/env python3
# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/comparison/__init__.py
"""Comparative evaluation subpackage.

Provides functionality for running and analyzing comparisons between HEMA and vanilla LLM systems.
Re-exports all public symbols for backward compatibility with evaluation.run_comparison.
"""

# Re-export all public symbols from runners
from .runners import (
    run_comparison,
    aggregate_system_results,
    format_multi_system_summary,
    DEFAULT_COMPARISON_SYSTEMS,
    ALL_SYSTEM_TYPES,
    RAW_CSV_SYSTEMS,
    STRUCTURED_SYSTEMS,
    EXPERIMENT_RUNNERS,
)

# Re-export all public symbols from formatters
from .formatters import (
    format_comparison_summary,
    format_comparison_report,
    format_multi_system_report,
)

# Re-export all public symbols from matrix
from .matrix import (
    run_all_scenarios,
    run_full_matrix,
    COMPARISON_SCENARIOS,
)

# Re-export CLI
from .cli import main

__all__ = [
    # runners
    "run_comparison",
    "aggregate_system_results",
    "format_multi_system_summary",
    "DEFAULT_COMPARISON_SYSTEMS",
    "ALL_SYSTEM_TYPES",
    "RAW_CSV_SYSTEMS",
    "STRUCTURED_SYSTEMS",
    "EXPERIMENT_RUNNERS",
    # formatters
    "format_comparison_summary",
    "format_comparison_report",
    "format_multi_system_report",
    # matrix
    "run_all_scenarios",
    "run_full_matrix",
    "COMPARISON_SCENARIOS",
    # cli
    "main",
]
