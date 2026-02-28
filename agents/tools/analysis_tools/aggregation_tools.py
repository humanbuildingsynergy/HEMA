# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/tools/analysis_tools/aggregation_tools.py
"""Unified flexible aggregation tool for energy data analysis.

This tool replaces the old aggregation_tools.py with a single, parameterized
function that can handle any time period and aggregation level.
"""
from typing import Optional
from langchain_core.tools import tool
from utils.logger import setup_logger
from .cache import _data_cache

logger = setup_logger()


@tool
def analyze_energy_period(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    aggregation: str = "daily",
    appliances: Optional[str] = None,
    include_breakdown: bool = False,
    day_filter: Optional[str] = None,
    hour_range: Optional[str] = None,
) -> str:
    """
    Analyze energy consumption for any time period with flexible aggregation.

    This is the primary tool for ALL energy aggregation and period-based analysis.
    Use it for questions like:
    - "What was my usage yesterday?" (start_date="yesterday", aggregation="hourly")
    - "Show me last week's consumption" (start_date="last week", aggregation="daily")
    - "Give me a weekly breakdown" (aggregation="weekly")
    - "Compare my seasonal usage" (aggregation="seasonal")
    - "What's my usage on weekdays vs weekends?" (day_filter="weekday" or "weekend")
    - "Show morning usage patterns" (hour_range="6-12")

    Args:
        start_date: Start date - can be:
                   - Specific date: "2024-01-15", "July 3", "2018-07-01"
                   - Relative: "yesterday", "last week", "last month"
                   - None: Use all available data
        end_date: End date (same formats as start_date). If not provided with
                 relative start_date, will be auto-calculated.
        aggregation: How to group the data:
                    - "raw" or "15min": Raw 15-minute intervals
                    - "hourly": Hourly totals (24 data points per day)
                    - "daily": Daily totals
                    - "weekly": Weekly totals with best/worst week
                    - "monthly": Monthly totals with best/worst month
                    - "seasonal": Seasonal totals (winter/spring/summer/fall)
        appliances: Comma-separated list of appliance names (e.g., "HVAC unit,Refrigerator").
                   If not provided, includes all appliances.
        include_breakdown: Include per-appliance breakdown in results (default: False)
        day_filter: Filter by day type:
                   - "weekday": Monday-Friday only
                   - "weekend": Saturday-Sunday only
                   - Specific day: "monday", "tuesday", etc.
        hour_range: Filter by hours of day (e.g., "6-12" for morning, "14-20" for peak hours)

    Returns:
        Formatted analysis results with statistics, data, and insights.
    """
    from core.analysis.flexible_query import FlexibleQueryEngine

    logger.info(f"analyze_energy_period: aggregation={aggregation}, start={start_date}, "
                f"end={end_date}, appliances={appliances}, breakdown={include_breakdown}, "
                f"day_filter={day_filter}, hour_range={hour_range}")

    if _data_cache["energy_df"] is None:
        return "Error: No data loaded. Please use load_energy_data first."

    try:
        # Parse appliances string into list
        appliance_list = None
        if appliances:
            appliance_list = [a.strip() for a in appliances.split(",")]

        # Parse hour_range string into tuple
        hour_tuple = None
        if hour_range:
            parts = hour_range.replace(" ", "").split("-")
            if len(parts) == 2:
                hour_tuple = (int(parts[0]), int(parts[1]))

        # Create engine
        engine = FlexibleQueryEngine(
            _data_cache["energy_df"],
            _data_cache.get("rate_df")
        )

        # Execute query
        result = engine.query(
            start_date=start_date,
            end_date=end_date,
            aggregation=aggregation,
            appliances=appliance_list,
            day_filter=day_filter,
            hour_range=hour_tuple,
            include_breakdown=include_breakdown,
        )

        if not result.get("success", False):
            return f"Error: {result.get('error', 'Unknown error')}"

        return _format_result(result, aggregation)

    except Exception as e:
        logger.error(f"Error in analyze_energy_period: {str(e)}")
        return f"Error analyzing energy period: {str(e)}"


