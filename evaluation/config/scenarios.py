# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/config/scenarios.py
"""
Scenario definitions for LLM-as-Simulated-User evaluation.

Scenarios define WHAT the user wants to accomplish (goals, context).

CORE SCENARIOS (7 total):
- 4 Analysis Agent scenarios for demonstrating data analysis and reasoning
- 2 Control Agent scenarios for device control and automation
- 1 Knowledge Agent scenario for RAG and knowledge retrieval

These core scenarios are sufficient for reproducing manuscript results and
demonstrating HEMA's key capabilities. Removed scenarios are archived in git history.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Scenario:
    """Defines an evaluation scenario."""
    id: str
    name: str
    description: str

    # Goal Structure
    primary_goal: str
    success_criteria: List[str]

    # Conversation Setup
    initial_context: str  # What the user knows going in
    opening_message: str  # First message to send

    # Evaluation Focus
    evaluation_dimensions: List[str]
    max_turns: int = 40  # Safety limit to prevent runaway conversations

    # Expected device state changes (for Control Agent scenarios)
    # Format: {"device_key": {"state_property": expected_value_or_check}}
    # Special checks: {"_changed": True} means value should change (any change)
    #                 {"_in_range": [min, max]} means value should be in range
    expected_device_changes: Optional[Dict[str, Dict]] = None

    def to_prompt_context(self) -> str:
        """Generate prompt context for the simulated user LLM."""
        criteria = "\n".join(f"  - {c}" for c in self.success_criteria)

        return f"""## Your Scenario: {self.name}

**What You Want:** {self.primary_goal}

**You'll Consider This Successful If:**
{criteria}

**What You Already Know:** {self.initial_context}

