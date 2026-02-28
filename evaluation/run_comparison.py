#!/usr/bin/env python3
# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/run_comparison.py
"""Run comparative evaluation between HEMA and Vanilla LLM variants.

This module is a re-export facade that provides backward compatibility.
All functionality has been moved to the evaluation.comparison subpackage.

Default comparison uses 4 focused systems:
- vanilla: Raw CSV data with minimal prompting
- vanilla_structured: Preprocessed structured data with minimal prompting
- vanilla_structured_cot: Preprocessed structured data with CoT prompting
- hema: Multi-agent architecture with tools

This selection enables analysis of:
- vanilla vs vanilla_structured: Effect of data preprocessing alone
- vanilla_structured vs vanilla_structured_cot: Effect of CoT prompting
- vanilla_structured_cot vs hema: Gap that multi-agent architecture provides

Usage:
    # Single persona-scenario with default 4 systems
    python -m evaluation.run_comparison --persona tech_savvy_optimizer --scenario appliance_analysis

    # All 7 systems comparison (includes raw CoT/ReAct and structured ReAct)
    python -m evaluation.run_comparison --persona tech_savvy_optimizer --scenario appliance_analysis --all-systems

    # Specific systems
    python -m evaluation.run_comparison --persona tech_savvy_optimizer --scenario appliance_analysis \\
        --systems hema,vanilla_structured,vanilla_structured_cot

    # Multiple runs for statistical rigor (default: 3)
    python -m evaluation.run_comparison --persona tech_savvy_optimizer --scenario appliance_analysis --runs 3

    # Full matrix (all personas × all scenarios)
    python -m evaluation.run_comparison --full-matrix --runs 3

    # All scenarios for one persona
    python -m evaluation.run_comparison --all-scenarios --persona confused_newcomer --runs 3
"""

# Re-export all public symbols from evaluation.comparison
from evaluation.comparison import (
    run_comparison,
    aggregate_system_results,
    format_multi_system_summary,
    format_comparison_summary,
    format_comparison_report,
    format_multi_system_report,
    run_all_scenarios,
    run_full_matrix,
    DEFAULT_COMPARISON_SYSTEMS,
    ALL_SYSTEM_TYPES,
    RAW_CSV_SYSTEMS,
    STRUCTURED_SYSTEMS,
    COMPARISON_SCENARIOS,
    EXPERIMENT_RUNNERS,
    main,
)

__all__ = [
    "run_comparison",
    "aggregate_system_results",
    "format_multi_system_summary",
    "format_comparison_summary",
    "format_comparison_report",
    "format_multi_system_report",
    "run_all_scenarios",
    "run_full_matrix",
    "DEFAULT_COMPARISON_SYSTEMS",
    "ALL_SYSTEM_TYPES",
    "RAW_CSV_SYSTEMS",
    "STRUCTURED_SYSTEMS",
    "COMPARISON_SCENARIOS",
    "EXPERIMENT_RUNNERS",
    "main",
]


if __name__ == "__main__":
    main()
