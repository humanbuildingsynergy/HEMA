# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.

"""
Unified data period utilities for analysis tools.

This module consolidates data period extraction and formatting logic that was
previously duplicated across consumption_tools, frequency_tools, solar_tools,
aggregation_tools, and query_tools.

It provides utilities to:
- Extract data period info from loaded energy dataframe
- Format data period as human-readable strings
- Get scope information for analysis context
"""

from typing import Any, Dict, Optional

import pandas as pd


def find_timestamp_column(df: pd.DataFrame) -> Optional[str]:
    """Find the timestamp column in a dataframe.

    Checks for common column names in order: local_15min, timestamp, datetime.

    Args:
        df: Pandas dataframe to search

    Returns:
        Name of timestamp column, or None if not found

    Example:
        >>> df = pd.read_csv("energy.csv")
        >>> ts_col = find_timestamp_column(df)
        >>> if ts_col:
        ...     df[ts_col] = pd.to_datetime(df[ts_col])
    """
    for col in ["local_15min", "timestamp", "datetime", "time", "date"]:
        if col in df.columns:
            return col
    return None


def get_data_period_info(df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """Extract data period information from energy dataframe.

    If no dataframe provided, attempts to get from cache.

    Args:
        df: Pandas dataframe with energy data. If None, tries to get from cache.

    Returns:
        Dictionary with:
        - start_date: Start date as string "YYYY-MM-DD"
        - end_date: End date as string "YYYY-MM-DD"
        - num_days: Number of days in period
        - start_datetime: Start as datetime object
        - end_datetime: End as datetime object
        Returns empty dict if unable to extract.

    Example:
        >>> from agents.tools.analysis_tools.cache import get_data_cache
        >>> cache = get_data_cache()
        >>> period_info = get_data_period_info(cache["energy_df"])
        >>> if period_info:
        ...     print(f"Data from {period_info['start_date']} to {period_info['end_date']}")
    """
    # Try to get from cache if not provided
    if df is None:
        try:
            from agents.tools.analysis_tools.cache import get_data_cache
            cache = get_data_cache()
            df = cache.get("energy_df")
        except (ImportError, AttributeError):
            return {}

    if df is None or df.empty:
        return {}

    try:
        # Find timestamp column
        ts_col = find_timestamp_column(df)
        if not ts_col:
            return {}

        # Convert to datetime and get range
        timestamps = pd.to_datetime(df[ts_col])
        start_datetime = timestamps.min()
        end_datetime = timestamps.max()
        num_days = (end_datetime - start_datetime).days + 1

        return {
            "start_date": start_datetime.strftime("%Y-%m-%d"),
            "end_date": end_datetime.strftime("%Y-%m-%d"),
            "num_days": num_days,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
        }
    except Exception:
        return {}


def get_data_scope_string(df: Optional[pd.DataFrame] = None) -> str:
    """Get human-readable data scope/period string.

    Format: "YYYY-MM-DD to YYYY-MM-DD (N days)"

    Args:
        df: Pandas dataframe. If None, gets from cache.

    Returns:
        Formatted date range string, or empty string if unavailable

    Example:
        >>> scope = get_data_scope_string()
        >>> print(scope)  # "2024-01-01 to 2024-12-31 (365 days)"
    """
    period_info = get_data_period_info(df)
    if not period_info:
        return ""

    return (
        f"{period_info['start_date']} to {period_info['end_date']} "
        f"({period_info['num_days']} days)"
    )


def format_data_period_header(df: Optional[pd.DataFrame] = None) -> str:
    """Format data period info as a header for tool outputs.

    Includes important context about the data period and what aggregation level
    the results represent.

    Args:
        df: Pandas dataframe. If None, gets from cache.

    Returns:
        Formatted header string, or empty string if no data available

    Example:
        >>> header = format_data_period_header()
        >>> response = header + "### Analysis Results\\n..."
    """
    period_info = get_data_period_info(df)
    if not period_info:
        return ""

    days = period_info["num_days"]
    return f"""**Data Scope:** {period_info['start_date']} to {period_info['end_date']} ({days} days)
All values below are totals for this {days}-day period. They are NOT monthly or annual totals, and NOT filtered by day type (weekday/weekend) unless explicitly stated.

"""


def validate_data_loaded(df: Optional[pd.DataFrame] = None) -> tuple[bool, str]:
    """Check if energy data is loaded and valid.

    Args:
        df: Dataframe to validate. If None, gets from cache.

    Returns:
        Tuple of (is_valid, error_message)
        - If valid: (True, "")
        - If invalid: (False, error message to show user)

    Example:
        >>> is_valid, error = validate_data_loaded()
        >>> if not is_valid:
        ...     return error
        >>> # Continue with analysis
    """
    if df is None:
        try:
            from agents.tools.analysis_tools.cache import get_data_cache
            cache = get_data_cache()
            df = cache.get("energy_df")
        except (ImportError, AttributeError):
            return False, "Error: No data loaded. Please use load_energy_data first."

    if df is None:
        return False, "Error: No data loaded. Please use load_energy_data first."

    if df.empty:
        return False, "Error: Loaded data is empty. Please check your data file."

    if find_timestamp_column(df) is None:
        return (
            False,
            "Error: Unable to find timestamp column in data. "
            "Expected 'local_15min', 'timestamp', or 'datetime'.",
        )

    return True, ""


def get_or_calculate_processed_df(df: Optional[pd.DataFrame] = None) -> Optional[pd.DataFrame]:
    """Get processed dataframe if available, else return energy dataframe.

    This is a common pattern: use processed data if available, fall back to energy data.

    Args:
        df: If provided, skip cache lookup

    Returns:
        Processed dataframe if available, else energy dataframe, or None if nothing loaded

    Example:
        >>> df = get_or_calculate_processed_df()
        >>> if df is not None:
        ...     # Use df for analysis
    """
    if df is not None:
        return df

    try:
        from agents.tools.analysis_tools.cache import get_data_cache
        cache = get_data_cache()

        # Prefer processed data if available
        processed = cache.get("processed_df")
        if processed is not None:
            return processed

        # Fall back to energy data
        return cache.get("energy_df")
    except (ImportError, AttributeError):
        return None
