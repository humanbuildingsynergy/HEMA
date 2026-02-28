# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.

"""
Unified response formatting utilities for analysis tools.

This module consolidates response formatting logic that was previously duplicated
across multiple analysis tool modules (consumption_tools, frequency_tools, solar_tools,
aggregation_tools, query_tools, etc.).

Instead of each tool implementing its own _format_*() functions, they now use
the ResponseBuilder class for consistent, maintainable formatting.

Example:
    >>> builder = ResponseBuilder("Appliance Energy Analysis", "Jan 1 - Dec 31, 2024")
    >>> response = (builder
    ...     .add_header("Jan 1 - Dec 31, 2024")
    ...     .add_summary({"Total": "500 kWh", "Average": "1.4 kWh/day"})
    ...     .add_section("Top Appliances", "1. AC: 200 kWh\\n2. Water Heater: 100 kWh")
    ...     .add_insights(["AC is the biggest consumer", "Usage is seasonal"])
    ...     .build())
"""

from typing import Any, Dict, List, Optional


class ResponseBuilder:
    """Builder class for consistent response formatting across analysis tools.

    This class provides a fluent API for building formatted analysis responses
    with sections, headers, metrics, tables, and insights.

    Attributes:
        title: Main title of the analysis
        scope: Data scope/period being analyzed
    """

    def __init__(self, title: str, scope: str = ""):
        """Initialize response builder.

        Args:
            title: Main title for the analysis (e.g., "Appliance Energy Analysis")
            scope: Optional data scope/period (e.g., "Jan 1 - Dec 31, 2024")
        """
        self.title = title
        self.scope = scope
        self.sections = []
        self._include_header = True

    def set_title(self, title: str) -> "ResponseBuilder":
        """Set the main title.

        Args:
            title: Title text

        Returns:
            Self for chaining
        """
        self.title = title
        return self

    def add_header(self, data_range: str = "") -> "ResponseBuilder":
        """Add data period header section.

        Args:
            data_range: Data range string (e.g., "Jan 1 - Dec 31, 2024")

        Returns:
            Self for chaining
        """
        if not data_range and self.scope:
            data_range = self.scope
        if data_range:
            self.sections.append(f"**Data Period**: {data_range}")
        return self

    def add_summary(self, metrics: Dict[str, Any]) -> "ResponseBuilder":
        """Add summary section with key metrics.

        Args:
            metrics: Dictionary of metric_name -> value

        Returns:
            Self for chaining

        Example:
            >>> builder.add_summary({
            ...     "Total Usage": "500 kWh",
            ...     "Average Daily": "1.37 kWh",
            ...     "Peak": "3.2 kWh"
            ... })
        """
        if not metrics:
            return self

        self.sections.append("### Summary")
        for key, value in metrics.items():
            self.sections.append(f"- **{key}**: {value}")
        return self

    def add_section(self, title: str, content: str) -> "ResponseBuilder":
        """Add a generic section with title and content.

        Args:
            title: Section title
            content: Section content (can include markdown)

        Returns:
            Self for chaining

        Example:
            >>> builder.add_section("Details", "- Point 1\\n- Point 2")
        """
        if not content:
            return self

        self.sections.append(f"### {title}")
        self.sections.append(content)
        return self

    def add_metrics_table(
        self, title: str, headers: List[str], rows: List[List[str]]
    ) -> "ResponseBuilder":
        """Add a formatted markdown table for metrics.

        Args:
            title: Table title
            headers: Column headers
            rows: List of rows, each row is a list of strings

        Returns:
            Self for chaining

        Example:
            >>> builder.add_metrics_table(
            ...     "Appliance Breakdown",
            ...     ["Appliance", "Usage (kWh)", "Percentage"],
            ...     [
            ...         ["AC", "200", "40%"],
            ...         ["Water Heater", "100", "20%"],
            ...     ]
            ... )
        """
        if not headers or not rows:
            return self

        self.sections.append(f"### {title}")

        # Build markdown table
        table = "| " + " | ".join(headers) + " |\n"
        table += "| " + " | ".join(["---"] * len(headers)) + " |\n"
        for row in rows:
            table += "| " + " | ".join(str(cell) for cell in row) + " |\n"

        self.sections.append(table.rstrip())
        return self

    def add_insights(self, insights: List[str]) -> "ResponseBuilder":
        """Add insights section with bullet points.

        Args:
            insights: List of insight strings

        Returns:
            Self for chaining

        Example:
            >>> builder.add_insights([
            ...     "AC is the largest energy consumer at 40% of total",
            ...     "Usage peaks in summer months",
            ...     "Water heater has 24-hour cycle"
            ... ])
        """
        if not insights:
            return self

        self.sections.append("### Insights")
        for insight in insights:
            self.sections.append(f"- {insight}")
        return self

    def add_recommendations(self, recommendations: List[str]) -> "ResponseBuilder":
        """Add recommendations section with actionable items.

        Args:
            recommendations: List of recommendation strings

        Returns:
            Self for chaining

        Example:
            >>> builder.add_recommendations([
            ...     "Raise thermostat by 2-3°F in summer to reduce AC usage",
            ...     "Check water heater temperature settings",
            ... ])
        """
        if not recommendations:
            return self

        self.sections.append("### Recommendations")
        for rec in recommendations:
            self.sections.append(f"- {rec}")
        return self

    def add_custom(self, content: str) -> "ResponseBuilder":
        """Add custom markdown content.

        Args:
            content: Raw markdown content

        Returns:
            Self for chaining
        """
        if content:
            self.sections.append(content)
        return self

    def build(self) -> str:
        """Build the final formatted response string.

        Returns:
            Complete formatted response as string

        Example:
            >>> response = builder.build()
            >>> print(response)  # Ready to send to user
        """
        if not self.title and not self.sections:
            return ""

        # Build main header
        result = f"## {self.title}\n\n"

        # Add all sections
        if self.sections:
            result += "\n\n".join(self.sections)

        return result

    def build_subsection(self) -> str:
        """Build response without main title (for subsections).

        Useful when response is part of a larger context.

        Returns:
            Formatted content without main header
        """
        if not self.sections:
            return ""
        return "\n\n".join(self.sections)


