# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/evaluator/evaluator.py
"""Core ConversationEvaluator class using objective metrics."""

from typing import List, Optional

from utils.logger import setup_logger
from config.config import LLMProvider, EVALUATOR_PROVIDER, EVALUATOR_MODEL
from config.llm_factory import create_llm
from evaluation.config import Persona, Scenario
from evaluation.data.ground_truth import GroundTruthSummary, get_current_ground_truth

from .dataclasses import ObjectiveMetrics, EvaluationResult
from .objective_metrics import compute_objective_metrics, format_transcript

logger = setup_logger(__name__)


class ConversationEvaluator:
    """
    Evaluates conversation quality using objective metrics only.

    All evaluation is based on automatically-counted metrics:
    - Tier 1: Pure counting (turns, questions, response length)
    - Tier 2: LLM-extracted metrics (questions, recommendations, jargon, etc.)
    - Tier 3: Factual claim verification (when ground truth available)

    LLM is used ONLY for extraction (Tier 2-3), not for subjective judgment.
    No subjective metrics like "goal_achieved", "strengths", or "weaknesses" are generated.
    """

    def __init__(
        self,
        provider: LLMProvider = None,
        model: str = None,
        temperature: float = 0.1,
    ):
        """
        Initialize the evaluator.

        Args:
            provider: LLM provider (for metric extraction only)
            model: Specific model to use
            temperature: Temperature for extraction (low for consistency)
        """
        self.provider = provider or EVALUATOR_PROVIDER
        self.model = model or EVALUATOR_MODEL

        self.llm = create_llm(
            provider=self.provider,
            model=self.model,
            temperature=temperature,
        )
        self.temperature = temperature

    def evaluate(
        self,
        conversation_history: List[dict],
        persona: Persona,
        scenario: Scenario,
        goal_signaled: bool = False,
        ground_truth: Optional[GroundTruthSummary] = None,
    ) -> EvaluationResult:
        """
        Evaluate a completed conversation using objective metrics only.

        All metrics are automatically counted:
        - Tier 1: Pure counting (turns, question marks, response length)
        - Tier 2: LLM-extracted metrics (questions, recommendations, jargon, etc.)
        - Tier 3: Factual claim verification (when ground truth available)

        The LLM is used ONLY for extraction in Tiers 2-3, not for subjective judgment.

        Args:
            conversation_history: List of {"role": "user"/"assistant", "content": str}
            persona: The persona used in the simulation
            scenario: The scenario being evaluated
            goal_signaled: Unused (kept for backward compatibility)
            ground_truth: Optional ground truth data for factual accuracy evaluation.
                          If not provided, will attempt to extract from current data cache.

        Returns:
            EvaluationResult with objective metrics only
        """
        # Build conversation transcript
        transcript = format_transcript(conversation_history)

        # Try to get ground truth if not provided
        if ground_truth is None:
            ground_truth = get_current_ground_truth()

        # Compute objective metrics (Tiers 1-3) — all automatic, no subjective judgment
        objective_metrics = compute_objective_metrics(
            conversation_history, self.llm,
            ground_truth=ground_truth,
        )

        return EvaluationResult(
            persona_id=persona.id,
            scenario_id=scenario.id,
            total_turns=len(conversation_history),
            conversation_transcript=transcript,
            objective_metrics=objective_metrics,
        )

    def format_report(self, result: EvaluationResult) -> str:
        """Format an evaluation result as a readable report."""
        lines = [
            "=" * 60,
            "CONVERSATION EVALUATION REPORT",
            "=" * 60,
            f"Persona: {result.persona_id}",
            f"Scenario: {result.scenario_id}",
            f"Total Turns: {result.total_turns}",
            "",
            "-" * 40,
            "OBJECTIVE METRICS",
            "-" * 40,
        ]

        if result.objective_metrics:
            m = result.objective_metrics.to_dict()
            lines.extend([
                f"  Answered Question Ratio: {m.get('answered_user_question_ratio', 0):.2f}",
                f"  User Questions: {m.get('user_questions', 0)}",
                f"  Technical Terms Explained: {m.get('technical_terms_explained', 0)}",
                f"  Data-Backed Responses: {m.get('appropriate_data_backed_response', 0)}",
                f"  Avg Response Length: {m.get('average_system_response_length', 0):.0f} chars",
            ])
            if m.get('factual_claims_count', 0) > 0:
                lines.extend([
                    f"  Factual Claims Verified: {m.get('factual_claims_count', 0)}",
                    f"  Factual Accuracy Rate: {m.get('factual_accuracy', 0):.2f}",
                    f"  Mean Error Pct: {m.get('mean_error_percentage', 0):.1f}%",
                ])

        lines.extend([
            "",
            "=" * 60,
            "CONVERSATION TRANSCRIPT",
            "=" * 60,
            result.conversation_transcript,
            "",
            "=" * 60,
        ])

        return "\n".join(lines)
