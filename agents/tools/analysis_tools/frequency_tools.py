# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/tools/analysis_tools/frequency_tools.py
"""Usage frequency analysis tools."""
import os
from typing import Optional
from langchain_core.tools import tool
from config.config import DEFAULT_THRESHOLDS_FILE, DATA_DIR
from utils.logger import setup_logger
from .cache import _data_cache

# Use common utilities to reduce code duplication
from agents.tools.common import ResponseBuilder, parse_appliance_list

logger = setup_logger()


@tool
def analyze_usage_frequency(
    appliances: Optional[str] = None,
    num_days: Optional[int] = None,
    use_thresholds_file: bool = True,
) -> str:
    """
    Analyze appliance usage frequency patterns based on binary activity indicators.

    This tool calculates how frequently each appliance is actively used throughout
    the day, using threshold-based detection to distinguish active usage from
    standby/phantom loads.

    Use this tool for questions like:
    - "How often do I use my HVAC?"
    - "What are my appliance usage patterns?"
    - "Which appliances run the most throughout the day?"
    - "When are my appliances most active?"
    - "Show me the hourly usage frequency of my dishwasher"

    The analysis includes:
    1. **Hourly Usage Frequency**: For each hour, counts how many 15-min intervals
       the appliance was active (above threshold). Range: 0-4 per hour.
    2. **Normalized Average Hourly Frequency**: The hourly frequency averaged over
       the specified days, normalized to 0-1 range (1.0 = active all 4 intervals).

    Args:
        appliances: Comma-separated list of appliances to analyze (e.g., "HVAC unit,Refrigerator").
                   If not provided, analyzes top 5 appliances by consumption.
        num_days: Number of recent days to include in the analysis.
                 If not provided, uses all available days.
        use_thresholds_file: Whether to use appliance-specific thresholds from file (default True).
                            If False or no thresholds file exists, uses default 0.01 kW threshold.

    Returns:
        Detailed usage frequency analysis including hourly profiles, peak usage hours,
        and insights about usage patterns.
    """
    import pandas as pd
    from core.analysis.appliance_analyzer import ApplianceAnalyzer

    logger.info(f"Analyzing usage frequency: appliances={appliances}, num_days={num_days}")

    if _data_cache["energy_df"] is None:
        return "Error: No data loaded. Please use load_energy_data first."

    try:
        energy_df = _data_cache["energy_df"]

        # Use processed data if available
        if _data_cache["processed_df"] is not None:
            df = _data_cache["processed_df"]
        else:
            df = energy_df

        # Parse appliances string into list (uses common utility)
        appliance_list = parse_appliance_list(appliances)

        # Load thresholds from file if requested
        thresholds = {}
        if use_thresholds_file:
            thresholds = _load_appliance_thresholds()

        # Run usage frequency analysis
        analyzer = ApplianceAnalyzer()
        results = analyzer.analyze_usage_frequency(
            df=df,
            appliances=appliance_list,
            thresholds=thresholds if thresholds else None,
            num_days=num_days,
        )

        # Format response
        return _format_usage_frequency_result(results)

    except Exception as e:
        logger.error(f"Error analyzing usage frequency: {str(e)}")
        return f"Error analyzing usage frequency: {str(e)}"


def _load_appliance_thresholds() -> dict:
    """Load appliance thresholds from the thresholds file."""
    import pandas as pd

    try:
        # Try to find thresholds file based on loaded energy data
        thresholds_path = DEFAULT_THRESHOLDS_FILE
        energy_path = _data_cache.get("energy_path")

        if energy_path:
            import re
            match = re.search(r'(\d+)\.csv$', energy_path)
            if match:
                home_id = match.group(1)
                potential_path = os.path.join(DATA_DIR, "home_power", f"appliance_thresholds_{home_id}.csv")
                if os.path.exists(potential_path):
                    thresholds_path = potential_path

        if not os.path.exists(thresholds_path):
            logger.warning(f"Thresholds file not found: {thresholds_path}")
            return {}

        # Load thresholds
        thresholds_df = pd.read_csv(thresholds_path)
        thresholds = dict(zip(thresholds_df['appliance_name'], thresholds_df['threshold_kw']))
        logger.info(f"Loaded {len(thresholds)} appliance thresholds from {thresholds_path}")
        return thresholds

    except Exception as e:
        logger.warning(f"Error loading thresholds: {str(e)}")
        return {}


