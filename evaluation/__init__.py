# evaluation/__init__.py
"""
LLM-as-Simulated-User Evaluation Framework for HEMA.

This standalone module enables automated evaluation of the interactive
energy management system using LLM-simulated users.

Architecture:
    - Simulated User (Gemini): Plays personas with specific goals/behaviors
    - System Under Test (HEMA): The energy management chatbot
    - Evaluator (Gemini): Extracts objective metrics from conversations

Subpackages:
    - runners/: Conversation infrastructure (HEMA & vanilla runners, simulated user)
    - data/: Data utilities (ground truth extraction, household metrics)
    - evaluator/: Objective metrics computation (3-tier evaluation)
    - metrics/: Result dataclasses, formatters, and device verification
    - config/: Persona and scenario definitions
    - comparison/: Comparative evaluation utilities

Usage:
    python -m evaluation.run_experiment
    python -m evaluation.run_experiment --runs 5          # Multi-run aggregation
    python -m evaluation.run_experiment --matrix --runs 5  # Full evaluation matrix
"""

from .runners.dataclasses import ConversationTurn, ConversationRecord
from .runners.conversation import ConversationRunner, run_single_evaluation, run_full_experiment
from .runners.simulated_user import SimulatedUser, OpeningMode
from .evaluator import ConversationEvaluator
from .metrics import (
    TaskCompletionMetrics,
    TurnMetrics,
    SystemPerformanceMetrics,
    ConversationQualityMetrics,
    AggregateMetrics,
    ExperimentResult,
    format_metrics_report,
    format_aggregate_report,
)
from .data.household_metrics import (
    HouseholdProfile,
    extract_household_profile,
    format_household_comparison,
)
from .data.ground_truth import (
    GroundTruthSummary,
    extract_ground_truth,
    get_current_ground_truth,
)

__all__ = [
    # Dataclasses
    "ConversationTurn",
    "ConversationRecord",
    # Core classes
    "ConversationRunner",
    "SimulatedUser",
    "ConversationEvaluator",
    "OpeningMode",
    # Entry points
    "run_single_evaluation",
    "run_full_experiment",
    # Metrics
    "TaskCompletionMetrics",
    "TurnMetrics",
    "SystemPerformanceMetrics",
    "ConversationQualityMetrics",
    "AggregateMetrics",
    "ExperimentResult",
    # Household metrics
    "HouseholdProfile",
    "extract_household_profile",
    "format_household_comparison",
    # Ground truth for factual accuracy
    "GroundTruthSummary",
    "extract_ground_truth",
    "get_current_ground_truth",
    # Formatters
    "format_metrics_report",
    "format_aggregate_report",
]
