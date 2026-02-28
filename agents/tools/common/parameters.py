# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.

"""
Common parameter parsing utilities for analysis tools.

This module consolidates parameter parsing logic that was duplicated across
multiple analysis tool modules. It provides utilities for parsing user-provided
parameters from tool inputs.
"""

from typing import List, Optional, Tuple


def parse_appliance_list(appliances_str: Optional[str]) -> Optional[List[str]]:
    """Parse comma-separated appliance list into list of appliance names.

    Args:
        appliances_str: Comma-separated string of appliance names, or None

    Returns:
        List of appliance names (with whitespace trimmed), or None if input was None

    Example:
        >>> parse_appliance_list("HVAC, Water Heater, Refrigerator")
        ['HVAC', 'Water Heater', 'Refrigerator']
        >>> parse_appliance_list(None)
        None
    """
    if not appliances_str:
        return None
    return [a.strip() for a in appliances_str.split(",")]


def parse_time_range(range_str: Optional[str]) -> Optional[Tuple[int, int]]:
    """Parse time range string into (start_hour, end_hour) tuple.

    Formats: "9-17", "9 to 17", "9:00-17:00"

    Args:
        range_str: Time range string (see formats above), or None

    Returns:
        Tuple of (start_hour, end_hour) as integers, or None if input was None

    Raises:
        ValueError: If range_str cannot be parsed or is invalid

    Example:
        >>> parse_time_range("9-17")
        (9, 17)
        >>> parse_time_range("9:00-17:00")
        (9, 17)
    """
    if not range_str:
        return None

    # Remove common separators and normalize
    range_str = range_str.replace(" to ", "-").replace(":", "").strip()

    try:
        parts = range_str.split("-")
        if len(parts) != 2:
            raise ValueError(f"Invalid time range format: {range_str}")

        start = int(parts[0].strip())
        end = int(parts[1].strip())

        if not (0 <= start <= 24 and 0 <= end <= 24):
            raise ValueError(f"Hours must be between 0 and 24: {start}-{end}")

        if start >= end:
            raise ValueError(f"Start time must be before end time: {start}-{end}")

        return (start, end)
    except ValueError as e:
        raise ValueError(f"Could not parse time range '{range_str}': {e}")


def parse_date_range(range_str: Optional[str]) -> Optional[Tuple[str, str]]:
    """Parse date range string into (start_date, end_date) tuple.

    Formats: "2024-01-01-2024-12-31", "2024-01-01 to 2024-12-31"

    Args:
        range_str: Date range string in YYYY-MM-DD format, or None

    Returns:
        Tuple of (start_date, end_date) as strings, or None if input was None

    Raises:
        ValueError: If range_str cannot be parsed

    Example:
        >>> parse_date_range("2024-01-01-2024-12-31")
        ('2024-01-01', '2024-12-31')
    """
    if not range_str:
        return None

    # Normalize separators
    range_str = range_str.replace(" to ", "-").strip()

    try:
        # Find all dates in YYYY-MM-DD format
        parts = range_str.split("-")

        # Need at least 6 parts for YYYY-MM-DD-YYYY-MM-DD
        if len(parts) < 6:
            raise ValueError(f"Invalid date range format: {range_str}")

        start_date = f"{parts[0]}-{parts[1]}-{parts[2]}"
        end_date = f"{parts[3]}-{parts[4]}-{parts[5]}"

        # Basic validation
        if len(start_date) != 10 or len(end_date) != 10:
            raise ValueError(f"Invalid date format (expected YYYY-MM-DD)")

        return (start_date, end_date)
    except (ValueError, IndexError) as e:
        raise ValueError(f"Could not parse date range '{range_str}': {e}")


def parse_device_name(name_str: Optional[str]) -> Optional[str]:
    """Parse and normalize device name from user input.

    Args:
        name_str: Device name string, or None

    Returns:
        Normalized device name, or None if input was None

    Example:
        >>> parse_device_name("  HVAC  ")
        'HVAC'
    """
    if not name_str:
        return None
    return name_str.strip()


def parse_boolean(value_str: Optional[str]) -> Optional[bool]:
    """Parse boolean value from user input.

    Recognizes: yes, no, true, false, y, n, 1, 0 (case-insensitive)

    Args:
        value_str: Boolean string, or None

    Returns:
        Boolean value, or None if input was None

    Raises:
        ValueError: If value_str is not a recognized boolean format

    Example:
        >>> parse_boolean("yes")
        True
        >>> parse_boolean("false")
        False
    """
    if value_str is None:
        return None

    value_lower = value_str.strip().lower()

    if value_lower in ("yes", "true", "y", "1", "on"):
        return True
    elif value_lower in ("no", "false", "n", "0", "off"):
        return False
    else:
        raise ValueError(f"Could not parse boolean value: {value_str}")


def parse_numeric_range(
    range_str: Optional[str], parse_as_float: bool = False
) -> Optional[Tuple[float, float]]:
    """Parse numeric range string into (min, max) tuple.

    Formats: "10-100", "10 to 100", "10.5-99.5"

    Args:
        range_str: Range string, or None
        parse_as_float: If True, parse as floats; if False, parse as integers

    Returns:
        Tuple of (min_value, max_value), or None if input was None

    Raises:
        ValueError: If range_str cannot be parsed

    Example:
        >>> parse_numeric_range("10-100")
        (10.0, 100.0)
    """
    if not range_str:
        return None

    try:
        # Normalize
        range_str = range_str.replace(" to ", "-").strip()
        parts = range_str.split("-")

        if len(parts) != 2:
            raise ValueError(f"Invalid range format: {range_str}")

        parse_func = float if parse_as_float else int
        min_val = parse_func(parts[0].strip())
        max_val = parse_func(parts[1].strip())

        if min_val >= max_val:
            raise ValueError(f"Min value must be less than max value: {min_val}-{max_val}")

        return (min_val, max_val)
    except ValueError as e:
        raise ValueError(f"Could not parse numeric range '{range_str}': {e}")


def validate_optional_string(
    value: Optional[str], min_length: int = 1, max_length: Optional[int] = None
) -> bool:
    """Validate optional string parameter.

    Args:
        value: String to validate, or None
        min_length: Minimum required length
        max_length: Maximum allowed length, or None for unlimited

    Returns:
        True if valid, False otherwise

    Example:
        >>> validate_optional_string("HVAC", min_length=1, max_length=50)
        True
        >>> validate_optional_string("", min_length=1)
        False
    """
    if value is None:
        return True  # None is acceptable (optional)

    if len(value.strip()) < min_length:
        return False

    if max_length is not None and len(value) > max_length:
        return False

    return True
