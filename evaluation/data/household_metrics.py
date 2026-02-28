# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/data/household_metrics.py
"""Household-specific metrics for case study comparisons.

This module provides tools for extracting and tracking household characteristics
that are important for comparing HEMA's performance across different homes.
"""

from dataclasses import dataclass, asdict
from typing import List, Tuple, Optional
import re

import pandas as pd

from utils.logger import setup_logger

logger = setup_logger()


@dataclass
class HouseholdProfile:
    """Household characteristics for case study comparisons.

    Captures key metrics about a household's energy data that are useful
    for comparing HEMA's recommendations across different home types.
    """

    # Core identifiers
    household_id: str
    data_file: str

    # Requested metrics
    num_appliances: int
    avg_daily_consumption_kwh: float
    has_solar: bool
    has_ev: bool
    peak_usage_percentage: float
    data_start_date: str
    data_end_date: str
    data_timespan_days: int
    dominant_appliances: List[Tuple[str, float]]  # [(name, kwh), ...]

    # Additional useful metrics
    total_consumption_kwh: float
    peak_demand_kw: float
    appliance_list: List[str]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        # Convert numpy types to native Python types for JSON serialization
        for key, value in result.items():
            if hasattr(value, 'item'):  # numpy scalar
                result[key] = value.item()
            elif isinstance(value, list):
                result[key] = [
                    (item[0], item[1].item() if hasattr(item[1], 'item') else item[1])
                    if isinstance(item, tuple) else item
                    for item in value
                ]
        return result

    def summary(self) -> str:
        """Human-readable summary for reports."""
        solar_str = "Yes" if self.has_solar else "No"
        ev_str = "Yes" if self.has_ev else "No"

        dominant = ", ".join(
            [f"{name} ({kwh:.1f} kWh)" for name, kwh in self.dominant_appliances[:3]]
        )

        return f"""Household {self.household_id}
- Appliances: {self.num_appliances}
- Avg daily consumption: {self.avg_daily_consumption_kwh:.1f} kWh
- Solar: {solar_str} | EV: {ev_str}
- Peak usage: {self.peak_usage_percentage:.1f}%
- Data: {self.data_start_date} to {self.data_end_date} ({self.data_timespan_days} days)
- Top consumers: {dominant}"""

    def __str__(self) -> str:
        return self.summary()


def extract_household_profile(
    energy_df: pd.DataFrame,
    data_file: str,
    rate_df: Optional[pd.DataFrame] = None,
) -> HouseholdProfile:
    """Extract household profile from loaded energy data.

    Args:
        energy_df: DataFrame with energy consumption data
        data_file: Path to the energy data file
        rate_df: Optional DataFrame with rate structure data

    Returns:
        HouseholdProfile with extracted metrics
    """
    logger.info(f"Extracting household profile from {data_file}")

    # 1. Extract household ID from filename
    match = re.search(r"energy_use_data_(\d+)", data_file)
    household_id = match.group(1) if match else "unknown"

    # 2. Identify appliance columns (exclude non-appliance columns)
    excluded_cols = {
        "local_15min",
        "dataid",
        "grid",
        "Solar power generation 1",
        "Solar power generation 2",
        "total_consumption",
        "_total",
    }
    appliance_cols = [c for c in energy_df.columns if c not in excluded_cols]

    # 3. Check for solar and EV presence
    all_cols_lower = [c.lower() for c in energy_df.columns]
    has_solar = any("solar" in c for c in all_cols_lower)
    has_ev = any(
        "vehicle" in c or "ev " in c or c.startswith("ev") for c in all_cols_lower
    )

    # 4. Compute total consumption
    # Check if total_consumption column exists, otherwise calculate
    if "total_consumption" in energy_df.columns:
        total_col = "total_consumption"
    else:
        # Calculate total from appliance columns
        energy_df = energy_df.copy()
        energy_df["_total"] = energy_df[appliance_cols].sum(axis=1)
        total_col = "_total"

    # Data is in 15-minute intervals (power readings in kW)
    # Divide by 4 to convert to kWh (4 intervals per hour)
    total_consumption = energy_df[total_col].sum() / 4

    # 5. Calculate data timespan
    timestamps = pd.to_datetime(energy_df["local_15min"])
    start_date = timestamps.min()
    end_date = timestamps.max()
    timespan_days = (end_date - start_date).days + 1

    # 6. Calculate average daily consumption
    avg_daily = total_consumption / timespan_days if timespan_days > 0 else 0.0

    # 7. Calculate peak demand (max power in any interval)
    peak_demand = energy_df[total_col].max()

    # 8. Calculate peak usage percentage
    peak_pct = _compute_peak_percentage(energy_df, total_col, rate_df)

    # 9. Find dominant appliances (top 3 by total consumption)
    # Divide by 4 to convert 15-min intervals to kWh
    appliance_totals = []
    for col in appliance_cols:
        if col in energy_df.columns:
            total = energy_df[col].sum() / 4  # Convert to kWh
            if total > 0:  # Only include appliances with actual consumption
                appliance_totals.append((col, total))

    appliance_totals.sort(key=lambda x: x[1], reverse=True)
    dominant = appliance_totals[:3]

    profile = HouseholdProfile(
        household_id=household_id,
        data_file=data_file,
        num_appliances=len(appliance_cols),
        avg_daily_consumption_kwh=round(avg_daily, 2),
        has_solar=has_solar,
        has_ev=has_ev,
        peak_usage_percentage=round(peak_pct, 1),
        data_start_date=start_date.strftime("%Y-%m-%d"),
        data_end_date=end_date.strftime("%Y-%m-%d"),
        data_timespan_days=timespan_days,
        dominant_appliances=[(name, round(kwh, 2)) for name, kwh in dominant],
        total_consumption_kwh=round(total_consumption, 2),
        peak_demand_kw=round(peak_demand, 3),
        appliance_list=appliance_cols,
    )

    logger.info(f"Household profile extracted: {household_id}, {len(appliance_cols)} appliances")
    return profile


