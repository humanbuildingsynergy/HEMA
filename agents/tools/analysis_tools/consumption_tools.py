# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/tools/analysis_tools/consumption_tools.py
"""Consumption and appliance analysis tools."""
from langchain_core.tools import tool
from utils.logger import setup_logger
from .cache import _data_cache

# Use common utilities to reduce code duplication
from agents.tools.common import (
    ResponseBuilder,
    get_data_period_info,
    format_data_period_header,
)

logger = setup_logger()


@tool
def analyze_consumption() -> str:
    """
    Analyze overall energy consumption patterns.

    Requires data to be loaded first using load_energy_data.

    Returns:
        Analysis of consumption patterns including daily/hourly profiles,
        peak usage times, and statistical summaries.
    """
    from core.analysis.consumption_analyzer import ConsumptionAnalyzer
    from core.analysis.feature_engineer import FeatureEngineer

    logger.info("Analyzing consumption patterns")

    if _data_cache["energy_df"] is None:
        return "Error: No data loaded. Please use load_energy_data first."

    try:
        energy_df = _data_cache["energy_df"]

        # Feature engineering if not done
        if _data_cache["processed_df"] is None:
            engineer = FeatureEngineer()
            processed_df = engineer.add_time_features(energy_df.copy())
            processed_df = engineer.add_energy_metrics(processed_df)
            _data_cache["processed_df"] = processed_df
        else:
            processed_df = _data_cache["processed_df"]

        # Run consumption analysis
        analyzer = ConsumptionAnalyzer()
        results = analyzer.analyze(processed_df)

        # Store results
        if _data_cache["analysis_results"] is None:
            _data_cache["analysis_results"] = {}
        _data_cache["analysis_results"]["consumption"] = results

        # Format response
        summary = results.get("summary", {})
        daily = results.get("daily_profile", {})
        period_header = format_data_period_header()

        response = f"""## Consumption Analysis Results

{period_header}### Overall Statistics
- Total consumption: {summary.get('total_kwh', 0):.2f} kWh (for this period)
- Average daily: {summary.get('avg_daily_kwh', 0):.2f} kWh/day
- Peak demand: {summary.get('peak_demand_kw', 0):.2f} kW
- Load factor: {summary.get('load_factor', 0):.1%}

### Daily Profile
- Highest usage hour: {daily.get('peak_hour', 'N/A')}
- Lowest usage hour: {daily.get('off_peak_hour', 'N/A')}
- Morning peak: {daily.get('morning_peak', 'N/A')}
- Evening peak: {daily.get('evening_peak', 'N/A')}

### Patterns Detected
{results.get('patterns', 'No specific patterns identified.')}
"""
        return response

    except Exception as e:
        logger.error(f"Error analyzing consumption: {str(e)}")
        return f"Error analyzing consumption: {str(e)}"


