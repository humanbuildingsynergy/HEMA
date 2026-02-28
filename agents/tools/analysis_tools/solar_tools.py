# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/tools/analysis_tools/solar_tools.py
"""Solar power analysis tools."""
from typing import Optional
from langchain_core.tools import tool
from utils.logger import setup_logger
from .cache import _data_cache

# Use common utilities to reduce code duplication
from agents.tools.common import ResponseBuilder

logger = setup_logger()


@tool
def analyze_solar_availability(
    analysis_type: str = "average_profile",
    date: Optional[str] = None,
    timeframe: str = "daily",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> str:
    """
    Analyze solar power generation patterns and availability.

    This tool analyzes solar generation data to show daily profiles, average patterns,
    or aggregated generation totals over time.

    Use this tool for questions like:
    - "What was my solar generation on July 4th?"
    - "Show my average daily solar profile"
    - "What are my peak solar hours?"
    - "Show weekly solar generation totals"
    - "How much solar power do I generate on average?"
    - "When does my solar production peak?"

    Args:
        analysis_type: Type of analysis to perform:
            - "daily_profile": Solar generation for a specific date (requires date param)
            - "average_profile": Average hourly solar profile across all days (default)
            - "aggregated": Total generation by timeframe (daily/weekly/monthly)
        date: Specific date for daily_profile analysis (YYYY-MM-DD format).
              Required when analysis_type is "daily_profile".
        timeframe: Aggregation level for "aggregated" analysis type.
                  Options: "daily", "weekly", "monthly". Default is "daily".
        start_date: Optional start date filter (YYYY-MM-DD format).
        end_date: Optional end date filter (YYYY-MM-DD format).

    Returns:
        Detailed solar generation analysis including profiles, totals, and peak hours.
    """
    from core.analysis.solar import SolarAvailabilityAnalyzer

    logger.info(f"Analyzing solar availability: type={analysis_type}, date={date}, timeframe={timeframe}")

    if _data_cache["energy_df"] is None:
        return "Error: No data loaded. Please use load_energy_data first."

    # Validate analysis_type
    valid_types = ["daily_profile", "average_profile", "aggregated"]
    if analysis_type not in valid_types:
        return f"Error: Invalid analysis_type '{analysis_type}'. Valid options: {', '.join(valid_types)}"

    # Validate date requirement for daily_profile
    if analysis_type == "daily_profile" and not date:
        return "Error: 'date' parameter is required for daily_profile analysis. Please provide a date in YYYY-MM-DD format."

    # Validate timeframe for aggregated
    valid_timeframes = ["daily", "weekly", "monthly"]
    if analysis_type == "aggregated" and timeframe not in valid_timeframes:
        return f"Error: Invalid timeframe '{timeframe}'. Valid options: {', '.join(valid_timeframes)}"

    try:
        energy_df = _data_cache["energy_df"]

        # Use processed data if available
        if _data_cache["processed_df"] is not None:
            df = _data_cache["processed_df"]
        else:
            df = energy_df

        # Run solar availability analysis
        analyzer = SolarAvailabilityAnalyzer()
        results = analyzer.analyze_solar_availability(
            df=df,
            analysis_type=analysis_type,
            date=date,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
        )

        # Check for errors
        if 'error' in results:
            return f"Error: {results['error']}"

        # Format response based on analysis type
        if analysis_type == "daily_profile":
            return _format_daily_profile(results)
        elif analysis_type == "average_profile":
            return _format_average_profile(results)
        else:  # aggregated
            return _format_aggregated(results)

    except Exception as e:
        logger.error(f"Error analyzing solar availability: {str(e)}")
        return f"Error analyzing solar availability: {str(e)}"


def _format_daily_profile(results: dict) -> str:
    """Format daily profile results."""
    date = results.get('date', 'Unknown')
    total_kwh = results.get('total_kwh', 0)
    peak_hour = results.get('peak_hour', 0)
    peak_kw = results.get('peak_kw', 0)
    gen_start = results.get('generation_start')
    gen_end = results.get('generation_end')
    gen_hours = results.get('generation_hours', 0)
    profile = results.get('profile', [])

    response = f"""## Solar Generation - {date}

### Summary
- **Total generation:** {total_kwh} kWh
- **Peak hour:** {peak_hour}:00 ({peak_kw:.2f} kW)
- **Generation window:** {gen_start}:00 - {gen_end}:00 ({gen_hours} hours)

### Hourly Profile
"""

    # Show profile (filter to hours with generation > 0)
    active_profile = [p for p in profile if p.get('kw', 0) > 0.01]
    if active_profile:
        for p in active_profile:
            hour = p.get('hour', p.get('time', ''))
            kw = p.get('kw', 0)
            bar = '█' * int(kw * 5)  # Visual bar
            if isinstance(hour, int):
                response += f"- {hour:02d}:00: {kw:.2f} kW {bar}\n"
            else:
                response += f"- {hour}: {kw:.2f} kW {bar}\n"
    else:
        response += "No significant solar generation on this date.\n"

    return response


def _format_average_profile(results: dict) -> str:
    """Format average profile results."""
    date_range = results.get('date_range', {})
    days_analyzed = results.get('days_analyzed', 0)
    avg_daily_kwh = results.get('avg_daily_kwh', 0)
    peak_hour = results.get('peak_hour', 0)
    peak_mean_kw = results.get('peak_mean_kw', 0)
    gen_start = results.get('generation_start')
    gen_end = results.get('generation_end')
    avg_gen_hours = results.get('avg_generation_hours', 0)
    profile = results.get('profile', [])

    response = f"""## Average Daily Solar Profile

### Summary
- **Days analyzed:** {days_analyzed}
- **Date range:** {date_range.get('start', 'N/A')} to {date_range.get('end', 'N/A')}
- **Average daily generation:** {avg_daily_kwh} kWh
- **Peak hour:** {peak_hour}:00 (avg {peak_mean_kw:.2f} kW)
- **Typical generation window:** {gen_start}:00 - {gen_end}:00 ({avg_gen_hours} hours)

### Hourly Profile (Mean ± Std Dev)
"""

    # Show profile (filter to hours with generation > 0)
    active_profile = [p for p in profile if p.get('mean_kw', 0) > 0.01]
    if active_profile:
        for p in active_profile:
            hour = p.get('hour', 0)
            mean_kw = p.get('mean_kw', 0)
            std_kw = p.get('std_kw', 0)
            bar = '█' * int(mean_kw * 5)
            response += f"- {hour:02d}:00: {mean_kw:.2f} ± {std_kw:.2f} kW {bar}\n"
    else:
        response += "No significant solar generation in the data.\n"

    return response


def _format_aggregated(results: dict) -> str:
    """Format aggregated generation results."""
    timeframe = results.get('timeframe', 'daily')
    date_range = results.get('date_range', {})
    num_periods = results.get('num_periods', 0)
    total_kwh = results.get('total_kwh', 0)
    avg_kwh = results.get('avg_kwh_per_period', 0)
    best = results.get('best_period', {})
    worst = results.get('worst_period', {})
    periods = results.get('periods', [])

    response = f"""## Solar Generation ({timeframe.capitalize()} Totals)

### Summary
- **Date range:** {date_range.get('start', 'N/A')} to {date_range.get('end', 'N/A')}
- **Periods analyzed:** {num_periods}
- **Total generation:** {total_kwh} kWh
- **Average per {timeframe[:-2] if timeframe.endswith('ly') else timeframe}:** {avg_kwh} kWh
- **Best period:** {best.get('period', 'N/A')} ({best.get('total_kwh', 0)} kWh)
- **Worst period:** {worst.get('period', 'N/A')} ({worst.get('total_kwh', 0)} kWh)

### {timeframe.capitalize()} Breakdown
"""

    # Show periods (limit to most recent 10 if too many)
    display_periods = periods[-10:] if len(periods) > 10 else periods
    if len(periods) > 10:
        response += f"(Showing most recent 10 of {len(periods)} periods)\n\n"

    max_kwh = max(p.get('total_kwh', 0) for p in display_periods) if display_periods else 1
    for p in display_periods:
        period = p.get('period', '')
        kwh = p.get('total_kwh', 0)
        bar_len = int((kwh / max_kwh) * 20) if max_kwh > 0 else 0
        bar = '█' * bar_len
        response += f"- {period}: {kwh} kWh {bar}\n"

    return response


@tool
def analyze_solar_alignment(
    appliance: Optional[str] = None,
    analysis_type: str = "summary",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> str:
    """
    Analyze how well appliance usage aligns with solar power generation.

    This tool measures the synchronization between appliance operation and solar production.
    The alignment score represents the fraction of appliance active time that coincides
    with solar generation periods.

    Use this tool for questions like:
    - "How well does my HVAC usage align with solar production?"
    - "Which appliances run mostly during solar hours?"
    - "Can I improve my solar self-consumption?"
    - "What's the solar alignment for my pool pump?"
    - "Show me solar alignment for all appliances"
    - "When does my dishwasher run relative to solar generation?"

    Args:
        appliance: Specific appliance to analyze (e.g., "HVAC unit", "Pool pump").
                  If not provided, analyzes all appliances.
        analysis_type: Type of analysis to perform:
            - "summary": Overall alignment scores for appliances (default)
            - "daily": Day-by-day alignment profile for a specific appliance
            - "hourly": Hourly pattern showing appliance activity vs solar (requires appliance)
        start_date: Optional start date filter (YYYY-MM-DD format)
        end_date: Optional end date filter (YYYY-MM-DD format)

    Returns:
        Solar alignment analysis showing how well appliances sync with solar generation.
    """
    from core.analysis.solar import SolarAlignmentAnalyzer

    logger.info(f"Analyzing solar alignment: appliance={appliance}, type={analysis_type}")

    if _data_cache["energy_df"] is None:
        return "Error: No data loaded. Please use load_energy_data first."

    # Validate analysis_type
    valid_types = ["summary", "daily", "hourly"]
    if analysis_type not in valid_types:
        return f"Error: Invalid analysis_type '{analysis_type}'. Valid options: {', '.join(valid_types)}"

    # Validate appliance requirement for daily/hourly
    if analysis_type in ["daily", "hourly"] and not appliance:
        return f"Error: 'appliance' parameter is required for {analysis_type} analysis."

    try:
        energy_df = _data_cache["energy_df"]

        # Use processed data if available
        if _data_cache["processed_df"] is not None:
            df = _data_cache["processed_df"]
        else:
            df = energy_df

        # Initialize analyzer (loads thresholds from CSV)
        analyzer = SolarAlignmentAnalyzer()

        if analysis_type == "summary":
            results = analyzer.calculate_alignment(
                df=df,
                appliance=appliance,
                start_date=start_date,
                end_date=end_date,
            )
            if 'error' in results:
                return f"Error: {results['error']}"
            return _format_alignment_summary(results)

        elif analysis_type == "daily":
            results = analyzer.get_daily_alignment_profile(
                df=df,
                appliance=appliance,
                start_date=start_date,
                end_date=end_date,
            )
            if 'error' in results:
                return f"Error: {results['error']}"
            return _format_daily_alignment(results)

        else:  # hourly
            results = analyzer.get_hourly_alignment_pattern(
                df=df,
                appliance=appliance,
                start_date=start_date,
                end_date=end_date,
            )
            if 'error' in results:
                return f"Error: {results['error']}"
            return _format_hourly_alignment(results)

    except Exception as e:
        logger.error(f"Error analyzing solar alignment: {str(e)}")
        return f"Error analyzing solar alignment: {str(e)}"


def _format_alignment_summary(results: dict) -> str:
    """Format alignment summary results."""
    date_range = results.get('date_range', {})
    days = results.get('days_analyzed', 0)
    total_intervals = results.get('total_intervals', 0)
    solar_intervals = results.get('solar_generation_intervals', 0)
    alignments = results.get('appliance_alignments', {})

    response = f"""## Solar Alignment Analysis

### Data Overview
- **Date range:** {date_range.get('start', 'N/A')} to {date_range.get('end', 'N/A')}
- **Days analyzed:** {days}
- **Solar generation periods:** {solar_intervals} intervals ({solar_intervals * 0.25:.1f} hours)

### Appliance Alignment Scores
"""

    # Sort by alignment score (highest first)
    sorted_appliances = sorted(
        [(app, data) for app, data in alignments.items() if data.get('alignment_score') is not None],
        key=lambda x: x[1].get('alignment_score', 0),
        reverse=True
    )

    if not sorted_appliances:
        response += "\nNo appliances with recorded activity during the analysis period.\n"
        return response

    for app, data in sorted_appliances:
        score = data.get('alignment_percentage', 0)
        aligned_hrs = data.get('aligned_hours', 0)
        active_hrs = data.get('active_hours', 0)
        threshold = data.get('threshold_kw', 0)

        # Visual indicator
        if score >= 70:
            indicator = "🌞"  # High alignment
        elif score >= 40:
            indicator = "⛅"  # Medium alignment
        else:
            indicator = "🌙"  # Low alignment

        response += f"\n**{app}** {indicator}\n"
        response += f"- Alignment: {score:.1f}% ({aligned_hrs:.1f} of {active_hrs:.1f} active hours during solar)\n"
        response += f"- Active threshold: {threshold} kW\n"

    # Add interpretation
    response += """
### Interpretation
- 🌞 **70%+**: Excellent solar alignment - appliance runs mostly during solar hours
- ⛅ **40-70%**: Moderate alignment - some opportunity to shift usage
- 🌙 **<40%**: Low alignment - consider scheduling during solar production
"""

    return response


def _format_daily_alignment(results: dict) -> str:
    """Format daily alignment profile results."""
    appliance = results.get('appliance', 'Unknown')
    threshold = results.get('threshold_kw', 0)
    date_range = results.get('date_range', {})
    days = results.get('days_analyzed', 0)
    days_active = results.get('days_with_activity', 0)
    avg_alignment = results.get('average_alignment')
    daily_profile = results.get('daily_profile', [])

    response = f"""## Daily Solar Alignment - {appliance}

### Summary
- **Date range:** {date_range.get('start', 'N/A')} to {date_range.get('end', 'N/A')}
- **Days analyzed:** {days} (active: {days_active})
- **Average alignment:** {avg_alignment * 100:.1f}% (when active)
- **Active threshold:** {threshold} kW

### Daily Profile
"""

    # Show daily scores
    for day in daily_profile:
        date = day.get('date', '')
        score = day.get('alignment_score')
        active = day.get('active_intervals', 0)

        if score is not None:
            pct = score * 100
            bar_len = int(pct / 5)
            bar = '█' * bar_len
            response += f"- {date}: {pct:5.1f}% {bar} ({active * 0.25:.1f}h active)\n"
        else:
            response += f"- {date}: No activity\n"

    return response


def _format_hourly_alignment(results: dict) -> str:
    """Format hourly alignment pattern results."""
    appliance = results.get('appliance', 'Unknown')
    threshold = results.get('threshold_kw', 0)
    date_range = results.get('date_range', {})
    solar_window = results.get('solar_generation_window', {})
    hourly_pattern = results.get('hourly_pattern', [])

    solar_start = solar_window.get('start_hour')
    solar_end = solar_window.get('end_hour')

    response = f"""## Hourly Pattern - {appliance}

### Summary
- **Date range:** {date_range.get('start', 'N/A')} to {date_range.get('end', 'N/A')}
- **Active threshold:** {threshold} kW
- **Solar window:** {solar_start}:00 - {solar_end}:00

### Hour-by-Hour Pattern
| Hour | Solar (kW) | Activity Rate | Appliance (kW) | Status |
|------|------------|---------------|----------------|--------|
"""

    for h in hourly_pattern:
        hour = h.get('hour', 0)
        solar_kw = h.get('avg_solar_kw', 0)
        activity = h.get('appliance_activity_rate', 0)
        app_kw = h.get('avg_appliance_kw', 0)

        # Determine if this is in solar window
        in_solar = solar_start is not None and solar_start <= hour <= solar_end
        solar_indicator = "☀️" if in_solar and solar_kw > 0.01 else "  "

        # Activity indicator
        if activity > 0.3:
            activity_bar = "███"
        elif activity > 0.1:
            activity_bar = "██ "
        elif activity > 0:
            activity_bar = "█  "
        else:
            activity_bar = "   "

        # Status based on alignment
        if activity > 0.1 and in_solar:
            status = "✓ Aligned"
        elif activity > 0.1 and not in_solar:
            status = "⚠ Consider shift"
        else:
            status = ""

        response += f"| {hour:02d}:00 | {solar_indicator} {solar_kw:.2f} | {activity_bar} {activity:.0%} | {app_kw:.3f} | {status} |\n"

    # Add recommendations
    response += "\n### Recommendations\n"
    if solar_start is not None:
        response += f"- Optimal usage window: {solar_start}:00 - {solar_end}:00 (solar generation hours)\n"
        response += "- Consider scheduling high-energy tasks during this window\n"

    return response
