# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/validation_tests/scenarios.py
"""
Validation scenarios for the LLM-as-user evaluation framework.

Each scenario pairs a persona with a goal-oriented task to validate that
the simulated user, HEMA, and evaluator interact correctly.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ValidationScenario:
    """Defines a framework validation scenario."""

    id: str
    name: str
    description: str

    # Which persona and scenario to use from the main config
    persona_id: str
    scenario_id: str

    # What this validation test checks
    validation_focus: List[str]  # ["goal_completion", "persona_consistency", etc.]

    # Expected behavior (for validation)
    expect_goal_completion: bool  # Should user eventually signal goal met?
    max_acceptable_errors: int  # How many errors are tolerable

    # Optional notes for interpretation
    notes: Optional[str] = None


# =============================================================================
# VALIDATION SCENARIOS
# =============================================================================

VALIDATION_SCENARIOS: List[ValidationScenario] = [
    # Test 1: Basic goal completion with novice user
    ValidationScenario(
        id="novice_tou_understanding",
        name="Novice User Understanding TOU Rates",
        description=(
            "A confused newcomer asks about TOU rates. Tests whether the "
            "simulated user can navigate from confusion to understanding "
            "and appropriately signal goal completion."
        ),
        persona_id="confused_newcomer",
        scenario_id="understand_utility_rate",
        validation_focus=[
            "goal_completion",
            "conversation_coherence",
            "evaluator_validity",
        ],
        expect_goal_completion=True,
        max_acceptable_errors=0,
        notes="Core test - if this fails, the framework has fundamental issues.",
    ),

    # Test 2: Expert user with technical questions
    ValidationScenario(
        id="expert_appliance_analysis",
        name="Expert User Analyzing Appliances",
        description=(
            "A tech-savvy user asks detailed questions about appliance energy "
            "usage. Tests whether the simulated user maintains expert-level "
            "discourse and asks appropriate follow-up questions."
        ),
        persona_id="tech_savvy_optimizer",
        scenario_id="appliance_analysis",
        validation_focus=[
            "persona_consistency",
            "technical_depth",
            "conversation_coherence",
        ],
        expect_goal_completion=True,
        max_acceptable_errors=0,
        notes="Expert users should ask detailed follow-ups, not accept surface answers.",
    ),

    # Test 3: Skeptical user requiring trust-building
    ValidationScenario(
        id="skeptic_hvac_advice",
        name="Skeptical Senior Seeking HVAC Advice",
        description=(
            "A skeptical senior asks about HVAC optimization. Tests whether "
            "the simulated user maintains skepticism appropriately and whether "
            "HEMA can address concerns patiently."
        ),
        persona_id="skeptical_senior",
        scenario_id="hvac_optimization",
        validation_focus=[
            "persona_consistency",
            "skepticism_maintenance",
            "conversation_flow",
        ],
        expect_goal_completion=True,  # Should eventually warm up
        max_acceptable_errors=0,
        notes="User should express doubt initially but warm up if HEMA is patient.",
    ),

    # Test 4: Budget-conscious user with practical constraints
    ValidationScenario(
        id="parent_peak_reduction",
        name="Busy Parent Reducing Peak Usage",
        description=(
            "A budget-conscious parent wants to reduce peak hour usage. "
            "Tests whether the simulated user appropriately mentions constraints "
            "and focuses on practical solutions."
        ),
        persona_id="budget_conscious_parent",
        scenario_id="peak_reduction_strategy",
        validation_focus=[
            "constraint_awareness",
            "practical_focus",
            "goal_completion",
        ],
        expect_goal_completion=True,
        max_acceptable_errors=0,
        notes="User should mention time/budget constraints and ask about savings.",
    ),

    # Test 5: Environmental user with renter constraints
    ValidationScenario(
        id="renter_weather_impact",
        name="Eco-Conscious Renter and Weather",
        description=(
            "An environmentally-focused renter asks about weather impact on "
            "energy. Tests whether the simulated user frames questions in terms "
            "of environmental impact and mentions renter limitations."
        ),
        persona_id="eco_conscious_renter",
        scenario_id="weather_energy_impact",
        validation_focus=[
            "environmental_framing",
            "constraint_awareness",
            "conversation_coherence",
        ],
        expect_goal_completion=True,
        max_acceptable_errors=0,
        notes="User should ask about carbon footprint, not just cost savings.",
    ),

    # Test 6: Complex multi-turn investigation
    ValidationScenario(
        id="novice_energy_comparison",
        name="Novice Comparing Energy Usage",
        description=(
            "A confused newcomer compares energy usage between time periods. "
            "Tests whether the conversation can handle diagnostic back-and-forth "
            "without getting stuck in loops."
        ),
        persona_id="confused_newcomer",
        scenario_id="energy_comparison",
        validation_focus=[
            "multi_turn_coherence",
            "no_repetition_loops",
            "diagnostic_flow",
        ],
        expect_goal_completion=True,
        max_acceptable_errors=0,
        notes="Comparison scenarios require multiple exchanges - test for loops.",
    ),

    # Test 7: Cross-domain knowledge test
    ValidationScenario(
        id="expert_solar_consideration",
        name="Expert Considering Solar",
        description=(
            "A tech-savvy user asks about solar panels. Tests whether HEMA "
            "provides appropriately detailed information and whether the "
            "simulated user asks challenging follow-up questions."
        ),
        persona_id="tech_savvy_optimizer",
        scenario_id="solar_consideration",
        validation_focus=[
            "knowledge_depth",
            "persona_consistency",
            "evaluator_validity",
        ],
        expect_goal_completion=True,
        max_acceptable_errors=0,
        notes="Expert should challenge vague answers and ask for specifics.",
    ),

    # Test 8: Period comparison requiring data interpretation
    ValidationScenario(
        id="parent_energy_comparison",
        name="Parent Comparing Energy Usage",
        description=(
            "A busy parent asks to compare energy usage over time. Tests "
            "whether the system provides meaningful comparisons and the "
            "user asks appropriate clarifying questions."
        ),
        persona_id="budget_conscious_parent",
        scenario_id="energy_comparison",
        validation_focus=[
            "data_interpretation",
            "practical_focus",
            "goal_completion",
        ],
        expect_goal_completion=True,
        max_acceptable_errors=0,
        notes="User should focus on cost implications of usage changes.",
    ),
]


def get_validation_scenario(scenario_id: str) -> Optional[ValidationScenario]:
    """Get a validation scenario by ID."""
    for scenario in VALIDATION_SCENARIOS:
        if scenario.id == scenario_id:
            return scenario
    return None


def list_validation_scenarios() -> List[str]:
    """List all available validation scenario IDs."""
    return [s.id for s in VALIDATION_SCENARIOS]
