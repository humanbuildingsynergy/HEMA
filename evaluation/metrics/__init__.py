# evaluation/metrics/__init__.py
"""
Metrics module for LLM-as-Simulated-User evaluation.

This module provides structured metrics for task completion, system performance,
conversation quality analysis, device state verification, and action correctness.
"""

# Device verification
from .device_verification import (
    DeviceStateVerificationResult,
    verify_device_state_changes,
)

# Action correctness
from .action_correctness import (
    ActionCorrectnessResult,
    evaluate_action_correctness,
    EFFICIENT_TEMP_RANGES,
)

# Performance metrics
from .performance import (
    TaskCompletionMetrics,
    TurnMetrics,
    SystemPerformanceMetrics,
    ConversationQualityMetrics,
    AggregateMetrics,
    MODEL_PRICING,
    calculate_cost,
)

# Experiment result
from .experiment import ExperimentResult

# Report formatters
from .formatters import (
    format_metrics_report,
    format_aggregate_report,
)

__all__ = [
    # Device verification
    "DeviceStateVerificationResult",
    "verify_device_state_changes",
    # Action correctness
    "ActionCorrectnessResult",
    "evaluate_action_correctness",
    "EFFICIENT_TEMP_RANGES",
    # Performance metrics
    "TaskCompletionMetrics",
    "TurnMetrics",
    "SystemPerformanceMetrics",
    "ConversationQualityMetrics",
    "AggregateMetrics",
    "MODEL_PRICING",
    "calculate_cost",
    # Experiment result
    "ExperimentResult",
    # Report formatters
    "format_metrics_report",
    "format_aggregate_report",
]