# Utility functions for common formatting patterns

def format_value_with_unit(value: float, key: str) -> str:
    """Format a value with appropriate unit based on key name.

    Args:
        value: Numeric value to format
        key: Key name to infer unit from

    Returns:
        Formatted string with unit

    Example:
        >>> format_value_with_unit(72.5, "temperature_f")
        '72.5°F'
        >>> format_value_with_unit(1234.56, "kw_usage")
        '1234.56 kW'
    """
    key_lower = key.lower()

    if "percent" in key_lower or "%" in key_lower:
        return f"{value:.1f}%"
    elif "temp" in key_lower or "fahrenheit" in key_lower or "_f" in key_lower:
        return f"{value:.1f}°F"
    elif "celsius" in key_lower or "_c" in key_lower:
        return f"{value:.1f}°C"
    elif "kw" in key_lower or "kilowatt" in key_lower:
        return f"{value:.2f} kW"
    elif "kwh" in key_lower or "kilowatt-hour" in key_lower:
        return f"{value:.2f} kWh"
    elif "watt" in key_lower and "hour" not in key_lower:
        return f"{value:.0f} W"
    elif "cost" in key_lower or "price" in key_lower or "rate" in key_lower:
        return f"${value:.2f}"
    elif "hour" in key_lower or "time" in key_lower:
        return f"{int(value)}h" if value == int(value) else f"{value:.1f}h"
    else:
        # Default: 2 decimal places for generic numeric values
        return f"{value:.2f}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format a decimal as percentage.

    Args:
        value: Decimal value (0-1 or 0-100)
        decimals: Number of decimal places

    Returns:
        Formatted percentage string

    Example:
        >>> format_percentage(0.4567)
        '45.7%'
    """
    if value <= 1:
        value = value * 100
    return f"{value:.{decimals}f}%"


def format_date_range(start_date, end_date) -> str:
    """Format a date range string.

    Args:
        start_date: Start date (datetime or string)
        end_date: End date (datetime or string)

    Returns:
        Formatted date range

    Example:
        >>> format_date_range(datetime(2024, 1, 1), datetime(2024, 12, 31))
        'Jan 1 - Dec 31, 2024'
    """
    from datetime import datetime

    # Handle string inputs
    if isinstance(start_date, str):
        start_date = datetime.fromisoformat(start_date.split()[0])
    if isinstance(end_date, str):
        end_date = datetime.fromisoformat(end_date.split()[0])

    # Same year?
    if start_date.year == end_date.year:
        return f"{start_date.strftime('%b %-d')} - {end_date.strftime('%b %-d, %Y')}"
    else:
        return f"{start_date.strftime('%b %-d, %Y')} - {end_date.strftime('%b %-d, %Y')}"
