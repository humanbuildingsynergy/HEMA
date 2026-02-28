# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# scripts/test_scenarios/scenarios/multi_turn.py
"""MULTI_TURN category test scenarios - Context & Follow-up."""
from ..models import TestScenario

MULTI_TURN_SCENARIOS = [
    TestScenario(
        id="multi_001",
        name="Follow-up Pronoun Reference",
        category="multi_turn",
        input_message="Tell me more about that",
        expected_not_contains=["Error", "exception"],
        description="Pronoun reference without context - should handle gracefully",
    ),
    TestScenario(
        id="multi_002",
        name="Follow-up Question",
        category="multi_turn",
        input_message="What about the other one?",
        expected_not_contains=["Error", "exception"],
        description="Vague follow-up - should ask for clarification",
    ),
    TestScenario(
        id="multi_003",
        name="Continuation Request",
        category="multi_turn",
        input_message="Continue",
        expected_not_contains=["Error", "exception"],
        description="Continuation without context - should handle gracefully",
    ),
    TestScenario(
        id="multi_004",
        name="Yes Response",
        category="multi_turn",
        input_message="Yes",
        expected_not_contains=["Error", "exception"],
        description="Affirmative without context - should handle gracefully",
    ),
    TestScenario(
        id="multi_005",
        name="No Response",
        category="multi_turn",
        input_message="No",
        expected_not_contains=["Error", "exception"],
        description="Negative without context - should handle gracefully",
    ),
]
