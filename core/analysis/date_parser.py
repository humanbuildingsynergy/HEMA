# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# core/analysis/date_parser.py
"""Natural language date parsing utilities for energy data queries."""
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple

from utils.logger import setup_logger

logger = setup_logger()


def parse_natural_date(
    date_str: str,
    reference_date: Optional[datetime] = None
) -> Optional[datetime]:
    """
    Parse a natural language date string into a datetime object.

    Supports:
    - Relative: "today", "yesterday", "last week", "last month", "last year"
    - Offsets: "3 days ago", "2 weeks ago", "1 month ago"
    - Named days: "monday", "last monday", "this friday"
    - Specific dates: "2024-01-15", "January 15, 2024", "01/15/2024"

    Args:
        date_str: Natural language date string
        reference_date: Reference date for relative calculations (default: now)

    Returns:
        Parsed datetime or None if parsing fails
    """
    if reference_date is None:
        reference_date = datetime.now()

    date_str = date_str.lower().strip()

    # Handle relative keywords
    if date_str == "today":
        return reference_date.replace(hour=0, minute=0, second=0, microsecond=0)

    if date_str == "yesterday":
        return (reference_date - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    if date_str == "tomorrow":
        return (reference_date + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    # Handle "last X" patterns
    if date_str == "last week":
        # Start of last week (Monday)
        days_since_monday = reference_date.weekday()
        start_of_this_week = reference_date - timedelta(days=days_since_monday)
        return (start_of_this_week - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)

    if date_str == "last month":
        # First day of last month
        first_of_month = reference_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month = first_of_month - timedelta(days=1)
        return last_month.replace(day=1)

    if date_str == "last year":
        return reference_date.replace(year=reference_date.year - 1, month=1, day=1,
                                       hour=0, minute=0, second=0, microsecond=0)

    # Handle "this X" patterns
    if date_str == "this week":
        days_since_monday = reference_date.weekday()
        return (reference_date - timedelta(days=days_since_monday)).replace(
            hour=0, minute=0, second=0, microsecond=0)

    if date_str == "this month":
        return reference_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if date_str == "this year":
        return reference_date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    # Handle "N units ago" patterns
    ago_pattern = r"(\d+)\s*(day|week|month|year)s?\s*ago"
    match = re.match(ago_pattern, date_str)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)

        if unit == "day":
            return (reference_date - timedelta(days=amount)).replace(
                hour=0, minute=0, second=0, microsecond=0)
        elif unit == "week":
            return (reference_date - timedelta(weeks=amount)).replace(
                hour=0, minute=0, second=0, microsecond=0)
        elif unit == "month":
            # Approximate months
            new_date = reference_date - timedelta(days=amount * 30)
            return new_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif unit == "year":
            return reference_date.replace(year=reference_date.year - amount,
                                          hour=0, minute=0, second=0, microsecond=0)

    # Handle "past N units" patterns
    past_pattern = r"(?:the\s+)?(?:past|last)\s+(\d+)\s*(day|week|month|year)s?"
    match = re.match(past_pattern, date_str)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)

        if unit == "day":
            return (reference_date - timedelta(days=amount)).replace(
                hour=0, minute=0, second=0, microsecond=0)
        elif unit == "week":
            return (reference_date - timedelta(weeks=amount)).replace(
                hour=0, minute=0, second=0, microsecond=0)
        elif unit == "month":
            new_date = reference_date - timedelta(days=amount * 30)
            return new_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif unit == "year":
            return reference_date.replace(year=reference_date.year - amount,
                                          hour=0, minute=0, second=0, microsecond=0)

    # Handle named months: "january", "january 2024", "jan 2024"
    month_names = {
        "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
        "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
        "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
        "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12
    }

    for month_name, month_num in month_names.items():
        if date_str.startswith(month_name):
            # Check for year
            year_match = re.search(r"(\d{4})", date_str)
            year = int(year_match.group(1)) if year_match else reference_date.year

            # Check for day
            day_match = re.search(r"\b(\d{1,2})\b(?!\d)", date_str.replace(str(year) if year_match else "", ""))
            day = int(day_match.group(1)) if day_match else 1

            try:
                return datetime(year, month_num, day)
            except ValueError:
                return datetime(year, month_num, 1)

    # Handle standard date formats
    date_formats = [
        "%Y-%m-%d",           # 2024-01-15
        "%m/%d/%Y",           # 01/15/2024
        "%m-%d-%Y",           # 01-15-2024
        "%d/%m/%Y",           # 15/01/2024
        "%B %d, %Y",          # January 15, 2024
        "%b %d, %Y",          # Jan 15, 2024
        "%B %d %Y",           # January 15 2024
        "%Y/%m/%d",           # 2024/01/15
    ]

    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    logger.warning(f"Could not parse date string: {date_str}")
    return None


