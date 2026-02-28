# core/analysis/appliance/__init__.py
"""Appliance analysis package.

This package provides modular appliance analysis functionality:
- base: Core appliance analysis and consumption rankings
- consistency: Daily usage pattern consistency analysis
- peak_power: Peak power consumption analysis
- frequency: Usage frequency analysis with threshold-based detection
- variability: Usage variability analysis with coefficient of variation
"""
from typing import Dict, Any, List, Optional
import pandas as pd

from .base import ApplianceAnalyzerBase
from .consistency import ConsistencyAnalyzer
from .peak_power import PeakPowerAnalyzer
from .frequency import UsageFrequencyAnalyzer
from .variability import UsageVariabilityAnalyzer, TimeframeGranularity


class ApplianceAnalyzer(ApplianceAnalyzerBase):
    """
    Comprehensive appliance analyzer combining all analysis modules.

    This class inherits from ApplianceAnalyzerBase and adds methods from
    the specialized analyzer modules.
    """

    def __init__(self):
        """Initialize the analyzer with specialized modules."""
        super().__init__()
        self._consistency_analyzer = ConsistencyAnalyzer()
        self._peak_power_analyzer = PeakPowerAnalyzer()
        self._frequency_analyzer = UsageFrequencyAnalyzer()
        self._variability_analyzer = UsageVariabilityAnalyzer()

    # Consistency analysis methods
    def _calculate_daily_consistency(self, df: pd.DataFrame, appliance: str) -> Dict[str, float]:
        """Calculate daily usage consistency for an appliance."""
        return self._consistency_analyzer.calculate_daily_consistency(df, appliance)

    # Peak power analysis methods
    def _analyze_peak_power(self, df: pd.DataFrame, appliance: str) -> Dict[str, Any]:
        """Analyze peak power consumption for an appliance."""
        return self._peak_power_analyzer.analyze_peak_power(df, appliance)

    # Usage frequency analysis methods
    def calculate_hourly_usage_frequency(
        self,
        df: pd.DataFrame,
        appliance: str,
        threshold: float
    ) -> pd.DataFrame:
        """
        Calculate hourly usage frequency for an appliance.

        The hourly usage frequency is the sum of binary indicator values
        (True: when above threshold, False: when below threshold) for all
        15-minute intervals within each hour.
        """
        return self._frequency_analyzer.calculate_hourly_usage_frequency(df, appliance, threshold)

    def calculate_normalized_avg_hourly_frequency(
        self,
        df: pd.DataFrame,
        appliance: str,
        threshold: float,
        num_days: int = None
    ) -> pd.DataFrame:
        """
        Calculate normalized averaged hourly usage frequency.

        The normalized averaged hourly usage frequency is the average of
        hourly usage frequency values over a specified number of days,
        normalized by the maximum possible frequency (4 for 15-min intervals).
        """
        return self._frequency_analyzer.calculate_normalized_avg_hourly_frequency(
            df, appliance, threshold, num_days
        )

    def analyze_usage_frequency(
        self,
        df: pd.DataFrame,
        appliances: List[str] = None,
        thresholds: Dict[str, float] = None,
        num_days: int = None
    ) -> Dict[str, Any]:
        """
        Comprehensive usage frequency analysis for multiple appliances.

        Args:
            df: DataFrame containing appliance data
            appliances: List of appliance names to analyze. If None, analyzes top 5 by consumption.
            thresholds: Dict mapping appliance names to threshold values in kW.
            num_days: Number of days to include in normalized average.

        Returns:
            Dict containing summary, appliance_profiles, high_usage_hours, and insights.
        """
        return self._frequency_analyzer.analyze_usage_frequency(
            df, appliances, thresholds, num_days
        )

    # Usage variability analysis methods
    def calculate_variability(
        self,
        df: pd.DataFrame,
        appliance: str,
        timeframe: TimeframeGranularity = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate usage variability for a single appliance using coefficient of variation.

        Args:
            df: DataFrame containing appliance data
            appliance: Name of appliance column
            timeframe: Aggregation level ("hourly", "daily", "weekly", "monthly")
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)

        Returns:
            Dict containing cv, mean_kwh, std_kwh, min_kwh, max_kwh, n_periods, variability_level.
        """
        return self._variability_analyzer.calculate_variability(
            df, appliance, timeframe, start_date, end_date
        )

    def analyze_usage_variability(
        self,
        df: pd.DataFrame,
        appliances: Optional[List[str]] = None,
        timeframe: TimeframeGranularity = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive usage variability analysis for multiple appliances.

        Args:
            df: DataFrame containing appliance data
            appliances: List of appliance names to analyze. If None, analyzes top 5 by consumption.
            timeframe: Aggregation level ("hourly", "daily", "weekly", "monthly")
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)

        Returns:
            Dict containing summary, appliance_variability, rankings, and insights.
        """
        return self._variability_analyzer.analyze_usage_variability(
            df, appliances, timeframe, start_date, end_date
        )


__all__ = [
    "ApplianceAnalyzer",
    "ApplianceAnalyzerBase",
    "ConsistencyAnalyzer",
    "PeakPowerAnalyzer",
    "UsageFrequencyAnalyzer",
    "UsageVariabilityAnalyzer",
    "TimeframeGranularity",
]
