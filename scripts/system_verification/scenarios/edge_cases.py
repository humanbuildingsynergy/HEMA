# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# scripts/test_scenarios/scenarios/edge_cases.py
"""EDGE_CASES category test scenarios - Error Handling, Ambiguous, Invalid."""
from ..models import TestScenario

EDGE_CASES_SCENARIOS = [
    # --- Ambiguous Queries ---
    TestScenario(
        id="edge_001",
        name="Ambiguous TOU Query",
        category="edge_cases",
        input_message="Tell me about TOU rates",
        expected_agent=None,
        expected_not_contains=["Error", "error", "failed"],
        description="Ambiguous query - may trigger clarification",
    ),
    TestScenario(
        id="edge_002",
        name="Ambiguous Energy Question",
        category="edge_cases",
        input_message="I want to save energy",
        expected_not_contains=["Error", "error"],
        description="Could be general tips or personal analysis",
    ),
    TestScenario(
        id="edge_003",
        name="Mixed Intent Query",
        category="edge_cases",
        input_message="What is TOU pricing and how much am I paying?",
        expected_not_contains=["Error", "error"],
        description="Query with both general and personal aspects",
    ),
    TestScenario(
        id="edge_004",
        name="Control + Analysis Mix",
        category="edge_cases",
        input_message="Set my thermostat based on my peak usage hours",
        expected_not_contains=["Error", "error"],
        description="Query mixing control action with analysis",
    ),
    TestScenario(
        id="edge_005",
        name="Vague Analysis Request",
        category="edge_cases",
        input_message="Help me with my energy",
        expected_not_contains=["Error", "exception"],
        description="Vague request - should clarify or provide options",
    ),

    # --- Invalid/Edge Inputs ---
    TestScenario(
        id="edge_010",
        name="Very Short Query",
        category="edge_cases",
        input_message="rates",
        expected_not_contains=["Error", "error", "exception"],
        description="Very short query - should handle gracefully",
    ),
    TestScenario(
        id="edge_011",
        name="Nonsense Input",
        category="edge_cases",
        input_message="asdfghjkl qwerty",
        expected_not_contains=["exception", "traceback"],
        description="Random characters - should ask for clarification",
    ),
    TestScenario(
        id="edge_012",
        name="Empty-like Query",
        category="edge_cases",
        input_message="...",
        expected_not_contains=["exception", "traceback"],
        description="Punctuation-only input - should handle gracefully",
    ),
    TestScenario(
        id="edge_013",
        name="Numbers Only",
        category="edge_cases",
        input_message="123456",
        expected_not_contains=["exception", "traceback"],
        description="Numeric input only - should handle gracefully",
    ),
    TestScenario(
        id="edge_014",
        name="Special Characters",
        category="edge_cases",
        input_message="@#$%^&*()",
        expected_not_contains=["exception", "traceback"],
        description="Special characters - should handle gracefully",
    ),
    TestScenario(
        id="edge_015",
        name="Very Long Query",
        category="edge_cases",
        input_message="I want to know about my energy consumption and also "
                      "understand TOU rates and how they work and also control "
                      "my thermostat and get recommendations for saving money "
                      "on my electricity bill while also learning about solar "
                      "panels and whether I should get battery storage",
        expected_not_contains=["Error", "error", "exception"],
        description="Very long multi-topic query - should handle gracefully",
    ),

    # --- Nonexistent/Invalid Device ---
    TestScenario(
        id="edge_020",
        name="Nonexistent Device",
        category="edge_cases",
        input_message="What's the status of my smart toaster?",
        expected_agent="control_agent",
        expected_scope="ACTION",
        expected_contains=["not found", "available"],
        description="Query about nonexistent device - should indicate not found",
    ),
    TestScenario(
        id="edge_021",
        name="Invalid Device Name",
        category="edge_cases",
        input_message="Turn on my quantum reactor",
        expected_agent="control_agent",
        expected_scope="ACTION",
        expected_contains=["not found", "available"],
        description="Invalid device name - should indicate not found with alternatives",
    ),
    TestScenario(
        id="edge_022",
        name="Misspelled Device",
        category="edge_cases",
        input_message="Check my thermostt",
        expected_agent="control_agent",
        expected_scope="ACTION",
        description="Misspelled device - should handle with fuzzy matching",
    ),

    # --- Invalid Control Parameters ---
    TestScenario(
        id="edge_030",
        name="Temperature Out of Range - High",
        category="edge_cases",
        input_message="Set temperature to 150 degrees",
        expected_agent="control_agent",
        expected_scope="ACTION",
        expected_contains=["range", "valid"],
        description="Temperature too high - should indicate valid range",
    ),
    TestScenario(
        id="edge_031",
        name="Temperature Out of Range - Low",
        category="edge_cases",
        input_message="Set thermostat to 30 degrees",
        expected_agent="control_agent",
        expected_scope="ACTION",
        expected_contains=["range", "valid"],
        description="Temperature too low - should indicate valid range",
    ),
    TestScenario(
        id="edge_032",
        name="Invalid EV Charge Limit",
        category="edge_cases",
        input_message="Set my EV charge limit to 200%",
        expected_agent="control_agent",
        expected_scope="ACTION",
        expected_contains=["100", "limit"],
        description="Invalid charge limit - should indicate valid range",
    ),
    TestScenario(
        id="edge_033",
        name="Invalid Mode",
        category="edge_cases",
        input_message="Set thermostat to turbo mode",
        expected_agent="control_agent",
        expected_scope="ACTION",
        expected_contains=["mode", "valid"],
        description="Invalid mode - should indicate valid options",
    ),
]