@tool
def analyze_usage_variability(
    appliances: Optional[str] = None,
    timeframe: str = "daily",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> str:
    """
    Analyze appliance usage variability using coefficient of variation (CV).

    This tool calculates how variable or consistent each appliance's usage is
    over time. CV = standard_deviation / mean, providing a normalized measure
    that allows comparison across appliances regardless of their consumption levels.

    Use this tool for questions like:
    - "Which appliances have the most variable usage?"
    - "How consistent is my HVAC usage day-to-day?"
    - "What appliances are flexible enough for demand response?"
    - "Show me weekly usage variability for my appliances"
    - "Which appliances have steady baseload vs sporadic usage?"

    Variability interpretation:
    - CV < 0.5: Low variability (consistent/predictable usage)
    - 0.5 <= CV < 1.0: Moderate variability
    - CV >= 1.0: High variability (flexible/sporadic usage)

    Args:
        appliances: Comma-separated list of appliances to analyze (e.g., "HVAC unit,Refrigerator").
                   If not provided, analyzes top 5 appliances by consumption.
        timeframe: Aggregation level for analysis. Options: "hourly", "daily", "weekly", "monthly".
                  Default is "daily".
        start_date: Optional start date filter in YYYY-MM-DD format.
        end_date: Optional end date filter in YYYY-MM-DD format.

    Returns:
        Detailed variability analysis including CV values, rankings by variability,
        and insights about load flexibility.
    """
    from core.analysis.appliance_analyzer import ApplianceAnalyzer

    logger.info(f"Analyzing usage variability: appliances={appliances}, timeframe={timeframe}")

    if _data_cache["energy_df"] is None:
        return "Error: No data loaded. Please use load_energy_data first."

    # Validate timeframe
    valid_timeframes = ["hourly", "daily", "weekly", "monthly"]
    if timeframe not in valid_timeframes:
        return f"Error: Invalid timeframe '{timeframe}'. Valid options: {', '.join(valid_timeframes)}"

    try:
        energy_df = _data_cache["energy_df"]

        # Use processed data if available
        if _data_cache["processed_df"] is not None:
            df = _data_cache["processed_df"]
        else:
            df = energy_df

        # Parse appliances string into list (uses common utility)
        appliance_list = parse_appliance_list(appliances)

        # Run usage variability analysis
        analyzer = ApplianceAnalyzer()
        results = analyzer.analyze_usage_variability(
            df=df,
            appliances=appliance_list,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
        )

        # Format response
        return _format_usage_variability_result(results)

    except Exception as e:
        logger.error(f"Error analyzing usage variability: {str(e)}")
        return f"Error analyzing usage variability: {str(e)}"


def _format_usage_variability_result(results: dict) -> str:
    """Format usage variability analysis results."""
    summary = results.get("summary", {})
    appliance_variability = results.get("appliance_variability", {})
    rankings = results.get("rankings", [])
    insights = results.get("insights", [])

    timeframe = summary.get("timeframe", "daily")
    date_range = summary.get("date_range", {})

    builder = ResponseBuilder(f"Usage Variability Analysis ({timeframe.capitalize()})")

    # Summary metrics
    summary_metrics = {
        "Appliances analyzed": summary.get('appliances_analyzed', 0),
        "Timeframe": timeframe,
        "Date range": f"{date_range.get('start', 'all')} to {date_range.get('end', 'all')}",
        "Most variable": summary.get('most_variable', 'N/A'),
        "Most consistent": summary.get('most_consistent', 'N/A'),
        "High variability count": summary.get('high_variability_count', 0),
        "Low variability count": summary.get('low_variability_count', 0),
    }
    builder.add_summary(summary_metrics)

    # Variability rankings
    if rankings:
        ranking_lines = [
            f"- **{rank['appliance']}**: CV={rank.get('cv', 0):.2f} ({rank.get('variability_level', 'unknown')}), "
            f"avg {rank.get('mean_kwh', 0):.2f} kWh/{timeframe}"
            for rank in rankings
        ]
        builder.add_section("Variability Rankings (Most to Least Variable)", "\n".join(ranking_lines))

    # Detailed metrics
    detailed_lines = []
    for appliance, metrics in appliance_variability.items():
        if 'error' in metrics:
            detailed_lines.append(f"**{appliance}:** Error - {metrics['error']}")
            continue
        detailed_lines.append(f"**{appliance}**")
        detailed_lines.append(f"- CV: {metrics.get('cv', 0):.3f}")
        detailed_lines.append(f"- Level: {metrics.get('variability_level', 'unknown')}")
        detailed_lines.append(f"- Mean: {metrics.get('mean_kwh', 0):.2f} kWh/{timeframe}")
        detailed_lines.append(f"- Std dev: {metrics.get('std_kwh', 0):.2f} kWh")
        detailed_lines.append(f"- Range: {metrics.get('min_kwh', 0):.2f} - {metrics.get('max_kwh', 0):.2f} kWh")
        detailed_lines.append("")

    if detailed_lines:
        builder.add_section("Detailed Metrics", "\n".join(detailed_lines))

    # Insights
    if insights:
        builder.add_insights(insights)

    return builder.build()


def _format_usage_frequency_result(results: dict) -> str:
    """Format usage frequency analysis results."""
    summary = results.get("summary", {})
    profiles = results.get("appliance_profiles", {})
    high_usage_hours = results.get("high_usage_hours", {})
    insights = results.get("insights", [])

    builder = ResponseBuilder("Usage Frequency Analysis")

    # Summary metrics
    busiest_hour = summary.get('busiest_hour')
    summary_metrics = {
        "Appliances analyzed": summary.get('appliances_analyzed', 0),
        "Days analyzed": summary.get('days_analyzed', 'N/A'),
        "Most active appliance": summary.get('most_active_appliance', 'N/A'),
        "Busiest hour": f"{busiest_hour}:00" if busiest_hour is not None else 'N/A',
    }
    builder.add_summary(summary_metrics)

    # Appliance profiles
    profile_lines = []
    for appliance, profile in profiles.items():
        if 'error' in profile:
            profile_lines.append(f"**{appliance}:** Error - {profile['error']}")
            continue

        profile_lines.append(f"**{appliance}**")
        profile_lines.append(f"- Threshold: {profile.get('threshold_kw', 0.01):.3f} kW")
        profile_lines.append(f"- Daily active time: {profile.get('avg_daily_active_hours', 0):.1f} hours")
        profile_lines.append(f"- Max hourly activity: {profile.get('max_normalized_frequency', 0):.0%}")

        peak_hours = profile.get('peak_usage_hours', [])
        if peak_hours:
            peak_str = ", ".join([f"{h}:00" for h in sorted(peak_hours)])
            profile_lines.append(f"- Peak hours (>50% active): {peak_str}")
        profile_lines.append("")

    if profile_lines:
        builder.add_section("Appliance Usage Profiles", "\n".join(profile_lines))

    # High usage hours breakdown
    if high_usage_hours:
        sorted_hours = sorted(high_usage_hours.items(), key=lambda x: len(x[1]), reverse=True)[:6]
        hourly_lines = [f"- **{hour}:00**: {', '.join(active_apps)}" for hour, active_apps in sorted_hours]
        builder.add_section("Hourly Activity Overview", "\n".join(hourly_lines))

    # Insights
    if insights:
        builder.add_insights(insights)

    return builder.build()
