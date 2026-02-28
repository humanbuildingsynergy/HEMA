# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# scripts/test_scenarios/scenarios/flexible_query.py
"""FLEXIBLE_QUERY category test scenarios - Phase 1: Natural Language Date Queries."""
from ..models import TestScenario

# NOTE: Sample dataset (energy_data_sample.csv) covers June 30 - Sep 1, 2023 (64 days)
# Total: 9043.95 kWh, Daily avg: 141.31 kWh
# July: 4447.72 kWh, August: 4488.36 kWh
# HVAC: 5248.97 kWh (58%), Pool pump: 2858.41 kWh (31.6%)

FLEXIBLE_QUERY_SCENARIOS = [
    # --- Natural Language Date Parsing ---
    TestScenario(
        id="flex_001",
        name="Query Last Week Usage",
        category="flexible_query",
        input_message="What was my energy usage last week?",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["kWh", "consumption"],
        expected_response="Your energy usage last week was approximately 900-1000 kWh total (based on your average weekly consumption of 904 kWh). Your daily average was around 141 kWh. The main contributors were HVAC (about 58% of usage) and pool pump (about 32%).",
        description="Should query data for the previous 7 days using natural language date",
    ),
    TestScenario(
        id="flex_002",
        name="Query Yesterday Usage",
        category="flexible_query",
        input_message="How much energy did I use yesterday?",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["kWh"],
        expected_response="Yesterday you used approximately 141 kWh of energy, which is close to your daily average. HVAC accounted for about 82 kWh (58%) and your pool pump used about 45 kWh (32%).",
        description="Should query data for yesterday using natural language date",
    ),
    TestScenario(
        id="flex_003",
        name="Query Last Month Usage",
        category="flexible_query",
        input_message="Show me my energy consumption last month",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["kWh"],
        expected_response="Your energy consumption last month was approximately 4,450-4,500 kWh total, with a daily average of about 143-145 kWh. HVAC was your largest consumer at 58%, followed by the pool pump at 32%. This is typical summer usage with heavy AC load.",
        description="Should query data for previous month using natural language date",
    ),
    TestScenario(
        id="flex_004",
        name="Query Specific Month - July",
        category="flexible_query",
        input_message="What was my energy usage in July?",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["kWh", "July"],
        expected_response="In July 2023, your total energy consumption was 4,447.72 kWh with a daily average of 143.47 kWh. Your HVAC system used approximately 2,580 kWh (58% of total), and your pool pump consumed about 1,405 kWh (31.6%).",
        description="Should query data for a specific month name",
    ),
    TestScenario(
        id="flex_005",
        name="Query Days Ago",
        category="flexible_query",
        input_message="What was my power consumption 3 days ago?",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["kWh"],
        expected_response="Your power consumption 3 days ago was approximately 141 kWh, which is near your typical daily average. HVAC and pool pump together accounted for about 90% of that usage.",
        description="Should handle relative date expressions like 'X days ago'",
    ),
    TestScenario(
        id="flex_006",
        name="Query This Week",
        category="flexible_query",
        input_message="How much energy have I used this week?",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["kWh"],
        expected_response="Your energy usage this week is approximately 900-1000 kWh so far, based on your average weekly consumption of 904 kWh. Daily usage averages around 141 kWh, with HVAC being the primary consumer.",
        description="Should query data for current week",
    ),

    # --- Appliance-Specific Time Queries ---
    TestScenario(
        id="flex_010",
        name="HVAC Usage Last Week",
        category="flexible_query",
        input_message="Show me my HVAC consumption last week",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["HVAC", "kWh"],
        expected_response="Your HVAC consumption last week was approximately 520-550 kWh, representing about 58% of your total energy usage. This averages to about 82 kWh per day for cooling. HVAC is your largest energy consumer, especially during summer months.",
        description="Should query specific appliance for a time period",
    ),
    TestScenario(
        id="flex_011",
        name="Pool Pump Usage Last Month",
        category="flexible_query",
        input_message="How much energy did my pool pump use last month?",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["pool pump", "kWh"],
        expected_response="Your pool pump used approximately 1,400-1,450 kWh last month, which is about 31.6% of your total energy consumption. The pool pump averages around 45 kWh per day and is your second largest energy consumer after HVAC.",
        description="Should query specific appliance for last month",
    ),
    TestScenario(
        id="flex_012",
        name="Multiple Appliances Query - HVAC and Pool",
        category="flexible_query",
        input_message="Show my HVAC and pool pump usage for August",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["kWh"],
        expected_response="In August, your HVAC used approximately 2,600 kWh (58% of total) and your pool pump used about 1,420 kWh (31.6%). Together, these two appliances accounted for nearly 90% of your August energy consumption of 4,488 kWh.",
        description="Should handle multiple appliances in one query",
    ),

    # --- Day/Time Filters ---
    TestScenario(
        id="flex_020",
        name="Morning Usage Query",
        category="flexible_query",
        input_message="What's my energy usage in the mornings?",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["kWh"],
        expected_response="Your morning energy usage (6 AM - 12 PM) averages approximately 35-40 kWh per day, which is about 25-28% of your daily consumption. Morning HVAC usage is typically lower as temperatures haven't peaked yet.",
        description="Should filter by time of day",
    ),
    TestScenario(
        id="flex_021",
        name="Weekend Only Query",
        category="flexible_query",
        input_message="Show me my weekend energy usage",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["weekend", "kWh"],
        expected_response="Your weekend energy usage averages 148.48 kWh per day, which is 7.2% higher than your weekday average of 138.51 kWh. This is likely due to increased home occupancy and appliance usage on weekends.",
        description="Should filter by weekend days only",
    ),
    TestScenario(
        id="flex_022",
        name="Weekday Only Query",
        category="flexible_query",
        input_message="What's my average weekday consumption?",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        expected_contains=["weekday", "kWh"],
        expected_response="Your average weekday consumption is 138.51 kWh per day. This is about 7% lower than your weekend usage of 148.48 kWh per day, likely because you're away from home during work hours.",
        description="Should filter by weekday days only",
    ),
]
