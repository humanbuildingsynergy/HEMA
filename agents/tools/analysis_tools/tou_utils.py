# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/tools/analysis_tools/tou_utils.py
"""Time-of-Use (TOU) rate utilities.

This module provides functions to determine peak/off-peak periods based on
the actual utility rate data, rather than hard-coded values. This ensures
consistency between energy analysis, device control, and action correctness
evaluation.
"""

import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import pandas as pd

from config.config import DATA_DIR
from utils.logger import setup_logger
from .cache import get_data_cache, get_current_time

logger = setup_logger()

# Cache for parsed TOU periods
_tou_cache: Dict[str, any] = {
    "periods": None,  # Dict mapping month -> List of (start_hour, end_hour, rate, is_peak)
    "loaded_from": None,  # Path to the rate file used
}


@dataclass
class TOUPeriod:
    """A single TOU period with start/end hours and rate."""
    start_hour: int
    end_hour: int
    rate_cents: float
    is_peak: bool


@dataclass
class TOUClassification:
    """Result of classifying a time against TOU schedule."""
    is_peak: bool
    is_off_peak: bool
    rate_cents: float
    period_name: str  # "peak", "partial_peak", "off_peak"
    reason: str


def _parse_time_to_hour(time_str: str) -> int:
    """Parse a time string (e.g., '14:00' or '23:59') to hour (0-23)."""
    try:
        parts = str(time_str).split(":")
        return int(parts[0])
    except (ValueError, IndexError, AttributeError):
        return 0


def _load_tou_periods() -> Dict[str, List[TOUPeriod]]:
    """Load and parse TOU periods from the rate data.

    Returns a dict mapping month names to lists of TOUPeriod objects.
    """
    global _tou_cache

    # Try to get rate_df from cache first
    cache = get_data_cache()
    rate_df = cache.get("rate_df")
    rate_path = cache.get("rate_path")

    # If no cached rate_df, try to load the default TOU file
    if rate_df is None:
        rate_path = os.path.join(DATA_DIR, "utility_rate", "utility_rate_sample.csv")
        if os.path.exists(rate_path):
            try:
                rate_df = pd.read_csv(rate_path)
            except Exception as e:
                logger.warning(f"Could not load TOU rate file: {e}")
                return {}
        else:
            logger.warning(f"TOU rate file not found: {rate_path}")
            return {}

    # Check if we've already parsed this file
    if _tou_cache["periods"] is not None and _tou_cache["loaded_from"] == rate_path:
        return _tou_cache["periods"]

    # Parse the rate data
    periods: Dict[str, List[TOUPeriod]] = {}

    if rate_df is None or 'Month' not in rate_df.columns:
        return periods

    rate_col = 'Rate (cents per kWh)'
    if rate_col not in rate_df.columns:
        return periods

    # Group by month and find peak rates
    for month in rate_df['Month'].unique():
        month_df = rate_df[rate_df['Month'] == month]

        if month_df.empty:
            continue

        # Find the max rate for this month (peak rate)
        max_rate = month_df[rate_col].max()
        min_rate = month_df[rate_col].min()

        month_periods = []

        for _, row in month_df.iterrows():
            start_hour = _parse_time_to_hour(row.get('Start Time', '00:00'))
            end_time = row.get('End Time', '00:00')
            # Handle "23:59" as 24 for end-of-day
            end_hour = 24 if end_time == '23:59' else _parse_time_to_hour(end_time)
            rate = row[rate_col]

            # Determine if this is a peak period (highest rate for the month)
            is_peak = (rate == max_rate) and (max_rate > min_rate)

            month_periods.append(TOUPeriod(
                start_hour=start_hour,
                end_hour=end_hour,
                rate_cents=rate,
                is_peak=is_peak,
            ))

        periods[month] = month_periods

    # Cache the parsed periods
    _tou_cache["periods"] = periods
    _tou_cache["loaded_from"] = rate_path

    return periods


def _get_month_name(dt: datetime) -> str:
    """Get the month name for a datetime."""
    return dt.strftime('%B')


