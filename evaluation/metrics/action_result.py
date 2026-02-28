# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/metrics/action_result.py
"""Result dataclass for action correctness evaluation."""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class ActionCorrectnessResult:
    """Result of evaluating whether device control actions were appropriate.

    This evaluates the QUALITY of actions, not just whether they executed.
    For example:
    - Was the scheduled time during off-peak hours?
    - Was the temperature setting energy-efficient?
    - Was the mode appropriate for conditions?
    - Was the power action appropriate?
    """

    # Overall score (0-100%)
    correctness_score: float

    # Detailed evaluation per action
    actions_evaluated: int
    actions_correct: int
    actions_suboptimal: int  # Not wrong, but could be better

    # Per-action details
    action_details: List[Dict[str, Any]]
    # Each entry: {device, action, value, evaluation, is_correct, is_optimal, reason}

    # Summary by category
    schedule_correctness: Optional[float] = None  # % of schedules during off-peak
    temperature_correctness: Optional[float] = None  # % of temps in efficient range
    mode_correctness: Optional[float] = None  # % of mode changes appropriate
    power_correctness: Optional[float] = None  # % of power actions appropriate
    speed_correctness: Optional[float] = None  # % of speed settings appropriate

    # Constraint compliance
    constraint_compliance_rate: Optional[float] = None  # % of actions within device limits
    constraint_violations: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "correctness_score": self.correctness_score,
            "actions_evaluated": self.actions_evaluated,
            "actions_correct": self.actions_correct,
            "actions_suboptimal": self.actions_suboptimal,
            "action_details": self.action_details,
            "schedule_correctness": self.schedule_correctness,
            "temperature_correctness": self.temperature_correctness,
            "mode_correctness": self.mode_correctness,
            "power_correctness": self.power_correctness,
            "speed_correctness": self.speed_correctness,
            "constraint_compliance_rate": self.constraint_compliance_rate,
            "constraint_violations": self.constraint_violations,
        }
