# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# scripts/test_scenarios/scenarios/period_comparison.py
"""PERIOD_COMPARISON category test scenarios - Phase 2: Period Comparison Queries."""
from ..models import TestScenario

# NOTE: Sample data has July 2023 (4447.72 kWh) and August 2023 (4488.36 kWh)
# July vs August: +0.9% increase

PERIOD_COMPARISON_SCENARIOS = [
    TestScenario(
        id="comp_001",
        name="Month vs Month Comparison - July vs August",
        category="period_comparison",
        input_message="Compare my usage in July vs August",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["comparison", "%"],
        expected_response="Comparing July to August 2023: July total was 4,447.72 kWh (143.47 kWh/day) and August total was 4,488.36 kWh (144.79 kWh/day). August usage was 0.9% higher than July, an increase of about 40 kWh. Both months show similar summer patterns dominated by HVAC usage.",
        description="Should compare current month to previous month",
    ),
    TestScenario(
        id="comp_002",
        name="Week vs Week Comparison",
        category="period_comparison",
        input_message="How does my usage this week compare to last week?",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["comparison", "%"],
        expected_response="Your weekly usage typically varies between 341 kWh (lowest week - W26) and 1,101 kWh (highest week - W32). The average weekly consumption is 904 kWh. Week-to-week variation depends on weather conditions affecting HVAC usage.",
        description="Should compare current week to previous week",
    ),
    TestScenario(
        id="comp_003",
        name="Best vs Worst Week Comparison",
        category="period_comparison",
        input_message="Compare my best week to my worst week",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["comparison", "%"],
        expected_response="Your best (lowest) week was Week 26 with 341.40 kWh total, and your worst (highest) week was Week 32 with 1,101.32 kWh. The worst week used 223% more energy than the best week, likely due to extreme heat requiring more HVAC usage.",
        description="Should compare two specific months",
    ),
    TestScenario(
        id="comp_004",
        name="Appliance Period Comparison - HVAC",
        category="period_comparison",
        input_message="Is my HVAC using more energy in August than July?",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["HVAC", "%"],
        expected_response="Your HVAC usage in August was slightly higher than July, consistent with the overall 0.9% increase in total consumption. HVAC accounts for about 58% of your total usage in both months, so any temperature differences directly impact your HVAC consumption.",
        description="Should compare appliance usage between periods",
    ),
    TestScenario(
        id="comp_005",
        name="Weekday vs Weekend Comparison",
        category="period_comparison",
        input_message="Compare my weekday energy use to weekend use",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["comparison", "%"],
        expected_response="Your weekend energy usage (148.48 kWh/day average) is 7.2% higher than your weekday usage (138.51 kWh/day average). This represents about 10 kWh more per day on weekends, likely due to increased home occupancy and appliance usage when you're home.",
        description="Should handle weekday vs weekend comparison",
    ),
]