def get_tou_classification(
    hour: Optional[int] = None,
    dt: Optional[datetime] = None,
) -> TOUClassification:
    """Classify a time as peak, partial-peak, or off-peak.

    Args:
        hour: Hour of day (0-23). If not provided, uses current simulated time.
        dt: Optional datetime for month context. If not provided, uses current simulated time.

    Returns:
        TOUClassification with is_peak, is_off_peak, rate, and reason.
    """
    # Get current time if not provided
    if dt is None:
        dt = get_current_time()

    if hour is None:
        hour = dt.hour

    month_name = _get_month_name(dt)

    # Load TOU periods
    periods = _load_tou_periods()

    if not periods or month_name not in periods:
        # Fallback to default classification if no rate data
        # These are reasonable defaults based on typical TOU schedules
        logger.debug(f"No TOU data for {month_name}, using defaults")

        # Default: peak 14:00-20:00 (summer-like schedule)
        if 14 <= hour < 20:
            return TOUClassification(
                is_peak=True,
                is_off_peak=False,
                rate_cents=20.0,  # Default peak rate
                period_name="peak",
                reason=f"Default peak hours ({hour}:00)",
            )
        else:
            return TOUClassification(
                is_peak=False,
                is_off_peak=True,
                rate_cents=9.0,  # Default off-peak rate
                period_name="off_peak",
                reason=f"Default off-peak hours ({hour}:00)",
            )

    # Find the period for this hour
    month_periods = periods[month_name]

    for period in month_periods:
        # Handle periods that wrap around midnight
        if period.end_hour < period.start_hour:
            # Period wraps around midnight (e.g., 22:00 - 06:00)
            if hour >= period.start_hour or hour < period.end_hour:
                if period.is_peak:
                    return TOUClassification(
                        is_peak=True,
                        is_off_peak=False,
                        rate_cents=period.rate_cents,
                        period_name="peak",
                        reason=f"Peak hours in {month_name} ({hour}:00, rate: {period.rate_cents:.2f}¢/kWh)",
                    )
                else:
                    return TOUClassification(
                        is_peak=False,
                        is_off_peak=True,
                        rate_cents=period.rate_cents,
                        period_name="off_peak",
                        reason=f"Off-peak hours in {month_name} ({hour}:00, rate: {period.rate_cents:.2f}¢/kWh)",
                    )
        else:
            # Normal period (e.g., 14:00 - 20:00)
            if period.start_hour <= hour < period.end_hour:
                if period.is_peak:
                    return TOUClassification(
                        is_peak=True,
                        is_off_peak=False,
                        rate_cents=period.rate_cents,
                        period_name="peak",
                        reason=f"Peak hours in {month_name} ({hour}:00, rate: {period.rate_cents:.2f}¢/kWh)",
                    )
                else:
                    return TOUClassification(
                        is_peak=False,
                        is_off_peak=True,
                        rate_cents=period.rate_cents,
                        period_name="off_peak",
                        reason=f"Off-peak hours in {month_name} ({hour}:00, rate: {period.rate_cents:.2f}¢/kWh)",
                    )

    # Default to off-peak if no matching period found
    return TOUClassification(
        is_peak=False,
        is_off_peak=True,
        rate_cents=9.0,
        period_name="off_peak",
        reason=f"No matching period for {hour}:00 in {month_name}, assuming off-peak",
    )


def is_peak_hour(hour: Optional[int] = None, dt: Optional[datetime] = None) -> bool:
    """Check if an hour falls within peak TOU periods.

    Args:
        hour: Hour of day (0-23). If not provided, uses current simulated time.
        dt: Optional datetime for month context. If not provided, uses current simulated time.

    Returns:
        True if the hour is during peak rates.
    """
    classification = get_tou_classification(hour=hour, dt=dt)
    return classification.is_peak


def is_off_peak_hour(hour: Optional[int] = None, dt: Optional[datetime] = None) -> bool:
    """Check if an hour falls within off-peak TOU periods.

    Args:
        hour: Hour of day (0-23). If not provided, uses current simulated time.
        dt: Optional datetime for month context. If not provided, uses current simulated time.

    Returns:
        True if the hour is during off-peak rates.
    """
    classification = get_tou_classification(hour=hour, dt=dt)
    return classification.is_off_peak


def get_current_rate_info() -> Dict[str, any]:
    """Get current TOU rate information based on simulated time.

    Returns:
        Dict with is_peak, rate_cents, period_name, and reason.
    """
    classification = get_tou_classification()
    return {
        "is_peak": classification.is_peak,
        "is_off_peak": classification.is_off_peak,
        "rate_cents": classification.rate_cents,
        "period_name": classification.period_name,
        "reason": classification.reason,
    }


def get_optimal_hours_for_month(month_name: str) -> List[Tuple[int, int]]:
    """Get the off-peak (lowest rate) hours for a given month.

    Args:
        month_name: Full month name (e.g., "July", "December")

    Returns:
        List of (start_hour, end_hour) tuples for off-peak periods.
    """
    periods = _load_tou_periods()

    if not periods or month_name not in periods:
        # Default off-peak hours
        return [(0, 14), (20, 24)]

    month_periods = periods[month_name]

    # Find all non-peak periods
    off_peak_hours = []
    for period in month_periods:
        if not period.is_peak:
            off_peak_hours.append((period.start_hour, period.end_hour))

    return off_peak_hours


def clear_tou_cache():
    """Clear the TOU cache (useful for testing or when rate data changes)."""
    global _tou_cache
    _tou_cache = {
        "periods": None,
        "loaded_from": None,
    }
