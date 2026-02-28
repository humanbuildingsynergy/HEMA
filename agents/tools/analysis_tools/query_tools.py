# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/tools/analysis_tools/query_tools.py
"""Flexible query and period comparison tools."""
from typing import Optional
from langchain_core.tools import tool
from utils.logger import setup_logger
from .cache import _data_cache

logger = setup_logger()


def _get_data_boundaries_info() -> str:
    """Get a brief summary of available data boundaries for error messages."""
    import pandas as pd

    if _data_cache["energy_df"] is None:
        return "No data is currently loaded."

    energy_df = _data_cache["energy_df"]
    date_col = 'local_15min' if 'local_15min' in energy_df.columns else energy_df.columns[0]
    dates = pd.to_datetime(energy_df[date_col])

    start_date = dates.min()
    end_date = dates.max()
    years = dates.dt.year.unique().tolist()
    months = [str(m) for m in sorted(dates.dt.to_period('M').unique())]

    info = f"""**Available Data:**
- Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}
- Years covered: {', '.join(map(str, sorted(years)))}
- Available months: {', '.join(months)}"""

    if len(years) == 1:
        info += f"""

**Important:** This dataset only contains data from {years[0]}. Year-over-year comparisons are NOT possible.
You can compare different months, weeks, or days within this range."""

    return info


@tool
def query_energy_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    aggregation: str = "daily",
    appliances: Optional[str] = None,
    day_filter: Optional[str] = None,
    hour_start: Optional[int] = None,
    hour_end: Optional[int] = None,
) -> str:
    """
    Query energy data with flexible time ranges and filters.

    This tool allows you to query energy consumption for any time period,
    specific appliances, and with various filters. Use this for questions like:
    - "What was my energy use last week?"
    - "Show my HVAC consumption in January"
    - "What's my weekend vs weekday usage?"
    - "How much energy did I use in the mornings?"

    Args:
        start_date: Start date - supports natural language like "last week", "yesterday",
                   "January 2024", "3 days ago", or specific dates like "2024-01-15"
        end_date: End date - same format as start_date. If not provided, uses today.
        aggregation: How to aggregate the data. Options:
                    - "15min": Raw 15-minute intervals
                    - "hourly": Aggregate by hour
                    - "daily": Aggregate by day (default)
                    - "weekly": Aggregate by week
                    - "monthly": Aggregate by month
        appliances: Comma-separated list of appliance names to include (e.g., "HVAC unit,Refrigerator").
                   If not provided, includes all appliances.
        day_filter: Filter by day type. Options:
                   - "weekday": Monday through Friday only
                   - "weekend": Saturday and Sunday only
                   - "monday", "tuesday", etc.: Specific day of week
        hour_start: Start hour (0-23) for time-of-day filtering
        hour_end: End hour (0-23) for time-of-day filtering

    Returns:
        Energy consumption statistics and data for the specified query.
    """
    from core.analysis.flexible_query import FlexibleQueryEngine

    logger.info(f"Flexible query: start={start_date}, end={end_date}, agg={aggregation}, "
                f"appliances={appliances}, day_filter={day_filter}, hours={hour_start}-{hour_end}")

    if _data_cache["energy_df"] is None:
        return "Error: No data loaded. Please use load_energy_data first."

    try:
        # Parse appliances string into list
        appliance_list = None
        if appliances:
            appliance_list = [a.strip() for a in appliances.split(",")]

        # Parse hour range
        hour_range = None
        if hour_start is not None and hour_end is not None:
            hour_range = (hour_start, hour_end)

        # Create query engine and execute
        engine = FlexibleQueryEngine(
            _data_cache["energy_df"],
            _data_cache.get("rate_df")
        )

        result = engine.query(
            start_date=start_date,
            end_date=end_date,
            aggregation=aggregation,
            appliances=appliance_list,
            day_filter=day_filter,
            hour_range=hour_range,
        )

        if not result.get("success"):
            error_msg = result.get('error', 'Query failed')
            boundaries_info = _get_data_boundaries_info()
            return f"""## Query Failed

**Error:** {error_msg}

The requested date range may not exist in the dataset.

{boundaries_info}

**Suggestions:**
- Try querying within the available date range shown above
- Use `list_available_data()` to see detailed data availability before querying"""

        # Format response
        stats = result["statistics"]
        params = result["query_params"]
        data_range = result["data_range"]

        response = f"""## Energy Query Results

### Query Parameters
- **Date range:** {params['start_date']} to {params['end_date']}
- **Actual data:** {data_range['actual_start'][:10]} to {data_range['actual_end'][:10]}
- **Aggregation:** {params['aggregation']}
- **Appliances:** {params['appliances']}
- **Day filter:** {params['day_filter'] or 'All days'}
- **Hour filter:** {f"{params['hour_range'][0]}:00 - {params['hour_range'][1]}:00" if params['hour_range'] else 'All hours'}

### Statistics
- **Total consumption:** {stats['total_consumption_kwh']:.2f} kWh
- **Average daily:** {stats['average_daily_kwh']:.2f} kWh
- **Average power:** {stats['average_power_kw']:.3f} kW
- **Peak power:** {stats['peak_power_kw']:.3f} kW
- **Days analyzed:** {stats['num_days']}
- **Data points:** {stats['num_intervals']}
"""

        # Add appliance breakdown if available
        if "appliance_breakdown" in result:
            response += "\n### Appliance Breakdown\n"
            for appliance, data in result["appliance_breakdown"].items():
                pct = data.get('percentage', 0)
                response += f"- **{appliance}:** {data['total_kwh']:.2f} kWh ({pct:.1f}%) - avg {data['average_kw']:.3f} kW, peak {data['peak_kw']:.3f} kW\n"

        # Add aggregated data preview
        agg_data = result["aggregated_data"]
        if agg_data["records"]:
            response += f"\n### {params['aggregation'].title()} Summary\n"
            response += f"- Total periods: {agg_data['periods']}\n"
            response += f"- Average per {params['aggregation']}: {agg_data['avg_per_period']:.2f} kWh\n"

        return response

    except Exception as e:
        logger.error(f"Error in flexible query: {str(e)}")
        return f"Error executing query: {str(e)}"