@tool
def calculate_rolling_average(
    window_days: int = 7,
    appliances: Optional[str] = None,
) -> str:
    """
    Calculate rolling average consumption with trend analysis.

    Use this for questions like:
    - "What's my 7-day rolling average?"
    - "Is my energy usage trending up or down?"
    - "Show my 30-day consumption trend"

    Args:
        window_days: Rolling window size in days (common: 7 for weekly, 30 for monthly)
        appliances: Comma-separated list of appliance names (None = all)

    Returns:
        Rolling average statistics and trend analysis.
    """
    from core.analysis.flexible_query import FlexibleQueryEngine

    logger.info(f"calculate_rolling_average: window={window_days}, appliances={appliances}")

    if _data_cache["energy_df"] is None:
        return "Error: No data loaded. Please use load_energy_data first."

    try:
        appliance_list = None
        if appliances:
            appliance_list = [a.strip() for a in appliances.split(",")]

        engine = FlexibleQueryEngine(_data_cache["energy_df"])
        result = engine.calculate_rolling_average(
            window_days=window_days,
            appliances=appliance_list,
        )

        if not result.get("success", False):
            return f"Error: {result.get('error', 'Unknown error')}"

        return _format_rolling_result(result)

    except Exception as e:
        logger.error(f"Error in calculate_rolling_average: {str(e)}")
        return f"Error calculating rolling average: {str(e)}"


@tool
def compare_weekday_weekend(
    appliances: Optional[str] = None,
) -> str:
    """
    Compare weekday vs weekend energy consumption patterns.

    Use this for questions like:
    - "How does my weekend usage compare to weekdays?"
    - "Do I use more energy on weekdays or weekends?"

    Args:
        appliances: Comma-separated list of appliance names (None = all)

    Returns:
        Weekday vs weekend comparison with daily averages and patterns.
    """
    from core.analysis.flexible_query import FlexibleQueryEngine

    logger.info(f"compare_weekday_weekend: appliances={appliances}")

    if _data_cache["energy_df"] is None:
        return "Error: No data loaded. Please use load_energy_data first."

    try:
        appliance_list = None
        if appliances:
            appliance_list = [a.strip() for a in appliances.split(",")]

        engine = FlexibleQueryEngine(_data_cache["energy_df"])
        result = engine.compare_weekday_weekend(appliances=appliance_list)

        if not result.get("success", False):
            return f"Error: {result.get('error', 'Unknown error')}"

        return _format_weekday_weekend_result(result)

    except Exception as e:
        logger.error(f"Error in compare_weekday_weekend: {str(e)}")
        return f"Error comparing weekday/weekend: {str(e)}"


@tool
def analyze_peak_hours(
    peak_start: int = 14,
    peak_end: int = 20,
    appliances: Optional[str] = None,
) -> str:
    """
    Analyze peak vs off-peak energy consumption with savings estimates.

    Use this for questions like:
    - "How much energy do I use during peak hours?"
    - "What percentage of my usage is during peak time?"
    - "Should I shift my usage to off-peak hours?"
    - "Which appliances use the most energy during peak hours?"
    - "How much could I save by shifting usage to off-peak?"

    Args:
        peak_start: Start hour of peak period (default: 14 / 2 PM)
        peak_end: End hour of peak period (default: 20 / 8 PM)
        appliances: Comma-separated list of appliance names (None = all)

    Returns:
        Peak hours analysis with:
        - Total peak/off-peak consumption
        - Per-appliance peak breakdown (top 5 consumers)
        - Savings estimates for load shifting (based on TOU rates)
    """
    from core.analysis.flexible_query import FlexibleQueryEngine

    logger.info(f"analyze_peak_hours: peak={peak_start}-{peak_end}, appliances={appliances}")

    if _data_cache["energy_df"] is None:
        return "Error: No data loaded. Please use load_energy_data first."

    try:
        appliance_list = None
        if appliances:
            appliance_list = [a.strip() for a in appliances.split(",")]

        # Pass rate_df for savings calculation
        engine = FlexibleQueryEngine(
            _data_cache["energy_df"],
            rate_df=_data_cache.get("rate_df")
        )
        result = engine.analyze_peak_hours(
            peak_start=peak_start,
            peak_end=peak_end,
            appliances=appliance_list,
            include_savings=True,
            top_n_appliances=5,
        )

        if not result.get("success", False):
            return f"Error: {result.get('error', 'Unknown error')}"

        return _format_peak_hours_result(result)

    except Exception as e:
        logger.error(f"Error in analyze_peak_hours: {str(e)}")
        return f"Error analyzing peak hours: {str(e)}"


