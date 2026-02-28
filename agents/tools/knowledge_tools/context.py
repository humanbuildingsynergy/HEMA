# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/tools/knowledge_tools/context.py
"""User context tool for Knowledge Agent to access loaded energy data."""

from typing import Any, Dict, List
from langchain_core.tools import tool

from agents.tools.analysis_tools.cache import get_data_cache


def _format_top_consumers(rankings: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
    """Format top consumers from analysis results into a concise summary."""
    result = []
    for item in rankings[:limit]:
        result.append({
            "appliance": item.get("appliance", "Unknown"),
            "kwh": round(item.get("total_kwh", 0), 1),
            "percentage": round(item.get("percentage", 0), 1),
        })
    return result


@tool
def get_user_context() -> Dict[str, Any]:
    """Get the current user's energy data context if available.

    Use this tool BEFORE giving energy advice to check if you can personalize
    your recommendations based on the user's actual data.

    Returns a summary of:
    - Whether energy data is loaded
    - What appliances are tracked
    - Key consumption highlights (top appliances with kWh and percentages)
    - Rate type (TOU or flat) and solar status

    Example usage:
    - User asks "tips for reducing my energy bill?"
    - Call this tool first
    - If data_loaded=True, tailor your advice to their specific appliances
    - If data_loaded=False, provide general energy-saving tips
    """
    cache = get_data_cache()

    # Check if energy data is loaded
    energy_df = cache.get("energy_df")
    if energy_df is None:
        return {
            "data_loaded": False,
            "message": "No energy data loaded for this user. Provide general advice.",
        }

    # Build context summary from cached data
    result = {
        "data_loaded": True,
        "rate_type": cache.get("rate_type"),  # "tou" or "flat"
        "has_solar": cache.get("has_solar"),  # True/False
    }

    # Get tracked appliances (column names excluding timestamp columns)
    try:
        # Filter out common non-appliance columns
        exclude_cols = {"local_15min", "timestamp", "dataid", "localminute", "date", "time"}
        appliance_cols = [
            col for col in energy_df.columns
            if col.lower() not in exclude_cols and not col.startswith("Unnamed")
        ]
        result["tracked_appliances"] = appliance_cols
    except Exception:
        result["tracked_appliances"] = []

    # Get analysis results if available
    analysis_results = cache.get("analysis_results") or {}

    # Extract top consumers from appliance analysis
    appliance_analysis = analysis_results.get("appliances", {})
    rankings = appliance_analysis.get("consumption_rankings", [])
    if rankings:
        result["top_consumers"] = _format_top_consumers(rankings)
    else:
        result["top_consumers"] = []

    # Extract consumption summary if available
    consumption_analysis = analysis_results.get("consumption", {})
    if consumption_analysis:
        summary = consumption_analysis.get("summary", {})
        result["consumption_summary"] = {
            "total_kwh": round(summary.get("total_kwh", 0), 1),
            "avg_daily_kwh": round(summary.get("avg_daily_kwh", 0), 1),
            "peak_demand_kw": round(summary.get("peak_demand_kw", 0), 2),
        }
    else:
        result["consumption_summary"] = {}

    return result