def _compute_peak_percentage(
    energy_df: pd.DataFrame,
    total_col: str,
    rate_df: Optional[pd.DataFrame],
) -> float:
    """Compute percentage of consumption during peak hours.

    Args:
        energy_df: DataFrame with energy data
        total_col: Name of column with total consumption
        rate_df: Optional DataFrame with rate structure

    Returns:
        Percentage of total consumption during peak hours (0-100)
    """
    # Default peak hours if no rate data: 2 PM - 7 PM (14:00-19:00)
    DEFAULT_PEAK_START = 14
    DEFAULT_PEAK_END = 19

    df = energy_df.copy()
    df["_hour"] = pd.to_datetime(df["local_15min"]).dt.hour

    # Determine peak hours from rate data or use defaults
    peak_hours = list(range(DEFAULT_PEAK_START, DEFAULT_PEAK_END + 1))

    if rate_df is not None and "hour_start" in rate_df.columns:
        try:
            # Find peak rate hours from rate structure
            if "rate_kwh" in rate_df.columns:
                peak_rate = rate_df["rate_kwh"].max()
                peak_rows = rate_df[rate_df["rate_kwh"] == peak_rate]
                if len(peak_rows) > 0 and "hour_start" in peak_rows.columns:
                    peak_hours = peak_rows["hour_start"].tolist()
        except Exception as e:
            logger.warning(f"Could not extract peak hours from rate data: {e}")

    total = df[total_col].sum()
    if total <= 0:
        return 0.0

    peak_consumption = df[df["_hour"].isin(peak_hours)][total_col].sum()
    return (peak_consumption / total * 100)


def format_household_comparison(profiles: List[HouseholdProfile]) -> str:
    """Format a comparison of multiple household profiles.

    Args:
        profiles: List of HouseholdProfile objects to compare

    Returns:
        Formatted comparison string
    """
    if not profiles:
        return "No household profiles to compare."

    lines = [
        "=" * 70,
        "HOUSEHOLD COMPARISON",
        "=" * 70,
        "",
        f"{'Household':<12} {'Appliances':<12} {'Avg Daily':<12} {'Solar':<8} {'EV':<8} {'Peak %':<10}",
        "-" * 70,
    ]

    for p in profiles:
        lines.append(
            f"{p.household_id:<12} {p.num_appliances:<12} "
            f"{p.avg_daily_consumption_kwh:>8.1f} kWh  "
            f"{'Yes' if p.has_solar else 'No':<8} "
            f"{'Yes' if p.has_ev else 'No':<8} "
            f"{p.peak_usage_percentage:>6.1f}%"
        )

    lines.extend([
        "",
        "-" * 70,
        "Dominant Appliances:",
        "-" * 70,
    ])

    for p in profiles:
        dominant = ", ".join([f"{name}" for name, _ in p.dominant_appliances[:3]])
        lines.append(f"  {p.household_id}: {dominant}")

    lines.append("=" * 70)

    return "\n".join(lines)
