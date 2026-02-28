# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/evaluator/dataclasses.py
"""Dataclasses for conversation evaluation results (23 Table 1 metrics only)."""

import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ObjectiveMetrics:
    """
    Objective metrics for Table 1 evaluation (23 metrics only).

    Implements the 23 metrics from manuscript Table 1:
    - Task Performance: accuracy, errors, factual claims (6)
    - Interaction Quality: questions, responses, communication (8)
    - System Diagnostics: response metrics (2)
    - Supporting: extracted items for auditability

    Control Agent metrics (3) are in separate ControlProcessMetrics.
    Device-state metrics are placeholders (require actual device verification).
    """
    # User questions and answers
    user_questions: List[str] = field(default_factory=list)  # Actual questions asked
    questions_answered: List[str] = field(default_factory=list)  # Questions that got answers
    questions_unanswered: List[str] = field(default_factory=list)  # Questions not addressed

    # Communication quality indicators
    technical_terms_explained: List[str] = field(default_factory=list)  # Terms defined
    unexplained_jargon: List[str] = field(default_factory=list)  # Technical terms without explanation

    # Response Appropriateness Matrix (4 cells - required for Table 1)
    appropriate_data_backed: List[str] = field(default_factory=list)  # Data Q → Data-backed R ✅
    over_personalized: List[str] = field(default_factory=list)        # General Q → Data-backed R ⚠️
    under_personalized: List[str] = field(default_factory=list)       # Data Q → General R ❌
    appropriate_general: List[str] = field(default_factory=list)      # General Q → General R ✅

    # Factual Claims Verification
    # Each claim is a dict: {claim_text, claimed_value, ground_truth_value, unit, category, error_pct}
    factual_claims: List[Dict] = field(default_factory=list)

    # Turn counting (Tier 1)
    user_turns: int = 0
    system_turns: int = 0
    total_turns: int = 0
    user_messages_with_questions: int = 0

    # System performance metrics
    avg_system_response_length: float = 0.0
    max_system_response_length: int = 0
    min_system_response_length: int = 0

    def to_dict(
        self,
        last_turn_is_user: bool = False,
        goal_met: bool = False,
        avg_response_time: float = 0.0,
        total_tokens: int = 0,
    ) -> dict:
        """Convert to dictionary for JSON serialization (23 Table 1 metrics).

        Args:
            last_turn_is_user: Whether the last turn in the conversation was a user turn
            goal_met: Whether the conversation ended because the goal was achieved
            avg_response_time: Average response latency in seconds
            total_tokens: Total tokens used in conversation

        Returns the 23 metrics from manuscript Table 1.
        """
        total_questions = len(self.user_questions)
        answered = len(self.questions_answered)

        # Answered user question ratio: adjust for end-of-conversation questions
        # when last turn was user and goal was met
        if last_turn_is_user and goal_met and total_questions > 1:
            adjusted_total = total_questions - 1
            answered_ratio = min(answered / max(1, adjusted_total), 1.0)
        else:
            answered_ratio = answered / max(1, total_questions) if total_questions > 0 else 0.0

        # Factual accuracy metrics
        error_pcts = [
            c["error_pct"] for c in self.factual_claims
            if c.get("error_pct") is not None
        ]
        num_factual_claims = len(error_pcts)
        mean_error_pct = (
            sum(error_pcts) / num_factual_claims
            if num_factual_claims > 0 else None
        )
        num_accurate_claims = sum(1 for e in error_pcts if e <= 5.0)
        factual_accuracy_rate = (
            num_accurate_claims / num_factual_claims
            if num_factual_claims > 0 else None
        )

        return {
            # Table 1: 23 Metrics
            # Task Performance (6)
            "goal_achievement_rate": 1.0 if goal_met else 0.0,
            "task_to_completion_rate": 1.0 if goal_met else 0.0,
            "factual_accuracy": round(factual_accuracy_rate, 2) if factual_accuracy_rate is not None else None,
            "mean_error_percentage": round(mean_error_pct, 2) if mean_error_pct is not None else None,
            "factual_claims_count": num_factual_claims,
            "accurate_claims_count": num_accurate_claims,

            # Interaction Quality (8)
            "user_questions": total_questions,
            "answered_user_question_ratio": round(answered_ratio, 2),
            "appropriate_data_backed_response": len(self.appropriate_data_backed),
            "over_personalized_response": len(self.over_personalized),
            "under_personalized_response": len(self.under_personalized),
            "appropriate_general_response": len(self.appropriate_general),
            "technical_terms_explained": len(self.technical_terms_explained),
            "average_system_response_length": round(self.avg_system_response_length, 1),

            # Control Agent (3) - from ControlProcessMetrics:
            # information_before_action_rate, action_confirmation_rate, action_explanation_rate

            # Target Device Scenarios (3) - Placeholder (requires device state verification)
            "target_device_accuracy": None,
            "schedule_correctness": None,
            "mode_correctness": None,

            # System Constraint Compliance (1)
            "constraint_compliance_rate": None,

            # System Diagnostics (2)
            "response_latency": round(avg_response_time, 3),
            "token_usage": total_tokens,

            # Supporting data for auditability (not part of 23 metrics)
            "user_questions_list": self.user_questions,
            "questions_answered": self.questions_answered,
            "questions_unanswered": self.questions_unanswered,
            "technical_terms_explained_list": self.technical_terms_explained,
            "unexplained_jargon": self.unexplained_jargon,
            "appropriate_data_backed": self.appropriate_data_backed,
            "over_personalized": self.over_personalized,
            "under_personalized": self.under_personalized,
            "appropriate_general": self.appropriate_general,
            "factual_claims_list": self.factual_claims,
        }


@dataclass
class EvaluationResult:
    """Complete evaluation result for a conversation."""
    persona_id: str
    scenario_id: str
    total_turns: int

    # Raw data
    conversation_transcript: str

    # Objective metrics (all evaluation is based on these)
    objective_metrics: Optional[ObjectiveMetrics] = None

    # Metadata for reproducibility
    evaluation_runs: int = 1
    score_std_dev: float = 0.0