def get_end_date_for_period(
    start_date: datetime,
    period_str: str,
    reference_date: Optional[datetime] = None
) -> datetime:
    """
    Get the end date for a given period starting from start_date.

    Args:
        start_date: Start of the period
        period_str: Period description ("week", "month", "year", or specific date)
        reference_date: Reference date for relative calculations

    Returns:
        End datetime for the period
    """
    period_str = period_str.lower().strip()

    # Period-based queries that span multiple days
    if period_str in ("week", "this week", "last week"):
        return start_date + timedelta(days=7) - timedelta(seconds=1)

    if period_str in ("month", "this month", "last month"):
        # End of the month
        if start_date.month == 12:
            return datetime(start_date.year + 1, 1, 1) - timedelta(seconds=1)
        else:
            return datetime(start_date.year, start_date.month + 1, 1) - timedelta(seconds=1)

    if period_str in ("year", "this year", "last year"):
        return datetime(start_date.year + 1, 1, 1) - timedelta(seconds=1)

    # Handle "past/last N units" patterns (e.g., "last 7 days", "past 2 weeks")
    past_pattern = r"(?:the\s+)?(?:past|last)\s+(\d+)\s*(day|week|month|year)s?"
    match = re.match(past_pattern, period_str)
    if match:
        # For "last N days/weeks", end is the reference date (or end of start_date's day)
        return start_date.replace(hour=23, minute=59, second=59) + timedelta(
            days=int(match.group(1)) * (7 if match.group(2) == "week" else 1)
            if match.group(2) in ("day", "week") else 0
        ) - timedelta(seconds=1)

    # Point-in-time queries (yesterday, today, N days ago) - end is same day
    if period_str in ("today", "yesterday", "tomorrow"):
        return start_date.replace(hour=23, minute=59, second=59)

    # "N units ago" patterns - these are single days
    ago_pattern = r"(\d+)\s*(day|week|month|year)s?\s*ago"
    if re.match(ago_pattern, period_str):
        return start_date.replace(hour=23, minute=59, second=59)

    # Default to end of start_date's day
    return start_date.replace(hour=23, minute=59, second=59)


def parse_date_range(
    start_str: Optional[str] = None,
    end_str: Optional[str] = None,
    reference_date: Optional[datetime] = None
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Parse start and end date strings into a date range.

    Args:
        start_str: Start date string (natural language or specific)
        end_str: End date string (natural language or specific, default: today)
        reference_date: Reference date for relative calculations

    Returns:
        Tuple of (start_datetime, end_datetime)
    """
    if reference_date is None:
        reference_date = datetime.now()

    start_date = None
    end_date = None

    # Parse start date
    if start_str:
        start_date = parse_natural_date(start_str, reference_date)

    # Parse end date
    if end_str:
        end_date = parse_natural_date(end_str, reference_date)
        if end_date:
            # Make end date inclusive (end of day)
            end_date = end_date.replace(hour=23, minute=59, second=59)
    else:
        # Default end to now
        end_date = reference_date

    # If only relative period given (like "last week"), calculate end automatically
    if start_str and not end_str:
        end_date = get_end_date_for_period(start_date, start_str, reference_date) if start_date else reference_date

    return start_date, end_date
