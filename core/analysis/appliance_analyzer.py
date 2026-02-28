# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# core/analysis/appliance_analyzer.py
"""
Backward-compatible module for ApplianceAnalyzer.

This module re-exports from the new package structure for backward compatibility.
Import from core.analysis.appliance for the new modular structure.
"""
from core.analysis.appliance import (
    ApplianceAnalyzer,
    ApplianceAnalyzerBase,
    ConsistencyAnalyzer,
    PeakPowerAnalyzer,
    UsageFrequencyAnalyzer,
)

__all__ = [
    "ApplianceAnalyzer",
    "ApplianceAnalyzerBase",
    "ConsistencyAnalyzer",
    "PeakPowerAnalyzer",
    "UsageFrequencyAnalyzer",
]
