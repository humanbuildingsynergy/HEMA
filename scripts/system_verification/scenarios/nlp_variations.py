# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# scripts/test_scenarios/scenarios/nlp_variations.py
"""NLP_VARIATIONS category test scenarios - Natural Language Variations."""
from ..models import TestScenario

NLP_VARIATIONS_SCENARIOS = [
    TestScenario(
        id="nlp_001",
        name="Polite Request Form",
        category="nlp_variations",
        input_message="Could you please show me my energy usage?",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        description="Polite phrasing should route correctly",
    ),
    TestScenario(
        id="nlp_002",
        name="Question Form",
        category="nlp_variations",
        input_message="Can you analyze my electricity consumption?",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        description="Question form should route correctly",
    ),
    TestScenario(
        id="nlp_003",
        name="Command Form",
        category="nlp_variations",
        input_message="Analyze my energy data now",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        description="Command form should route correctly",
    ),
    TestScenario(
        id="nlp_004",
        name="Casual Phrasing",
        category="nlp_variations",
        input_message="yo what's my power bill looking like",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        description="Casual language should route correctly",
    ),
    TestScenario(
        id="nlp_005",
        name="Typo Tolerance",
        category="nlp_variations",
        input_message="analzye my enregy consumtion",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        description="Typos should be handled gracefully",
    ),
    TestScenario(
        id="nlp_006",
        name="All Caps",
        category="nlp_variations",
        input_message="WHAT IS MY ENERGY USAGE?",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        description="All caps should route correctly",
    ),
    TestScenario(
        id="nlp_007",
        name="Mixed Case",
        category="nlp_variations",
        input_message="WhAt Is My EnErGy UsAgE?",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        description="Mixed case should route correctly",
    ),
    TestScenario(
        id="nlp_008",
        name="Indirect Request",
        category="nlp_variations",
        input_message="I was wondering if you could tell me about my energy costs",
        expected_agent="analysis_agent",
        expected_scope="PERSONAL",
        description="Indirect phrasing should route correctly",
    ),
]
