# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/specialized/analysis_agent.py
"""Analysis Agent - handles energy data analysis tasks."""
from langgraph.prebuilt import create_react_agent

from agents.prompts import ANALYSIS_AGENT_SYSTEM_PROMPT
from agents.tools.analysis_tools import (
    # Data tools
    list_available_data,
    get_tracked_appliances,
    get_utility_rate,
    load_energy_data,
    # Consumption tools
    analyze_consumption,
    analyze_appliances,
    analyze_utility_rate,
    get_analysis_summary,
    # Query tools
    query_energy_data,
    compare_energy_periods,
    # Aggregation tools (unified flexible aggregation)
    analyze_energy_period,
    calculate_rolling_average,
    compare_weekday_weekend,
    analyze_peak_hours,
    # Frequency and variability tools
    analyze_usage_frequency,
    analyze_usage_variability,
    # Solar tools
    analyze_solar_availability,
    analyze_solar_alignment,
)
from config.llm_factory import create_llm_with_cascade
from utils.logger import setup_logger

logger = setup_logger()



def create_analysis_agent():
    """
    Create the Analysis Agent with energy analysis tools.

    Returns:
        A compiled ReAct agent graph ready for invocation.
    """
    logger.info("Creating Analysis Agent")

    try:
        # Create LLM using cascade (tries multiple providers/models)
        llm = create_llm_with_cascade()
    except (ValueError, ImportError) as e:
        logger.warning(f"Failed to create LLM for Analysis Agent: {e}")
        return None

    # Define tools
    tools = [
        # Data access tools (no loading required)
        list_available_data,
        get_tracked_appliances,
        get_utility_rate,
        # Data loading
        load_energy_data,
        # Standard analysis
        analyze_consumption,
        analyze_appliances,
        analyze_utility_rate,
        get_analysis_summary,
        # Flexible query tools
        query_energy_data,
        compare_energy_periods,
        # Aggregation tools (unified flexible aggregation)
        analyze_energy_period,
        calculate_rolling_average,
        compare_weekday_weekend,
        analyze_peak_hours,
        # Usage frequency and variability tools
        analyze_usage_frequency,
        analyze_usage_variability,
        # Solar tools
        analyze_solar_availability,
        analyze_solar_alignment,
    ]

    # Create the ReAct agent
    agent = create_react_agent(
        llm,
        tools,
        prompt=ANALYSIS_AGENT_SYSTEM_PROMPT,
    )

    logger.info("Analysis Agent created with tools: " + ", ".join(t.name for t in tools))
    return agent