# =============================================================================
# Formatting Functions
# =============================================================================

def _format_result(result: dict, aggregation: str) -> str:
    """Format query result based on aggregation level."""
    stats = result.get("statistics", {})
    agg_data = result.get("aggregated_data", {})
    records = agg_data.get("records", [])
    query_params = result.get("query_params", {})

    # Build header
    agg_labels = {
        "raw": "Raw 15-Minute",
        "15min": "Raw 15-Minute",
        "hourly": "Hourly",
        "daily": "Daily",
        "weekly": "Weekly",
        "monthly": "Monthly",
        "seasonal": "Seasonal",
    }
    header = f"## {agg_labels.get(aggregation, aggregation.capitalize())} Energy Analysis\n"

    # Query context
    context_parts = []
    if query_params.get("start_date") != "data start":
        context_parts.append(f"From: {query_params.get('start_date')}")
    if query_params.get("end_date") != "data end":
        context_parts.append(f"To: {query_params.get('end_date')}")
    if query_params.get("day_filter"):
        context_parts.append(f"Days: {query_params.get('day_filter')}")
    if query_params.get("hour_range"):
        context_parts.append(f"Hours: {query_params.get('hour_range')[0]}-{query_params.get('hour_range')[1]}")

    if context_parts:
        header += f"*{' | '.join(context_parts)}*\n\n"

    # Summary statistics
    response = header + f"""### Summary Statistics
- **Total consumption:** {stats.get('total_consumption_kwh', 0):.2f} kWh
- **Average daily consumption:** {stats.get('average_daily_kwh', 0):.2f} kWh/day
- **Peak power:** {stats.get('peak_power_kw', 0):.3f} kW
- **Days analyzed:** {stats.get('num_days', 0)}
"""

    # Best/worst periods (if available)
    best_worst = result.get("best_worst", {})
    if best_worst:
        best = best_worst.get("best_period", {})
        worst = best_worst.get("worst_period", {})
        period_label = aggregation.replace("ly", "")  # weekly -> week
        response += f"""
### Best & Worst {period_label.capitalize()}s
- **Best {period_label}:** {best.get('period', 'N/A')} ({best.get('total_kwh', 0):.2f} kWh, {best.get('daily_avg_kwh', 0):.2f} kWh/day)
- **Worst {period_label}:** {worst.get('period', 'N/A')} ({worst.get('total_kwh', 0):.2f} kWh, {worst.get('daily_avg_kwh', 0):.2f} kWh/day)
"""

    # Data records
    response += f"\n### {agg_labels.get(aggregation, aggregation.capitalize())} Data\n"

    # Format based on aggregation level
    if aggregation in ["raw", "15min"]:
        # Show limited raw data
        for rec in records[:20]:
            ts = rec.get("local_15min", "")
            kwh = rec.get("total_kwh", 0)
            response += f"- {ts}: {kwh:.3f} kWh\n"
        if len(records) > 20:
            response += f"*... and {len(records) - 20} more intervals*\n"

    elif aggregation == "hourly":
        for rec in records[:24]:
            hour = rec.get("agg_key", "")
            kwh = rec.get("total_kwh", 0)
            response += f"- {hour}: {kwh:.2f} kWh\n"
        if len(records) > 24:
            response += f"*... and {len(records) - 24} more hours*\n"

    elif aggregation == "daily":
        for rec in records[-14:]:  # Show last 14 days
            date = rec.get("date", "")
            kwh = rec.get("total_kwh", 0)
            avg = rec.get("daily_avg_kwh", kwh)
            response += f"- {date}: {kwh:.2f} kWh\n"
        if len(records) > 14:
            response += f"*... and {len(records) - 14} more days*\n"

    elif aggregation == "weekly":
        for rec in records[-8:]:  # Show last 8 weeks
            week = rec.get("year_week", "")
            kwh = rec.get("total_kwh", 0)
            avg = rec.get("daily_avg_kwh", 0)
            days = rec.get("days", 7)
            response += f"- {week}: {kwh:.2f} kWh total, {avg:.2f} kWh/day ({days} days)\n"

    elif aggregation == "monthly":
        for rec in records:
            month = rec.get("year_month", "")
            kwh = rec.get("total_kwh", 0)
            avg = rec.get("daily_avg_kwh", 0)
            days = rec.get("days", 30)
            response += f"- {month}: {kwh:.2f} kWh ({avg:.2f} kWh/day, {days} days)\n"

    elif aggregation == "seasonal":
        for rec in records:
            season = rec.get("season", "")
            kwh = rec.get("total_kwh", 0)
            avg = rec.get("daily_avg_kwh", 0)
            days = rec.get("days", 0)
            response += f"- **{season.capitalize()}:** {kwh:.2f} kWh ({avg:.2f} kWh/day, {days} days)\n"

    # Appliance breakdown (if included)
    breakdown = result.get("appliance_breakdown", {})
    if breakdown:
        response += "\n### Appliance Breakdown\n"
        for appliance, data in list(breakdown.items())[:10]:  # Top 10
            kwh = data.get("total_kwh", 0)
            pct = data.get("percentage", 0)
            response += f"- **{appliance}:** {kwh:.2f} kWh ({pct:.1f}%)\n"

    return response


