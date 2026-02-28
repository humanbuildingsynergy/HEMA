# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/tools/analysis_tools/cache.py
"""Shared data cache for analysis tools."""

from datetime import datetime
from typing import Optional

# Module-level cache for loaded data (shared across tool calls)
_data_cache = {
    "energy_df": None,
    "rate_df": None,
    "processed_df": None,
    "energy_path": None,
    "rate_path": None,
    "analysis_results": None,
    "household_profile": None,
    # Household configuration detection
    "rate_type": None,      # "tou" or "flat"
    "has_solar": None,      # True/False
    # Simulated time (for device control and TOU calculations)
    "simulated_time": None,  # Last timestamp from energy data
}

# Evaluation configuration (controls data filtering for fair comparison)
_eval_config = {
    "data_days": None,  # Number of days to use from start of dataset (None = all)
}


def get_data_cache():
    """Get the current data cache."""
    return _data_cache


def clear_data_cache():
    """Clear the data cache.

    Note: Clears in place to preserve references from other modules.
    """
    _data_cache["energy_df"] = None
    _data_cache["rate_df"] = None
    _data_cache["processed_df"] = None
    _data_cache["energy_path"] = None
    _data_cache["rate_path"] = None
    _data_cache["analysis_results"] = None
    _data_cache["household_profile"] = None
    _data_cache["rate_type"] = None
    _data_cache["has_solar"] = None
    _data_cache["simulated_time"] = None


def get_simulated_time() -> Optional[datetime]:
    """Get the simulated current time for device control.

    Returns the last timestamp from the loaded energy data, which is used
    as the "current time" for device control operations. This ensures
    consistency between energy analysis and device control recommendations.

    Returns:
        The simulated time (last timestamp from energy data), or None if no data loaded.
    """
    return _data_cache.get("simulated_time")


def set_simulated_time(time: Optional[datetime]) -> None:
    """Set the simulated current time.

    Args:
        time: The datetime to use as simulated current time, or None to clear.
    """
    _data_cache["simulated_time"] = time


def get_current_time() -> datetime:
    """Get the current time for device control operations.

    Returns the simulated time if set (from energy data), otherwise falls
    back to the actual current time. This allows consistent TOU period
    calculations during evaluation.

    Returns:
        The simulated time if available, otherwise datetime.now().
    """
    simulated = _data_cache.get("simulated_time")
    if simulated is not None:
        return simulated
    return datetime.now()


def set_eval_data_days(days: Optional[int]) -> None:
    """Set the number of days of data to use during evaluation.

    When set, load_energy_data will automatically filter to the first N days
    of the dataset. This ensures consistency across different evaluation systems.

    Args:
        days: Number of days from start of dataset to use, or None for all data.
    """
    _eval_config["data_days"] = days


def get_eval_data_days() -> Optional[int]:
    """Get the configured number of days for evaluation data filtering.

    Returns:
        Number of days to filter to, or None if no filtering should be applied.
    """
    return _eval_config.get("data_days")


def reset_eval_config() -> None:
    """Reset evaluation configuration to defaults."""
    global _eval_config
    _eval_config = {
        "data_days": None,
    }