@tool
def compare_energy_periods(
    period1_start: str,
    period1_end: str,
    period2_start: str,
    period2_end: str,
    appliances: Optional[str] = None,
) -> str:
    """
    Compare energy consumption between two time periods.

    Use this tool for questions like:
    - "Compare my usage this month vs last month"
    - "How does my January usage compare to February?"
    - "Is my HVAC using more energy this week than last week?"
    - "Compare weekend usage between summer and winter"

    IMPORTANT: Before attempting period comparisons, especially year-over-year,
    use list_available_data() to verify both periods exist in the dataset.
    The dataset may only contain data from a limited time range.

    Args:
        period1_start: Start date of first period (e.g., "last month", "January 2024", "2024-01-01")
        period1_end: End date of first period
        period2_start: Start date of second period
        period2_end: End date of second period
        appliances: Comma-separated list of appliances to compare (optional)

    Returns:
        Comparison of energy metrics between the two periods with insights.
    """
    from core.analysis.period_comparison import PeriodComparisonEngine

    logger.info(f"Period comparison: {period1_start}-{period1_end} vs {period2_start}-{period2_end}")

    if _data_cache["energy_df"] is None:
        return "Error: No data loaded. Please use load_energy_data first."

    try:
        # Parse appliances string into list
        appliance_list = None
        if appliances:
            appliance_list = [a.strip() for a in appliances.split(",")]

        # Create comparison engine and execute
        engine = PeriodComparisonEngine(
            _data_cache["energy_df"],
            _data_cache.get("rate_df")
        )

        result = engine.compare(
            period1_start=period1_start,
            period1_end=period1_end,
            period2_start=period2_start,
            period2_end=period2_end,
            appliances=appliance_list,
        )

        if not result.get("success"):
            error_msg = result.get('error', 'Comparison failed')
            boundaries_info = _get_data_boundaries_info()

            # Build detailed error with period-specific info
            period_errors = []
            if result.get("period1_error"):
                period_errors.append(f"- Period 1 ({period1_start} to {period1_end}): {result['period1_error']}")
            if result.get("period2_error"):
                period_errors.append(f"- Period 2 ({period2_start} to {period2_end}): {result['period2_error']}")

            period_error_str = "\n".join(period_errors) if period_errors else ""

            return f"""## Comparison Failed

**Error:** {error_msg}

{period_error_str}

One or both of the requested time periods may not exist in the dataset.

{boundaries_info}

**Suggestions:**
- Ensure both periods fall within the available date range
- For year-over-year comparisons, verify the dataset contains multiple years
- Try comparing different months or weeks within the same year instead"""

        # Format response
        p1 = result["period1"]
        p2 = result["period2"]
        comp = result["comparison"]

        response = f"""## Period Comparison Results

### Period 1: {p1['start']} to {p1['end']}
- **Days:** {p1['days']}
- **Total consumption:** {p1['total_kwh']:.2f} kWh
- **Average daily:** {p1['avg_daily_kwh']:.2f} kWh
- **Peak power:** {p1['peak_kw']:.3f} kW

### Period 2: {p2['start']} to {p2['end']}
- **Days:** {p2['days']}
- **Total consumption:** {p2['total_kwh']:.2f} kWh
- **Average daily:** {p2['avg_daily_kwh']:.2f} kWh
- **Peak power:** {p2['peak_kw']:.3f} kW

### Comparison
"""
        # Total consumption change
        total = comp["total_consumption"]
        direction_symbol = "📈" if total["difference_kwh"] > 0 else "📉" if total["difference_kwh"] < 0 else "➡️"
        response += f"- **Total consumption:** {direction_symbol} {total['direction']} by {abs(total['percent_change']):.1f}% ({abs(total['difference_kwh']):.2f} kWh)\n"

        # Daily average change
        avg = comp["average_daily"]
        direction_symbol = "📈" if avg["difference_kwh"] > 0 else "📉" if avg["difference_kwh"] < 0 else "➡️"
        response += f"- **Daily average:** {direction_symbol} {avg['direction']} by {abs(avg['percent_change']):.1f}% ({abs(avg['difference_kwh']):.2f} kWh/day)\n"

        # Peak power change
        peak = comp["peak_power"]
        direction_symbol = "📈" if peak["difference_kw"] > 0 else "📉" if peak["difference_kw"] < 0 else "➡️"
        response += f"- **Peak power:** {direction_symbol} {peak['direction']} by {abs(peak['percent_change']):.1f}% ({abs(peak['difference_kw']):.3f} kW)\n"

        # Appliance comparison
        if "appliance_comparison" in result:
            response += "\n### Appliance Changes\n"
            for appliance, data in result["appliance_comparison"].items():
                direction_symbol = "📈" if data["difference_kwh"] > 0 else "📉" if data["difference_kwh"] < 0 else "➡️"
                response += f"- **{appliance}:** {direction_symbol} {data['period1_kwh']:.2f} → {data['period2_kwh']:.2f} kWh ({data['percent_change']:+.1f}%)\n"

        # Insights
        if result.get("insights"):
            response += "\n### Key Insights\n"
            for insight in result["insights"]:
                response += f"- {insight}\n"

        return response

    except Exception as e:
        logger.error(f"Error in period comparison: {str(e)}")
        return f"Error comparing periods: {str(e)}"