def _format_rolling_result(result: dict) -> str:
    """Format rolling average result."""
    stats = result.get("statistics", {})

    trend_emoji = {
        "increasing": "📈",
        "decreasing": "📉",
        "stable": "➡️",
    }.get(stats.get("trend", ""), "")

    response = f"""## Rolling Average Analysis ({stats.get('window_days', 7)}-Day Window)

### Statistics
- **Current rolling average:** {stats.get('current_rolling_avg', 0):.2f} kWh/day
- **Minimum rolling average:** {stats.get('min_rolling_avg', 0):.2f} kWh/day
- **Maximum rolling average:** {stats.get('max_rolling_avg', 0):.2f} kWh/day
- **Overall daily average:** {stats.get('overall_daily_avg', 0):.2f} kWh/day
- **Days analyzed:** {stats.get('num_days', 0)}
"""

    if stats.get("trend") != "insufficient_data":
        response += f"""
### Trend Analysis
- **Trend:** {trend_emoji} {stats.get('trend', 'N/A').capitalize()}
- **Change:** {stats.get('trend_pct_change', 0):+.1f}%
"""
    else:
        response += "\n### Trend Analysis\nInsufficient data for trend detection.\n"

    return response


def _format_weekday_weekend_result(result: dict) -> str:
    """Format weekday/weekend comparison result."""
    weekday = result.get("weekday", {})
    weekend = result.get("weekend", {})
    comp = result.get("comparison", {})

    higher_emoji = "📈" if comp.get("higher_on") == "weekend" else "📉" if comp.get("higher_on") == "weekday" else "➡️"

    return f"""## Weekday vs Weekend Comparison

### Weekday Usage (Mon-Fri)
- **Total consumption:** {weekday.get('total_kwh', 0):.2f} kWh
- **Average daily:** {weekday.get('avg_daily_kwh', 0):.2f} kWh
- **Days analyzed:** {weekday.get('num_days', 0)}
- **Peak power:** {weekday.get('peak_kw', 0):.3f} kW

### Weekend Usage (Sat-Sun)
- **Total consumption:** {weekend.get('total_kwh', 0):.2f} kWh
- **Average daily:** {weekend.get('avg_daily_kwh', 0):.2f} kWh
- **Days analyzed:** {weekend.get('num_days', 0)}
- **Peak power:** {weekend.get('peak_kw', 0):.3f} kW

### Comparison
- **Difference:** {higher_emoji} {abs(comp.get('difference_kwh', 0)):.2f} kWh/day ({abs(comp.get('difference_pct', 0)):.1f}%)
- **Higher on:** {comp.get('higher_on', 'N/A').capitalize()}s
"""


