# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# core/analysis/period_comparison.py
"""Period comparison engine for comparing energy data between time periods."""
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from .flexible_query import FlexibleQueryEngine


class PeriodComparisonEngine:
    """
    Engine for comparing energy data between two time periods.
    """

    def __init__(self, df: pd.DataFrame, rate_df: Optional[pd.DataFrame] = None):
        """
        Initialize the comparison engine.

        Args:
            df: DataFrame with energy data
            rate_df: Optional rate data for cost calculations
        """
        self.query_engine = FlexibleQueryEngine(df, rate_df)

    def compare(
        self,
        period1_start: Union[str, datetime],
        period1_end: Union[str, datetime],
        period2_start: Union[str, datetime],
        period2_end: Union[str, datetime],
        comparison_type: str = "total",
        appliances: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Compare energy metrics between two time periods.

        Args:
            period1_start: Start of first period
            period1_end: End of first period
            period2_start: Start of second period
            period2_end: End of second period
            comparison_type: Type of comparison ("total", "average", "peak", "pattern")
            appliances: Optional list of appliances to compare

        Returns:
            Dict with comparison results
        """
        # Query both periods
        result1 = self.query_engine.query(
            start_date=period1_start,
            end_date=period1_end,
            aggregation="daily",
            appliances=appliances,
        )

        result2 = self.query_engine.query(
            start_date=period2_start,
            end_date=period2_end,
            aggregation="daily",
            appliances=appliances,
        )

        if not result1.get("success") or not result2.get("success"):
            return {
                "success": False,
                "error": "Failed to query one or both periods",
                "period1_error": result1.get("error"),
                "period2_error": result2.get("error"),
            }

        stats1 = result1["statistics"]
        stats2 = result2["statistics"]

        # Calculate differences
        total_diff = stats2["total_consumption_kwh"] - stats1["total_consumption_kwh"]
        total_pct_change = (total_diff / max(stats1["total_consumption_kwh"], 0.01)) * 100

        avg_diff = stats2["average_daily_kwh"] - stats1["average_daily_kwh"]
        avg_pct_change = (avg_diff / max(stats1["average_daily_kwh"], 0.01)) * 100

        peak_diff = stats2["peak_power_kw"] - stats1["peak_power_kw"]
        peak_pct_change = (peak_diff / max(stats1["peak_power_kw"], 0.01)) * 100

        comparison = {
            "success": True,
            "period1": {
                "start": result1["query_params"]["start_date"],
                "end": result1["query_params"]["end_date"],
                "days": stats1["num_days"],
                "total_kwh": stats1["total_consumption_kwh"],
                "avg_daily_kwh": stats1["average_daily_kwh"],
                "peak_kw": stats1["peak_power_kw"],
            },
            "period2": {
                "start": result2["query_params"]["start_date"],
                "end": result2["query_params"]["end_date"],
                "days": stats2["num_days"],
                "total_kwh": stats2["total_consumption_kwh"],
                "avg_daily_kwh": stats2["average_daily_kwh"],
                "peak_kw": stats2["peak_power_kw"],
            },
            "comparison": {
                "total_consumption": {
                    "difference_kwh": round(total_diff, 2),
                    "percent_change": round(total_pct_change, 1),
                    "direction": "increased" if total_diff > 0 else "decreased" if total_diff < 0 else "unchanged",
                },
                "average_daily": {
                    "difference_kwh": round(avg_diff, 2),
                    "percent_change": round(avg_pct_change, 1),
                    "direction": "increased" if avg_diff > 0 else "decreased" if avg_diff < 0 else "unchanged",
                },
                "peak_power": {
                    "difference_kw": round(peak_diff, 3),
                    "percent_change": round(peak_pct_change, 1),
                    "direction": "increased" if peak_diff > 0 else "decreased" if peak_diff < 0 else "unchanged",
                },
            },
        }

        # Add appliance breakdown comparison if requested
        if appliances and "appliance_breakdown" in result1 and "appliance_breakdown" in result2:
            comparison["appliance_comparison"] = self._compare_appliances(
                result1["appliance_breakdown"],
                result2["appliance_breakdown"]
            )

        # Generate insights
        comparison["insights"] = self._generate_comparison_insights(comparison)

        # Add warning for unequal period lengths
        period1_days = stats1["num_days"]
        period2_days = stats2["num_days"]

        if period1_days > 0 and period2_days > 0:
            ratio = max(period1_days, period2_days) / min(period1_days, period2_days)
            if ratio > 2:  # One period is more than 2x longer than the other
                comparison["warning"] = {
                    "type": "unequal_periods",
                    "message": (
                        f"Warning: Period 1 has {period1_days} days while Period 2 has {period2_days} days. "
                        f"Total consumption comparisons may be misleading. "
                        f"Use average daily consumption for fairer comparison."
                    ),
                    "period1_days": period1_days,
                    "period2_days": period2_days,
                    "recommendation": "Compare avg_daily_kwh instead of total_kwh"
                }
                # Add warning to the front of insights
                comparison["insights"].insert(
                    0,
                    f"⚠️ Unequal periods: {period1_days} days vs {period2_days} days - use daily averages for fair comparison"
                )

        return comparison

    def _compare_appliances(
        self,
        breakdown1: Dict[str, Dict[str, float]],
        breakdown2: Dict[str, Dict[str, float]]
    ) -> Dict[str, Dict[str, Any]]:
        """Compare appliance breakdowns between periods."""
        comparison = {}

        all_appliances = set(breakdown1.keys()) | set(breakdown2.keys())

        for appliance in all_appliances:
            data1 = breakdown1.get(appliance, {"total_kwh": 0})
            data2 = breakdown2.get(appliance, {"total_kwh": 0})

            diff = data2["total_kwh"] - data1["total_kwh"]
            pct_change = (diff / max(data1["total_kwh"], 0.01)) * 100 if data1["total_kwh"] > 0 else 0

            comparison[appliance] = {
                "period1_kwh": data1["total_kwh"],
                "period2_kwh": data2["total_kwh"],
                "difference_kwh": round(diff, 2),
                "percent_change": round(pct_change, 1),
            }

        return comparison

    def _generate_comparison_insights(self, comparison: Dict[str, Any]) -> List[str]:
        """Generate human-readable insights from comparison."""
        insights = []

        comp = comparison["comparison"]

        # Total consumption insight
        total = comp["total_consumption"]
        if abs(total["percent_change"]) > 5:
            insights.append(
                f"Total consumption {total['direction']} by {abs(total['percent_change']):.1f}% "
                f"({abs(total['difference_kwh']):.1f} kWh)"
            )

        # Daily average insight
        avg = comp["average_daily"]
        if abs(avg["percent_change"]) > 5:
            insights.append(
                f"Daily average {avg['direction']} by {abs(avg['percent_change']):.1f}% "
                f"({abs(avg['difference_kwh']):.1f} kWh/day)"
            )

        # Peak power insight
        peak = comp["peak_power"]
        if abs(peak["percent_change"]) > 10:
            insights.append(
                f"Peak power {peak['direction']} by {abs(peak['percent_change']):.1f}% "
                f"({abs(peak['difference_kw']):.2f} kW)"
            )

        # Appliance-specific insights
        if "appliance_comparison" in comparison:
            for appliance, data in comparison["appliance_comparison"].items():
                if abs(data["percent_change"]) > 20:
                    direction = "increased" if data["difference_kwh"] > 0 else "decreased"
                    insights.append(
                        f"{appliance} {direction} by {abs(data['percent_change']):.1f}%"
                    )

        if not insights:
            insights.append("Consumption remained relatively stable between the two periods")

        return insights
