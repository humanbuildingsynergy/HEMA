# core/analysis/solar/__init__.py
"""Solar power analysis package.

This package provides solar power generation analysis:
- availability: Solar availability and generation profile analysis
- alignment: Solar-appliance alignment analysis
"""
from .availability import SolarAvailabilityAnalyzer, AnalysisType, TimeframeType
from .alignment import SolarAlignmentAnalyzer

__all__ = [
    "SolarAvailabilityAnalyzer",
    "AnalysisType",
    "TimeframeType",
    "SolarAlignmentAnalyzer",
]