def _format_peak_hours_result(result: dict) -> str:
    """Format peak hours analysis result."""
    cons = result.get("consumption", {})
    intensity = result.get("intensity", {})
    num_days = result.get("num_days", 0)

    response = f"""## Peak Hours Analysis ({num_days}-Day Period)

### Time Periods
- **Peak period:** {result.get('peak_period', 'N/A')} ({result.get('peak_hours_per_day', 0)} hours/day)
- **Off-peak:** All other hours ({result.get('off_peak_hours_per_day', 0)} hours/day)
- **Analysis period:** {num_days} days

### Total Consumption (over {num_days} days)
- **Peak consumption:** {cons.get('peak_kwh', 0):.2f} kWh ({cons.get('peak_pct', 0):.1f}% of total)
- **Off-peak consumption:** {cons.get('off_peak_kwh', 0):.2f} kWh ({cons.get('off_peak_pct', 0):.1f}% of total)

### Intensity
- **Peak intensity:** {intensity.get('peak_kwh_per_hour', 0):.3f} kWh/hour
- **Off-peak intensity:** {intensity.get('off_peak_kwh_per_hour', 0):.3f} kWh/hour
- **Intensity ratio:** {intensity.get('ratio', 0):.2f}x
"""

    # Add per-appliance breakdown (single percentage column to avoid LLM confusion)
    appliance_breakdown = result.get("appliance_breakdown", [])
    if appliance_breakdown:
        response += f"\n### Top Peak Consumers by Appliance (over {num_days} days)\n"
        response += "| Appliance | Peak kWh | Off-Peak kWh | Total kWh | Share of Total Peak |\n"
        response += "|-----------|----------|--------------|-----------|--------------------|\n"
        for app in appliance_breakdown:
            response += (
                f"| {app['appliance']} | {app['peak_kwh']:.1f} | {app['off_peak_kwh']:.1f} | "
                f"{app['total_kwh']:.1f} | {app['contribution_to_total_peak']:.0f}% |\n"
            )

    # Add savings information
    savings = result.get("savings")
    if savings:
        response += f"""
### Potential Savings from Load Shifting
- **Peak rate:** {savings['peak_rate_cents_per_kwh']:.2f} ¢/kWh
- **Off-peak rate:** {savings['off_peak_rate_cents_per_kwh']:.2f} ¢/kWh
- **Rate difference:** {savings['rate_difference_cents']:.2f} ¢/kWh
- **Max savings (if all peak shifted):** ${savings['max_savings_if_all_shifted_dollars']:.2f} over {num_days} days

#### Per-Appliance Savings Potential
"""
        # Build a lookup for daily/monthly estimates from appliance_breakdown
        app_estimates = {}
        for app in appliance_breakdown:
            app_estimates[app['appliance']] = app

        for app_savings in savings.get("per_appliance_savings", []):
            app_name = app_savings['appliance']
            est = app_estimates.get(app_name, {})
            daily_note = f" ({est['daily_avg_kwh']:.1f} kWh/day, est. {est['estimated_monthly_kwh']:.0f} kWh/month)" if 'daily_avg_kwh' in est else ""
            response += (
                f"- **{app_name}:** Shift {app_savings['shiftable_peak_kwh']:.1f} kWh "
                f"→ save ${app_savings['potential_savings_dollars']:.2f}{daily_note}\n"
            )
        response += f"\n*Note: {savings.get('note', '')}*\n"

    # Add insights
    insights = result.get("insights", [])
    if insights:
        response += "\n### Insights\n"
        for insight in insights:
            response += f"- {insight}\n"

    return response