@tool
def analyze_appliances() -> str:
    """
    Analyze individual appliance energy usage.

    Requires data to be loaded first using load_energy_data.

    Returns:
        Breakdown of energy usage by appliance, including top consumers,
        usage patterns, and efficiency insights.
    """
    from core.analysis.appliance_analyzer import ApplianceAnalyzer

    logger.info("Analyzing appliance usage")

    if _data_cache["energy_df"] is None:
        return "Error: No data loaded. Please use load_energy_data first."

    try:
        energy_df = _data_cache["energy_df"]

        # Use processed data if available
        if _data_cache["processed_df"] is not None:
            df = _data_cache["processed_df"]
        else:
            df = energy_df

        # Run appliance analysis
        analyzer = ApplianceAnalyzer()
        results = analyzer.analyze(df)

        # Store results
        if _data_cache["analysis_results"] is None:
            _data_cache["analysis_results"] = {}
        _data_cache["analysis_results"]["appliances"] = results

        # Format response using common utilities
        rankings = results.get("consumption_rankings", [])
        top_appliances = rankings[:5] if rankings else []
        period_info = get_data_period_info(_data_cache.get("energy_df"))
        num_days = period_info.get('num_days', 14) if period_info else 14

        builder = ResponseBuilder("Appliance Analysis Results")
        builder.add_header(f"{period_info.get('start_date', '')} to {period_info.get('end_date', '')}")

        # Build appliance table
        if top_appliances:
            rows = []
            for i, app in enumerate(top_appliances, 1):
                total_kwh = app.get('total_kwh', 0)
                daily_avg = total_kwh / num_days if num_days > 0 else 0
                monthly_est = daily_avg * 30
                rows.append([
                    f"{i}. {app.get('appliance', 'Unknown')}",
                    f"{total_kwh:.2f} kWh",
                    f"{app.get('percentage', 0):.1f}%",
                    f"{daily_avg:.1f} kWh/day",
                    f"{monthly_est:.0f} kWh/mo"
                ])
            builder.add_metrics_table(
                f"Top Energy Consumers (over {num_days} days)",
                ["Appliance", "Total", "%", "Daily Avg", "Est. Monthly"],
                rows
            )

        # Add insights
        insights = results.get("insights", [])
        if insights:
            builder.add_insights(insights[:5])

        return builder.build()

    except Exception as e:
        logger.error(f"Error analyzing appliances: {str(e)}")
        return f"Error analyzing appliances: {str(e)}"


@tool
def analyze_utility_rate() -> str:
    """
    Analyze energy usage relative to the utility rate structure.

    Automatically adapts analysis based on rate type:
    - **TOU (Time-of-Use)**: Analyzes peak/off-peak consumption and load shifting savings
    - **Flat Rate**: Analyzes time-of-day patterns and total consumption costs

    Requires data to be loaded first using load_energy_data.
    Works best if rate data was also loaded.

    Returns:
        For TOU: Consumption by rate period (peak, off-peak) and potential savings from load shifting.
        For Flat: Time-of-day usage patterns and cost breakdown by appliance.
    """
    from core.analysis.tou_analyzer import TOUAnalyzer

    logger.info("Analyzing utility rate patterns")

    if _data_cache["energy_df"] is None:
        return "Error: No data loaded. Please use load_energy_data first."

    try:
        # Use processed data if available
        if _data_cache["processed_df"] is not None:
            df = _data_cache["processed_df"]
        else:
            df = _data_cache["energy_df"]

        rate_df = _data_cache.get("rate_df")

        # Run TOU analysis
        analyzer = TOUAnalyzer()
        results = analyzer.analyze(df, rate_df)

        # Store results
        if _data_cache["analysis_results"] is None:
            _data_cache["analysis_results"] = {}
        _data_cache["analysis_results"]["utility_rate"] = results

        # Format response based on rate type
        rate_type = results.get("rate_type", "tou")

        if rate_type == "flat":
            response = _format_flat_rate_results(results)
        else:
            response = _format_tou_results(results)

        return response

    except Exception as e:
        logger.error(f"Error analyzing utility rate: {str(e)}")
        return f"Error analyzing utility rate: {str(e)}"


def _format_tou_results(results: dict) -> str:
    """Format TOU analysis results."""
    period_breakdown = results.get("period_breakdown", {})
    savings_potential = results.get("savings_potential", {})
    period_info = get_data_period_info(_data_cache.get("energy_df"))

    builder = ResponseBuilder("Time-of-Use (TOU) Rate Analysis")
    if period_info:
        builder.add_header(f"{period_info.get('start_date', '')} to {period_info.get('end_date', '')}")

    # Consumption by period
    if period_breakdown:
        metrics = {
            period: f"{data.get('kwh', 0):.2f} kWh ({data.get('percentage', 0):.1f}%)"
            for period, data in period_breakdown.items()
        }
        builder.add_summary(metrics)

    # Savings potential
    if savings_potential:
        savings_metrics = {
            "Monthly savings": f"${savings_potential.get('monthly_savings', 0):.2f}",
            "Peak reduction": f"{savings_potential.get('peak_reduction_kwh', 0):.2f} kWh"
        }
        builder.add_section("Potential Savings", "\n".join(f"- **{k}**: {v}" for k, v in savings_metrics.items()))

    # Recommendations
    recommendations = results.get("recommendations", [])
    if recommendations:
        builder.add_recommendations(recommendations[:3])

    return builder.build()


