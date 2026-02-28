# evaluation/runners/__init__.py
"""Conversation infrastructure for evaluation.

Contains conversation runners (HEMA and vanilla), simulated user,
conversation monitoring, and shared dataclasses.
"""

from .dataclasses import ConversationTurn, ConversationRecord
from .conversation import ConversationRunner, run_single_evaluation, run_full_experiment
from .simulated_user import SimulatedUser, OpeningMode
from .vanilla_conversation import (
    VanillaConversationRunner,
    run_vanilla_experiment,
    run_vanilla_structured_experiment,
    run_vanilla_structured_cot_experiment,
    VANILLA_EXPERIMENT_RUNNERS,
    ALL_VANILLA_SYSTEMS,
)
from .conversation_monitor import ConversationMonitor, extract_scenario_keywords

__all__ = [
    # Dataclasses
    "ConversationTurn",
    "ConversationRecord",
    # HEMA runner
    "ConversationRunner",
    "run_single_evaluation",
    "run_full_experiment",
    # Simulated user
    "SimulatedUser",
    "OpeningMode",
    # Vanilla runners
    "VanillaConversationRunner",
    "run_vanilla_experiment",
    "run_vanilla_structured_experiment",
    "run_vanilla_structured_cot_experiment",
    "VANILLA_EXPERIMENT_RUNNERS",
    "ALL_VANILLA_SYSTEMS",
    # Monitor
    "ConversationMonitor",
    "extract_scenario_keywords",
]
