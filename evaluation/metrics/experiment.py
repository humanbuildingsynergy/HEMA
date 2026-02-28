# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/metrics/experiment.py
"""ExperimentResult dataclass for complete experiment results."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any, TYPE_CHECKING

from .performance import (
    TaskCompletionMetrics,
    SystemPerformanceMetrics,
    ConversationQualityMetrics,
    TurnMetrics,
)
from .device_verification import DeviceStateVerificationResult
from .action_correctness import ActionCorrectnessResult
from .control_process import ControlProcessMetrics

if TYPE_CHECKING:
    from evaluation.data.household_metrics import HouseholdProfile


@dataclass
class ExperimentResult:
    """Complete result from a single experiment run."""

    # Identifiers
    experiment_id: str
    persona_id: str
    scenario_id: str
    timestamp: str

    # All metrics
    task_metrics: TaskCompletionMetrics
    system_metrics: SystemPerformanceMetrics
    quality_metrics: ConversationQualityMetrics

    # Raw data
    conversation_transcript: str
    turn_details: List[TurnMetrics]

    # Household context for case study comparisons
    household_profile: Optional["HouseholdProfile"] = None

    # Device state tracking (for Control Agent evaluation)
    device_state_before: Optional[Dict[str, Any]] = None
    device_state_after: Optional[Dict[str, Any]] = None
    device_state_changes: Optional[Dict[str, Any]] = None

    # Device state verification result (for Control Agent scenarios)
    device_state_verification: Optional[DeviceStateVerificationResult] = None

    # Action correctness evaluation (for Control Agent scenarios)
    action_correctness: Optional[ActionCorrectnessResult] = None

    # Control process metrics (for Control Agent scenarios)
    control_process_metrics: Optional[ControlProcessMetrics] = None

    # System identification for comparison (hema vs vanilla)
    system_type: str = "hema"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "experiment_id": self.experiment_id,
            "persona_id": self.persona_id,
            "scenario_id": self.scenario_id,
            "timestamp": self.timestamp,
            "task_metrics": {
                "goal_achieved": self.task_metrics.goal_achieved,
                "turns_to_completion": self.task_metrics.turns_to_completion,
                "max_turns_allowed": self.task_metrics.max_turns_allowed,
                "terminated_reason": self.task_metrics.terminated_reason,
                "task_efficiency": self.task_metrics.task_efficiency,
                "goal_progress_score": self.task_metrics.goal_progress_score,
            },
            "system_metrics": {
                # Response latency metrics
                "avg_latency_ms": self.system_metrics.avg_latency_ms,
                "min_latency_ms": self.system_metrics.min_latency_ms,
                "max_latency_ms": self.system_metrics.max_latency_ms,
                "p95_latency_ms": self.system_metrics.p95_latency_ms,
                "per_turn_latency_ms": self.system_metrics.per_turn_latency_ms,
                # Agent routing metrics
                "agent_distribution": self.system_metrics.agent_distribution,
                "primary_agent": self.system_metrics.primary_agent,
                # Tool invocation metrics
                "tools_used": self.system_metrics.tools_used,
                "tool_call_count": self.system_metrics.tool_call_count,
                "tool_distribution": self.system_metrics.tool_distribution,
                # Error metrics
                "error_count": self.system_metrics.error_count,
                "error_rate": self.system_metrics.error_rate,
                # Turn counts
                "total_turns": self.system_metrics.total_turns,
                "system_turns": self.system_metrics.system_turns,
                "user_turns": self.system_metrics.user_turns,
                # Token usage
                "total_input_tokens": self.system_metrics.total_input_tokens,
                "total_output_tokens": self.system_metrics.total_output_tokens,
                "total_tokens": self.system_metrics.total_tokens,
                "hema_input_tokens": self.system_metrics.hema_input_tokens,
                "hema_output_tokens": self.system_metrics.hema_output_tokens,
                "simulated_user_input_tokens": self.system_metrics.simulated_user_input_tokens,
                "simulated_user_output_tokens": self.system_metrics.simulated_user_output_tokens,
                # Cost metrics
                "total_cost_usd": self.system_metrics.total_cost_usd,
                "hema_cost_usd": self.system_metrics.hema_cost_usd,
                "simulated_user_cost_usd": self.system_metrics.simulated_user_cost_usd,
                "model_used": self.system_metrics.model_used,
            },
            # Per-turn details (response latency and tool invocations per turn)
            "turn_details": [
                {
                    "turn_number": t.turn_number,
                    "speaker": t.speaker,
                    "latency_ms": t.latency_ms,
                    "agent_used": t.agent_used,
                    "tools_called": t.tools_called,
                    "had_error": t.had_error,
                    "input_tokens": t.input_tokens,
                    "output_tokens": t.output_tokens,
                }
                for t in self.turn_details
            ],
            "quality_metrics": {
                "llm_judge_score": self.quality_metrics.llm_judge_score,
                "dimension_scores": self.quality_metrics.dimension_scores,
                "dimension_evaluations": (
                    {
                        dim: {
                            "score": eval.score,
                            "reasoning": eval.reasoning,
                            "evidence": eval.evidence,
                        }
                        for dim, eval in self.quality_metrics.dimension_evaluations.items()
                    }
                    if self.quality_metrics.dimension_evaluations
                    else None
                ),
                "strengths": self.quality_metrics.strengths,
                "weaknesses": self.quality_metrics.weaknesses,
                "improvement_suggestions": self.quality_metrics.improvement_suggestions,
                # New fields for consensus evaluation
                "objective_metrics": self.quality_metrics.objective_metrics,
                "evaluation_runs": self.quality_metrics.evaluation_runs,
                "score_std_dev": self.quality_metrics.score_std_dev,
            },
            "conversation_transcript": self.conversation_transcript,
            "household_profile": self.household_profile.to_dict() if self.household_profile else None,
            "device_state_before": self.device_state_before,
            "device_state_after": self.device_state_after,
            "device_state_changes": self.device_state_changes,
            "device_state_verification": (
                self.device_state_verification.to_dict()
                if self.device_state_verification
                else None
            ),
            "action_correctness": (
                self.action_correctness.to_dict()
                if self.action_correctness
                else None
            ),
            "control_process_metrics": (
                self.control_process_metrics.to_dict()
                if self.control_process_metrics
                else None
            ),
            "system_type": self.system_type,
        }
