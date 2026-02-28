# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# scripts/test_scenarios/scenarios/aggregation.py
"""AGGREGATION category test scenarios - Phase 3: Advanced Aggregation Queries."""
from ..models import TestScenario

# NOTE: Sample data statistics:
# - Weekly avg: 904.39 kWh, Best W26: 341.40 kWh, Worst W32: 1101.32 kWh
# - Monthly: July 4447.72 kWh, August 4488.36 kWh
# - Weekday avg: 138.51 kWh/day, Weekend avg: 148.48 kWh/day (+7.2%)
# - Peak hours (2-8PM): 2394.73 kWh (26.5%)
# - Rolling 7-day trend: Increasing (+8.2%)

AGGREGATION_SCENARIOS = [
    # --- Weekly Aggregation ---
    TestScenario(
        id="agg_001",
        name="Weekly Usage Summary",
        category="aggregation",
        input_message="Show my weekly energy usage",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["weekly", "kWh"],
        expected_response="Your weekly energy usage summary: Average weekly consumption is 904 kWh. Week 26 had the lowest usage at 341 kWh, while Week 32 had the highest at 1,101 kWh. Weekly variations are primarily driven by HVAC load responding to outdoor temperatures.",
        description="Should show weekly aggregated consumption",
    ),
    TestScenario(
        id="agg_002",
        name="Best and Worst Weeks",
        category="aggregation",
        input_message="Which weeks did I use the most and least energy?",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["week", "kWh"],
        expected_response="Your best (lowest) week was Week 26 with 341.40 kWh total. Your worst (highest) week was Week 32 with 1,101.32 kWh total. The difference of 760 kWh represents a 223% variation, primarily due to HVAC usage differences during varying weather conditions.",
        description="Should identify best and worst weeks",
    ),

    # --- Monthly Aggregation ---
    TestScenario(
        id="agg_010",
        name="Monthly Usage Summary",
        category="aggregation",
        input_message="What's my monthly consumption pattern?",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["monthly", "kWh"],
        expected_response="Your monthly consumption pattern shows: July 2023: 4,447.72 kWh (143.47 kWh/day), August 2023: 4,488.36 kWh (144.79 kWh/day). August was slightly higher (+0.9%) than July. Both months reflect heavy summer HVAC usage accounting for 58% of consumption.",
        description="Should show monthly aggregated consumption",
    ),
    TestScenario(
        id="agg_011",
        name="Best and Worst Months",
        category="aggregation",
        input_message="Which month did I use the most energy?",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["month", "kWh"],
        expected_response="August 2023 was your highest consumption month at 4,488.36 kWh (144.79 kWh/day average). July 2023 was slightly lower at 4,447.72 kWh (143.47 kWh/day). The difference of about 40 kWh is minimal, as both are summer months with similar HVAC demands.",
        description="Should identify highest consumption month",
    ),

    # --- Seasonal Aggregation ---
    TestScenario(
        id="agg_020",
        name="Seasonal Comparison - Summer Only",
        category="aggregation",
        input_message="What was my summer energy usage?",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["summer", "kWh"],
        expected_response="Your summer energy usage (July-August 2023) totaled 8,936.08 kWh over 64 days, averaging 139.63 kWh per day. HVAC accounted for 58% of this usage (about 5,183 kWh), driven by air conditioning needs. The pool pump contributed 31.6% (about 2,824 kWh).",
        description="Should compare seasonal consumption patterns",
    ),
    TestScenario(
        id="agg_021",
        name="Seasonal Breakdown",
        category="aggregation",
        input_message="Show my energy usage by season",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["season", "kWh"],
        expected_response="Your available data covers summer 2023 only (June 30 - September 1). Summer total: 9,043.95 kWh over 64 days (141.31 kWh/day average). During summer, HVAC dominates at 58% of usage, followed by pool pump at 31.6%. Winter/spring/fall data not available in current dataset.",
        description="Should break down usage by all seasons",
    ),

    # --- Rolling Averages ---
    TestScenario(
        id="agg_030",
        name="7-Day Rolling Average",
        category="aggregation",
        input_message="What's my 7-day rolling average consumption?",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["average", "kWh"],
        expected_response="Your 7-day rolling average consumption is approximately 141 kWh per day. The trend shows an increasing pattern (+8.2% over the data period), indicating slightly rising energy usage over time, likely correlated with peak summer temperatures.",
        description="Should calculate 7-day rolling average",
    ),
    TestScenario(
        id="agg_031",
        name="30-Day Rolling Average",
        category="aggregation",
        input_message="Show me my 30-day average energy use",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["average", "kWh"],
        expected_response="Your 30-day rolling average energy use is approximately 141-145 kWh per day. July averaged 143.47 kWh/day and August averaged 144.79 kWh/day, showing consistent summer consumption patterns with HVAC as the primary driver.",
        description="Should calculate 30-day rolling average",
    ),
    TestScenario(
        id="agg_032",
        name="Usage Trend Detection",
        category="aggregation",
        input_message="Is my energy usage trending up or down?",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["trend"],
        expected_response="Your energy usage is trending upward with an 8.2% increase over the monitoring period. This upward trend is consistent with peak summer temperatures requiring more HVAC cooling. Weekly highs reached 1,101 kWh in Week 32 compared to 341 kWh in Week 26.",
        description="Should detect and report consumption trends",
    ),

    # --- Weekday/Weekend Comparison ---
    TestScenario(
        id="agg_040",
        name="Weekday vs Weekend Detailed",
        category="aggregation",
        input_message="Compare my weekday and weekend energy usage in detail",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["weekday", "weekend", "kWh"],
        expected_response="Detailed weekday vs weekend comparison: Weekday average: 138.51 kWh/day. Weekend average: 148.48 kWh/day. Weekends are 7.2% higher (about 10 kWh more per day). This pattern suggests increased home occupancy on weekends leading to higher HVAC and appliance usage.",
        description="Should provide detailed weekday vs weekend comparison",
    ),
    TestScenario(
        id="agg_041",
        name="Weekend Premium Analysis",
        category="aggregation",
        input_message="Do I use more energy on weekends?",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["weekend", "%"],
        expected_response="Yes, you use 7.2% more energy on weekends. Weekend daily average is 148.48 kWh compared to weekday average of 138.51 kWh. This approximately 10 kWh difference per day is typical for households where occupants are home more on weekends, using more HVAC and appliances.",
        description="Should compare weekend to weekday with percentage",
    ),

    # --- Peak Hour Analysis ---
    TestScenario(
        id="agg_050",
        name="Peak vs Off-Peak Analysis",
        category="aggregation",
        input_message="How much energy do I use during peak hours?",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["peak", "kWh", "%"],
        expected_response="During peak hours (2 PM - 8 PM), you used 2,394.73 kWh total, which is 26.5% of your overall consumption. Off-peak usage accounts for 73.5% (6,649.22 kWh). Shifting more usage to off-peak hours could reduce your electricity costs significantly under TOU pricing.",
        description="Should analyze peak vs off-peak consumption",
    ),
    TestScenario(
        id="agg_051",
        name="Peak Hour Percentage",
        category="aggregation",
        input_message="What percentage of my usage is during peak hours?",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["peak", "%"],
        expected_response="26.5% of your energy usage (2,394.73 kWh) occurs during peak hours (2 PM - 8 PM). This is relatively good as peak hours are only 25% of the day, meaning your usage is roughly proportional. HVAC cooling during afternoon peaks is the main contributor to peak-hour consumption.",
        description="Should calculate peak hour usage percentage",
    ),
    TestScenario(
        id="agg_052",
        name="Off-Peak Opportunity",
        category="aggregation",
        input_message="How can I shift more usage to off-peak hours?",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["off-peak"],
        expected_response="To shift usage to off-peak hours: 1) Pre-cool your home before 2 PM peak period starts. 2) Run your pool pump early morning or late evening instead of afternoon. 3) Schedule high-energy tasks like laundry and dishwashing for after 8 PM. Your pool pump (31.6% of usage) offers the best opportunity for shifting.",
        description="Should provide peak/off-peak insights for shifting",
    ),

    # --- Appliance-Specific Aggregations ---
    TestScenario(
        id="agg_060",
        name="HVAC Weekly Breakdown",
        category="aggregation",
        input_message="Show my HVAC usage broken down by week",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["HVAC", "kWh"],
        expected_response="Your HVAC weekly breakdown shows an average of about 524 kWh per week (58% of total weekly usage). HVAC usage correlates with outdoor temperatures - during your highest week (W32), HVAC likely consumed around 640 kWh. During your lowest week (W26), HVAC used approximately 198 kWh.",
        description="Should aggregate specific appliance by week",
    ),
    TestScenario(
        id="agg_061",
        name="HVAC Summer Usage",
        category="aggregation",
        input_message="How much energy did my HVAC use this summer?",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["HVAC", "kWh"],
        expected_response="Your HVAC used 5,248.97 kWh this summer (July-August), accounting for 58% of your total energy consumption. This averages to about 82 kWh per day for cooling. The high HVAC usage is typical for summer months in hot climates where air conditioning runs frequently.",
        description="Should show appliance seasonal patterns",
    ),
]
