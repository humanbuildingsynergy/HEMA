# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.

"""
Shared time management for agent tools.

This module provides a unified interface for time management across all agent tools,
eliminating cross-module dependencies. It allows:
- Device control to get current time for TOU calculations
- Evaluation framework to set simulated time from energy data
- All modules to access time without tight coupling

Note: This module will eventually replace agents/tools/analysis_tools/cache.py's
time-related functions to decouple control_tools from analysis_tools.
"""

from datetime import datetime
from typing import Optional

# Module-level time cache
_time_cache = {
    "simulated_time": None,  # Last timestamp from energy data
}


def get_current_time() -> datetime:
    """Get the current time for device control and TOU calculations.

    Returns the simulated time if set (from energy data), otherwise falls
    back to the actual current time. This allows consistent TOU period
    calculations during evaluation and consistent device scheduling.

    Returns:
        The simulated time if available, otherwise datetime.now().

    Example:
        >>> current_time = get_current_time()
        >>> # Use for thermostat scheduling, TOU lookups, etc.
    """
    simulated = _time_cache.get("simulated_time")
    if simulated is not None:
        return simulated
    return datetime.now()


def set_simulated_time(time: Optional[datetime]) -> None:
    """Set the simulated current time for testing and evaluation.

    Args:
        time: The datetime to use as simulated current time, or None to use real time.

    Example:
        >>> from datetime import datetime
        >>> set_simulated_time(datetime(2024, 1, 15, 14, 30))
        >>> current_time = get_current_time()  # Returns Jan 15, 2024 at 2:30 PM
    """
    _time_cache["simulated_time"] = time


def reset_time() -> None:
    """Reset time management to use real current time.

    Clears any simulated time, forcing get_current_time() to return datetime.now().
    """
    _time_cache["simulated_time"] = None


def get_simulated_time() -> Optional[datetime]:
    """Get the simulated time if set, otherwise None.

    Returns:
        The simulated time, or None if not set.

    Note:
        Use get_current_time() instead if you want the actual current time
        as fallback. This function only returns the explicitly set simulated time.
    """
    return _time_cache.get("simulated_time")


def is_simulated_time_set() -> bool:
    """Check if simulated time is currently set.

    Returns:
        True if simulated time is set, False if using real time.
    """
    return _time_cache.get("simulated_time") is not None