**Start the conversation with something like:** "{self.opening_message}"
(You can paraphrase naturally, don't copy exactly)
"""


# =============================================================================
# CORE SCENARIO DEFINITIONS
# =============================================================================

SCENARIOS: Dict[str, Scenario] = {
    # =============================================================================
    # ANALYSIS AGENT SCENARIOS (4)
    # =============================================================================

    "understand_utility_rate": Scenario(
        id="understand_utility_rate",
        name="Understanding My Utility Rate",
        description="User wants to understand their TOU rate structure and how it affects their bill",
        primary_goal=(
            "Understand what TOU (Time-of-Use) pricing is and how it applies to "
            "your home. Figure out when electricity is most expensive and what "
            "you can do about it."
        ),
        success_criteria=[
            "Understand what TOU pricing means in simple terms",
            "Know when peak vs off-peak hours are (approximately)",
            "Get at least one actionable tip for saving money",
            "Feel more confident about managing your energy use",
        ],
        initial_context=(
            "You saw 'TOU' on your bill but don't know what it means. You noticed "
            "your bill was higher than expected. You have a rough sense that electricity "
            "prices might change during the day but aren't sure."
        ),
        opening_message=(
            "Hi, I just got my electricity bill and it mentions something about TOU rates. "
            "What does that mean?"
        ),
        evaluation_dimensions=[
            "communication_quality",
            "task_effectiveness",
            "factual_accuracy",  # Has ground truth: rate info
        ],
    ),

    "appliance_analysis": Scenario(
        id="appliance_analysis",
        name="Appliance Energy Analysis",
        description="User wants to identify which appliances use the most energy",
        primary_goal=(
            "Find out which appliances in your home consume the most energy "
            "and get recommendations on how to reduce their usage or replace "
            "inefficient ones."
        ),
        success_criteria=[
            "Identify top energy-consuming appliances",
            "Understand relative energy usage of different appliances",
            "Get specific recommendations for reducing appliance energy use",
            "Learn about energy-efficient alternatives if applicable",
        ],
        initial_context=(
            "You have a general sense that some appliances use more energy than "
            "others, but you're not sure which ones are the biggest culprits. "
            "You've heard your AC and water heater might be big users."
        ),
        opening_message=(
            "I'm trying to figure out which appliances are costing me the most. "
            "Can you help me understand my energy usage?"
        ),
        evaluation_dimensions=[
            "communication_quality",
            "task_effectiveness",
            "factual_accuracy",  # Has ground truth: appliance consumption data
        ],
    ),

    "peak_reduction_strategy": Scenario(
        id="peak_reduction_strategy",
        name="Peak Usage Reduction",
        description="User wants to reduce energy usage during expensive peak hours",
        primary_goal=(
            "Develop a strategy to shift energy usage away from peak hours "
            "to save money. Get specific recommendations on what to change "
            "and when."
        ),
        success_criteria=[
            "Understand which activities contribute most to peak usage",
            "Get a concrete plan for shifting usage to off-peak hours",
            "Learn how much money could be saved with the changes",
            "Feel confident about implementing the strategy",
        ],
        initial_context=(
            "You know that peak hours are more expensive but you're not sure "
            "how to actually change your habits. You need practical advice "
            "that fits your daily routine."
        ),
        opening_message=(
            "I want to stop using so much electricity during peak hours. "
            "What should I change?"
        ),
        evaluation_dimensions=[
            "communication_quality",
            "task_effectiveness",
            "factual_accuracy",  # Has ground truth: appliance consumption, peak hours, rates
        ],
    ),

    "multi_step_investigation": Scenario(
        id="multi_step_investigation",
        name="Multi-Step Usage Investigation",
        description="User has a complex question requiring multiple analysis steps",
        primary_goal=(
            "Investigate a complex energy question that requires looking at data "
            "from multiple angles. Understand patterns and get actionable advice."
        ),
        success_criteria=[
            "Get analysis from multiple perspectives (time, appliance, pattern)",
            "Receive a coherent explanation connecting the findings",
            "Understand the root cause of observed patterns",
            "Get specific recommendations based on the investigation",
        ],
        initial_context=(
            "You've noticed your bills are higher on certain days but you're not sure why. "
            "You want to understand what combination of factors is driving your costs."
        ),
        opening_message=(
            "Why are my energy costs so much higher some days than others? Can you "
            "figure out what's going on and which appliances are responsible?"
        ),
        evaluation_dimensions=[
            "communication_quality",
            "task_effectiveness",
            "factual_accuracy",  # Has ground truth: multi-dimensional consumption data
        ],
    ),

    # =============================================================================
    # CONTROL AGENT SCENARIOS (2)
    # =============================================================================

    "thermostat_adjustment": Scenario(
        id="thermostat_adjustment",
        name="Thermostat Temperature Adjustment",
        description="User wants to adjust their smart thermostat settings based on rate structure",
        primary_goal=(
            "Adjust the thermostat to an optimal temperature for energy savings. "
            "Understand how the setting relates to your rate structure and get "
            "confirmation that the change was made."
        ),
        success_criteria=[
            "Successfully change the thermostat temperature",
            "Understand how the new setting affects energy costs",
            "Get confirmation of the current thermostat state after the change",
            "Learn about the relationship between temperature and energy usage",
        ],
        initial_context=(
            "You have a smart thermostat and your energy bills have been high. "
            "You want to adjust the temperature to save money but aren't sure "
            "what temperature is best for your rate plan."
        ),
        opening_message=(
            "Can you help me adjust my thermostat? I want to save on energy costs. "
            "What temperature should I set it to?"
        ),
        evaluation_dimensions=[
            "communication_quality",
            "task_effectiveness",
            "factual_accuracy",  # Has ground truth: rate info, device state
        ],
        expected_device_changes={
            "hvac": {
                # Temperature should change in the energy-saving direction by at least 4°F:
                # - Cooling mode (summer): INCREASE temp by ≥4°F (higher = less AC work)
                # - Heating mode (winter): DECREASE temp by ≥4°F (lower = less heating)
                # Use _any_of since we don't know ahead of time which mode the HVAC is in
                "_any_of": [
                    {"target_temperature_f": {"_direction": "increase", "_min_delta": 4}},  # Cooling mode
                    {"target_temperature_f": {"_direction": "decrease", "_min_delta": 4}},  # Heating mode
                    {"mode": {"_changed": True}},  # Mode change is also acceptable
                ]
            }
        },
    ),

    "vacation_preparation": Scenario(
        id="vacation_preparation",
        name="Multi-Device Vacation Preparation",
        description="User wants to configure multiple devices for energy savings while away on vacation",
        primary_goal=(
            "Set up all smart devices to minimize energy usage during a vacation. "
            "Configure HVAC, water heater, and pool pump appropriately while ensuring "
            "the home remains safe and systems are ready for return."
        ),
        success_criteria=[
            "Configure HVAC for minimal usage while away",
            "Set water heater to vacation or low-energy mode",
            "Get confirmation of all changes made",
        ],
        initial_context=(
            "You're leaving for a two-week vacation tomorrow. Your home has smart devices "
            "including HVAC, water heater, and pool pump. You want to save as much energy "
            "as possible while you're away but don't want any issues when you return."
        ),
        opening_message=(
            "I'm leaving for vacation tomorrow for two weeks. Can you help me set up "
            "all my devices to save energy while I'm gone? What should I do with my "
            "thermostat, water heater, and pool pump?"
        ),
        evaluation_dimensions=[
            "communication_quality",
            "task_effectiveness",
            "factual_accuracy",
        ],
        expected_device_changes={
            # Multiple devices should be configured
            "hvac": {
                # Temperature should be set to energy-saving level for vacation
                # Accept either full setback (80-85°F) or moderate energy-saving (76-82°F)
                "_any_of": [
                    {"target_temperature_f": {"_in_range": [80, 85]}},  # Full vacation setback
                    {"target_temperature_f": {"_in_range": [76, 82]}},  # Moderate energy-saving
                    {"mode": {"_changed": True}},  # Away mode or similar
                ]
            },
            "water_heater": {
                # Should be set to vacation mode or scheduled off
                "_any_of": [
                    {"mode": "vacation"},
                    {"scheduled_time": {"_changed": True}},
                ]
            },
        },
    ),

    # =============================================================================
    # KNOWLEDGE AGENT SCENARIO (1)
    # =============================================================================

    "rebate_inquiry": Scenario(
        id="rebate_inquiry",
        name="Energy Rebate Information",
        description="User wants to learn about available rebates and incentive programs",
        primary_goal=(
            "Find out what rebates and incentives are available for energy-efficient "
            "upgrades. Get specific details about eligibility, amounts, and how to apply."
        ),
        success_criteria=[
            "Learn about specific rebate programs available (e.g., heat pump, HVAC)",
            "Understand eligibility requirements for rebates",
            "Get specific rebate amounts or ranges",
            "Know how to apply for rebates",
        ],
        initial_context=(
            "You're considering upgrading your water heater or HVAC system and heard "
            "there might be rebates available. You want to know what programs exist "
            "and if you qualify."
        ),
        opening_message=(
            "I'm thinking about getting a heat pump water heater. Are there any "
            "rebates or incentives I can get?"
        ),
        evaluation_dimensions=[
            "communication_quality",
            "task_effectiveness",
            # No factual_accuracy: rebate info from RAG, no ground truth to verify
        ],
    ),
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_scenario(scenario_id: str) -> Optional[Scenario]:
    """Get a scenario by ID."""
    return SCENARIOS.get(scenario_id)


def list_scenarios() -> List[str]:
    """List all available scenario IDs."""
    return list(SCENARIOS.keys())