def _format_flat_rate_results(results: dict) -> str:
    """Format flat rate analysis results."""
    period_breakdown = results.get("period_breakdown", {})
    savings_potential = results.get("savings_potential", {})
    period_info = get_data_period_info(_data_cache.get("energy_df"))

    builder = ResponseBuilder("Flat Rate Analysis")
    if period_info:
        builder.add_header(f"{period_info.get('start_date', '')} to {period_info.get('end_date', '')}")

    # Summary stats
    total_kwh = results.get("total_kwh", 0)
    total_cost = results.get("total_cost", 0)
    flat_rate = results.get("flat_rate", 0)
    peak_hour = results.get("peak_hour", 0)

    summary_metrics = {
        "Total consumption": f"{total_kwh:.2f} kWh",
        "Estimated cost": f"${total_cost:.2f} (at {flat_rate*100:.2f}¢/kWh)",
        "Peak demand hour": f"{peak_hour}:00"
    }
    builder.add_summary(summary_metrics)

    # Consumption by time of day
    if period_breakdown:
        metrics = {
            period.capitalize(): f"{data.get('kwh', 0):.2f} kWh ({data.get('percentage', 0):.1f}%)"
            for period, data in period_breakdown.items()
        }
        builder.add_section("Consumption by Time of Day", "\n".join(f"- **{k}**: {v}" for k, v in metrics.items()))

    # Savings potential
    if savings_potential:
        savings_metrics = {
            "Efficiency improvement": f"${savings_potential.get('monthly_savings', 0):.2f}",
            "Reduction potential": f"{savings_potential.get('reduction_potential_kwh', 0):.2f} kWh",
            "Peak demand": f"{savings_potential.get('peak_demand_kw', 0):.2f} kW"
        }
        builder.add_section("Potential Savings", "\n".join(f"- **{k}**: {v}" for k, v in savings_metrics.items()))

    # Recommendations
    recommendations = results.get("recommendations", [])
    if recommendations:
        builder.add_recommendations(recommendations[:4])

    return builder.build()


@tool
def get_analysis_summary() -> str:
    """
    Get a comprehensive summary of all analyses performed.

    Returns:
        Combined summary of consumption, appliance, and TOU analyses
        along with personalized recommendations.
    """
    logger.info("Getting analysis summary")

    if _data_cache["analysis_results"] is None:
        return "No analysis has been performed yet. Please run analyze_consumption, analyze_appliances, or analyze_tou first."

    results = _data_cache["analysis_results"]
    period_info = get_data_period_info(_data_cache.get("energy_df"))

    builder = ResponseBuilder("Complete Energy Analysis Summary")
    if period_info:
        builder.add_header(f"{period_info.get('start_date', '')} to {period_info.get('end_date', '')}")

    # Consumption overview
    if "consumption" in results:
        summary = results["consumption"].get("summary", {})
        consumption_metrics = {
            "Total": f"{summary.get('total_kwh', 0):.2f} kWh",
            "Daily average": f"{summary.get('avg_daily_kwh', 0):.2f} kWh/day"
        }
        builder.add_section("Consumption Overview", "\n".join(f"- **{k}**: {v}" for k, v in consumption_metrics.items()))

    # Top appliances
    if "appliances" in results:
        rankings = results["appliances"].get("consumption_rankings", [])[:3]
        if rankings:
            appliance_strs = [f"- {app.get('appliance', 'Unknown')}: {app.get('total_kwh', 0):.2f} kWh" for app in rankings]
            builder.add_section("Top Appliances", "\n".join(appliance_strs))

    # Cost optimization
    if "utility_rate" in results:
        savings = results["utility_rate"].get("savings_potential", {})
        builder.add_section("Cost Optimization", f"- **Potential monthly savings**: ${savings.get('monthly_savings', 0):.2f}")

    return builder.build()
