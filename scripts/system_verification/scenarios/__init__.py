# scripts/system_verification/scenarios/__init__.py
"""Collect all verification test scenarios from category modules."""
from typing import List

from ..models import TestScenario

from .conversation import CONVERSATION_SCENARIOS
from .classification import CLASSIFICATION_SCENARIOS
from .control import CONTROL_SCENARIOS
from .analysis import ANALYSIS_SCENARIOS
from .knowledge import KNOWLEDGE_SCENARIOS
from .edge_cases import EDGE_CASES_SCENARIOS
from .multi_turn import MULTI_TURN_SCENARIOS
from .safety import SAFETY_SCENARIOS
from .nlp_variations import NLP_VARIATIONS_SCENARIOS
from .flexible_query import FLEXIBLE_QUERY_SCENARIOS
from .period_comparison import PERIOD_COMPARISON_SCENARIOS
from .aggregation import AGGREGATION_SCENARIOS
from .weather import WEATHER_SCENARIOS

# Combine all scenarios
TEST_SCENARIOS: List[TestScenario] = [
    *CONVERSATION_SCENARIOS,
    *CLASSIFICATION_SCENARIOS,
    *CONTROL_SCENARIOS,
    *ANALYSIS_SCENARIOS,
    *KNOWLEDGE_SCENARIOS,
    *EDGE_CASES_SCENARIOS,
    *MULTI_TURN_SCENARIOS,
    *SAFETY_SCENARIOS,
    *NLP_VARIATIONS_SCENARIOS,
    *FLEXIBLE_QUERY_SCENARIOS,
    *PERIOD_COMPARISON_SCENARIOS,
    *AGGREGATION_SCENARIOS,
    *WEATHER_SCENARIOS,
]

# List of available categories
CATEGORIES = [
    "conversation",
    "classification",
    "control",
    "analysis",
    "knowledge",
    "edge_cases",
    "multi_turn",
    "safety",
    "nlp_variations",
    "flexible_query",
    "period_comparison",
    "aggregation",
    "weather",
]

__all__ = [
    "TEST_SCENARIOS",
    "CATEGORIES",
    "CONVERSATION_SCENARIOS",
    "CLASSIFICATION_SCENARIOS",
    "CONTROL_SCENARIOS",
    "ANALYSIS_SCENARIOS",
    "KNOWLEDGE_SCENARIOS",
    "EDGE_CASES_SCENARIOS",
    "MULTI_TURN_SCENARIOS",
    "SAFETY_SCENARIOS",
    "NLP_VARIATIONS_SCENARIOS",
    "FLEXIBLE_QUERY_SCENARIOS",
    "PERIOD_COMPARISON_SCENARIOS",
    "AGGREGATION_SCENARIOS",
    "WEATHER_SCENARIOS",
]
