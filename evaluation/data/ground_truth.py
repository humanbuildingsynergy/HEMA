# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/data/ground_truth.py
"""Ground truth data extraction for factual accuracy evaluation.

This module provides functions to generate comprehensive data summaries
that serve as ground truth for evaluating HEMA's factual accuracy.
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
import json

from utils.logger import setup_logger

logger = setup_logger()


@dataclass
class GroundTruthSummary:
    """Comprehensive ground truth data for factual accuracy evaluation.

    Contains verified facts extracted from the actual energy data that
    the LLM evaluator can use to assess HEMA's claims.
    """

    # Household identification
    household_id: str
    data_file: str

    # Data coverage
    data_start_date: str
    data_end_date: str
    data_timespan_days: int

    # Consumption facts
    total_consumption_kwh: float
    avg_daily_consumption_kwh: float
    peak_demand_kw: float

    # Appliance facts
    num_appliances: int
    appliance_list: List[str]
    appliance_rankings: List[Dict[str, Any]]  # [{name, kwh, percentage}, ...]
    top_consumer: str
    top_consumer_percentage: float

    # Household features
    has_solar: bool
    has_ev: bool

    # Time-of-use facts (if available)
    rate_type: str  # "tou" or "flat"
    peak_hours: Optional[List[int]]  # e.g., [14, 15, 16, 17, 18, 19]
    peak_usage_percentage: float
    off_peak_usage_percentage: Optional[float]

    # Daily profile metrics (from consumption analysis)
    peak_hour: Optional[str]  # e.g., "11:00"
    off_peak_hour: Optional[str]  # e.g., "13:00"
    morning_peak_hour: Optional[str]  # e.g., "6:00"
    evening_peak_hour: Optional[str]  # e.g., "18:00"
    base_load_kw: Optional[float]
    load_factor: Optional[float]

    # TOU period breakdown (if TOU rate)
    tou_period_breakdown: Optional[Dict[str, Dict[str, float]]]  # {period: {kwh, percentage}}

    # Solar metrics (if has_solar)
    solar_generation_kwh: Optional[float]
    solar_contribution_percentage: Optional[float]
    grid_dependency_percentage: Optional[float]

    # Cost estimates (if rate data available)
    estimated_total_cost: Optional[float]
    potential_savings: Optional[float]

    # Raw analysis results (for detailed verification)
    consumption_analysis: Optional[Dict[str, Any]]
    appliance_analysis: Optional[Dict[str, Any]]
    tou_analysis: Optional[Dict[str, Any]]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def to_evaluation_context(self) -> str:
        """Format as a structured context string for the LLM evaluator.

        This produces a clear, readable summary that the evaluator LLM
        can use to verify factual claims made by HEMA.
        """
        lines = [
            "## Ground Truth Data Summary",
            "",
            "The following facts are verified from the actual energy data. "
            "Use these to evaluate the factual accuracy of HEMA's responses.",
            "",
            "### Household Information",
            f"- Household ID: {self.household_id}",
            f"- Data period: {self.data_start_date} to {self.data_end_date} ({self.data_timespan_days} days)",
            "",
            "### Energy Consumption Facts",
            f"- Total consumption: {self.total_consumption_kwh:,.2f} kWh",
            f"- Average daily consumption: {self.avg_daily_consumption_kwh:,.2f} kWh",
            f"- Peak demand: {self.peak_demand_kw:,.3f} kW",
        ]

        # Add load metrics if available
        if self.base_load_kw is not None:
            lines.append(f"- Base load: {self.base_load_kw:,.3f} kW")
        if self.load_factor is not None:
            lines.append(f"- Load factor: {self.load_factor:.1%}")

        lines.extend([
            "",
            "### Appliance Rankings (by total consumption)",
        ])

        for i, app in enumerate(self.appliance_rankings[:5], 1):
            lines.append(
                f"  {i}. {app['name']}: {app['kwh']:,.2f} kWh ({app['percentage']:.1f}%)"
            )

        lines.extend([
            "",
            f"- Number of tracked appliances: {self.num_appliances}",
            f"- Top energy consumer: {self.top_consumer} ({self.top_consumer_percentage:.1f}%)",
        ])

        # Add daily profile if available
        if self.peak_hour or self.off_peak_hour:
            lines.extend([
                "",
                "### Daily Usage Profile",
            ])
            if self.peak_hour:
                lines.append(f"- Highest usage hour: {self.peak_hour}")
            if self.off_peak_hour:
                lines.append(f"- Lowest usage hour: {self.off_peak_hour}")
            if self.morning_peak_hour:
                lines.append(f"- Morning peak: {self.morning_peak_hour}")
            if self.evening_peak_hour:
                lines.append(f"- Evening peak: {self.evening_peak_hour}")

        lines.extend([
            "",
            "### Household Features",
            f"- Solar panels: {'Yes' if self.has_solar else 'No'}",
            f"- Electric vehicle: {'Yes' if self.has_ev else 'No'}",
        ])

        # Add solar metrics if available
        if self.has_solar and self.solar_generation_kwh is not None:
            lines.extend([
                "",
                "### Solar Generation",
                f"- Total solar generation: {self.solar_generation_kwh:,.2f} kWh",
            ])
            if self.solar_contribution_percentage is not None:
                lines.append(f"- Solar contribution: {self.solar_contribution_percentage:.1f}%")
            if self.grid_dependency_percentage is not None:
                lines.append(f"- Grid dependency: {self.grid_dependency_percentage:.1f}%")

        lines.extend([
            "",
            "### Rate Structure",
            f"- Rate type: {self.rate_type.upper()}",
        ])

        if self.rate_type == "tou" and self.peak_hours:
            peak_range = f"{min(self.peak_hours)}:00 - {max(self.peak_hours) + 1}:00"
            lines.append(f"- Peak hours: {peak_range}")

        lines.append(f"- Peak period usage: {self.peak_usage_percentage:.1f}%")

        if self.off_peak_usage_percentage is not None:
            lines.append(f"- Off-peak period usage: {self.off_peak_usage_percentage:.1f}%")

        # Add TOU period breakdown if available
        if self.tou_period_breakdown:
            lines.append("")
            lines.append("### TOU Period Breakdown")
            for period, data in self.tou_period_breakdown.items():
                period_name = period.replace("_", " ").title()
                lines.append(f"- {period_name}: {data.get('kwh', 0):,.2f} kWh ({data.get('percentage', 0):.1f}%)")

        # Add cost estimates if available
        if self.estimated_total_cost is not None or self.potential_savings is not None:
            lines.extend([
                "",
                "### Cost Estimates",
            ])
            if self.estimated_total_cost is not None:
                lines.append(f"- Estimated total cost: ${self.estimated_total_cost:,.2f}")
            if self.potential_savings is not None:
                lines.append(f"- Potential monthly savings: ${self.potential_savings:,.2f}")

        # Add key facts for easy reference
        lines.extend([
            "",
            "### Key Facts for Verification",
            "When evaluating HEMA's claims, verify:",
            f"- Top appliance is {self.top_consumer} at {self.top_consumer_percentage:.1f}%",
            f"- Total consumption is {self.total_consumption_kwh:,.0f} kWh over {self.data_timespan_days} days",
            f"- Daily average is approximately {self.avg_daily_consumption_kwh:.0f} kWh",
        ])

        if self.appliance_rankings and len(self.appliance_rankings) >= 3:
            top3 = ", ".join([a['name'] for a in self.appliance_rankings[:3]])
            lines.append(f"- Top 3 consumers are: {top3}")

        lines.append(f"- Solar presence: {'Yes' if self.has_solar else 'No'}")
        lines.append(f"- EV presence: {'Yes' if self.has_ev else 'No'}")

        if self.peak_hour:
            lines.append(f"- Highest usage hour is {self.peak_hour}")

        return "\n".join(lines)


def extract_ground_truth(data_cache: Dict[str, Any]) -> Optional[GroundTruthSummary]:
    """Extract ground truth summary from the data cache.

    Args:
        data_cache: The _data_cache dict from analysis tools

    Returns:
        GroundTruthSummary with verified facts, or None if insufficient data
    """
    logger.info("Extracting ground truth summary for factual accuracy evaluation")

    # Check for required data
    household_profile = data_cache.get("household_profile")
    if household_profile is None:
        logger.warning("No household profile in data cache")
        return None

    energy_df = data_cache.get("energy_df")
    if energy_df is None:
        logger.warning("No energy data in data cache")
        return None

    # Extract appliance rankings with percentages
    appliance_rankings = []
    total_consumption = household_profile.total_consumption_kwh

    for name, kwh in household_profile.dominant_appliances:
        percentage = (kwh / total_consumption * 100) if total_consumption > 0 else 0
        appliance_rankings.append({
            "name": name,
            "kwh": round(kwh, 2),
            "percentage": round(percentage, 1),
        })

    # Fill in remaining appliances if available
    if hasattr(household_profile, 'appliance_list'):
        # Get all appliance totals
        # Data is in 15-minute intervals, divide by 4 to convert to kWh
        for col in household_profile.appliance_list:
            if col in energy_df.columns:
                kwh = energy_df[col].sum() / 4  # Convert to kWh
                # Check if already in rankings
                if not any(r['name'] == col for r in appliance_rankings) and kwh > 0:
                    percentage = (kwh / total_consumption * 100) if total_consumption > 0 else 0
                    appliance_rankings.append({
                        "name": col,
                        "kwh": round(kwh, 2),
                        "percentage": round(percentage, 1),
                    })

        # Sort by consumption
        appliance_rankings.sort(key=lambda x: x['kwh'], reverse=True)

    # Determine top consumer
    top_consumer = appliance_rankings[0]['name'] if appliance_rankings else "Unknown"
    top_consumer_pct = appliance_rankings[0]['percentage'] if appliance_rankings else 0

    # Get rate type and analysis results
    rate_type = data_cache.get("rate_type", "flat")
    analysis_results = data_cache.get("analysis_results") or {}

    # Extract consumption analysis metrics
    consumption_analysis = analysis_results.get("consumption")
    peak_hour = None
    off_peak_hour = None
    morning_peak_hour = None
    evening_peak_hour = None
    base_load_kw = None
    load_factor = None

    if consumption_analysis:
        daily_profile = consumption_analysis.get("daily_profile", {})
        peak_hour = daily_profile.get("peak_hour")
        off_peak_hour = daily_profile.get("off_peak_hour")
        morning_peak_hour = daily_profile.get("morning_peak")
        evening_peak_hour = daily_profile.get("evening_peak")

        summary_data = consumption_analysis.get("summary", {})
        base_load_kw = summary_data.get("base_load_kw")
        load_factor = summary_data.get("load_factor")

    # Extract TOU analysis metrics
    tou_analysis = analysis_results.get("utility_rate")
    peak_hours = None
    off_peak_pct = None
    tou_period_breakdown = None
    potential_savings = None

    if tou_analysis:
        period_breakdown = tou_analysis.get("period_breakdown", {})

        if rate_type == "tou" and period_breakdown:
            # Default TOU peak hours (2 PM - 8 PM)
            peak_hours = list(range(14, 20))

            # Extract period breakdown for ground truth
            tou_period_breakdown = {}
            for period, data in period_breakdown.items():
                tou_period_breakdown[period] = {
                    "kwh": data.get("kwh", 0),
                    "percentage": data.get("percentage", 0),
                }

            if "off_peak" in period_breakdown:
                off_peak_pct = period_breakdown["off_peak"].get("percentage")

        # Get savings potential
        savings_data = tou_analysis.get("savings_potential", {})
        potential_savings = savings_data.get("monthly_savings")

    # Extract solar metrics if available
    solar_generation_kwh = None
    solar_contribution_pct = None
    grid_dependency_pct = None

    if household_profile.has_solar:
        processed_df = data_cache.get("processed_df")
        if processed_df is not None:
            # Check for solar columns in processed data
            if "solar_generation" in processed_df.columns:
                solar_generation_kwh = processed_df["solar_generation"].sum() / 4  # Convert to kWh
            elif "Solar power generation 1" in energy_df.columns:
                solar_generation_kwh = energy_df["Solar power generation 1"].sum() / 4

            if "solar_contribution" in processed_df.columns:
                solar_contribution_pct = processed_df["solar_contribution"].mean()

            if "grid_dependency" in processed_df.columns:
                grid_dependency_pct = processed_df["grid_dependency"].mean()

    summary = GroundTruthSummary(
        household_id=household_profile.household_id,
        data_file=household_profile.data_file,
        data_start_date=household_profile.data_start_date,
        data_end_date=household_profile.data_end_date,
        data_timespan_days=household_profile.data_timespan_days,
        total_consumption_kwh=household_profile.total_consumption_kwh,
        avg_daily_consumption_kwh=household_profile.avg_daily_consumption_kwh,
        peak_demand_kw=household_profile.peak_demand_kw,
        num_appliances=household_profile.num_appliances,
        appliance_list=household_profile.appliance_list,
        appliance_rankings=appliance_rankings,
        top_consumer=top_consumer,
        top_consumer_percentage=top_consumer_pct,
        has_solar=household_profile.has_solar,
        has_ev=household_profile.has_ev,
        rate_type=rate_type,
        peak_hours=peak_hours,
        peak_usage_percentage=household_profile.peak_usage_percentage,
        off_peak_usage_percentage=off_peak_pct,
        # Daily profile metrics
        peak_hour=peak_hour,
        off_peak_hour=off_peak_hour,
        morning_peak_hour=morning_peak_hour,
        evening_peak_hour=evening_peak_hour,
        base_load_kw=base_load_kw,
        load_factor=load_factor,
        # TOU period breakdown
        tou_period_breakdown=tou_period_breakdown,
        # Solar metrics
        solar_generation_kwh=solar_generation_kwh,
        solar_contribution_percentage=solar_contribution_pct,
        grid_dependency_percentage=grid_dependency_pct,
        # Cost estimates
        estimated_total_cost=None,  # Would need rate data to compute
        potential_savings=potential_savings,
        # Raw analysis results
        consumption_analysis=consumption_analysis,
        appliance_analysis=analysis_results.get("appliances"),
        tou_analysis=tou_analysis,
    )

    logger.info(f"Ground truth extracted: {len(appliance_rankings)} appliances ranked")
    return summary


def get_current_ground_truth() -> Optional[GroundTruthSummary]:
    """Convenience function to get ground truth from the current data cache.

    Returns:
        GroundTruthSummary if data is available, None otherwise
    """
    try:
        from agents.tools.analysis_tools import get_data_cache
        cache = get_data_cache()
        return extract_ground_truth(cache)
    except Exception as e:
        logger.warning(f"Could not extract ground truth: {e}")
        return None
