# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/runners/vanilla_conversation.py
"""Conversation runner for vanilla LLM evaluation.

Provides the same conversation flow as ConversationRunner but uses
VanillaLLMRunner instead of HEMA's multi-agent system.
"""

import time
from datetime import datetime
from typing import Dict, List, Optional, Any

from ..config import Persona, Scenario
from .dataclasses import ConversationTurn, ConversationRecord
from .simulated_user import SimulatedUser, OpeningMode
from ..evaluator import ConversationEvaluator
from .conversation_monitor import ConversationMonitor, extract_scenario_keywords
from .vanilla_llm import (
    VanillaLLMRunner,
    VanillaStructuredRunner,
    VanillaStructuredCoTRunner,
    load_raw_data_context,
    load_structured_data_context,
)
from ..metrics import (
    TurnMetrics,
    TaskCompletionMetrics,
    SystemPerformanceMetrics,
    ConversationQualityMetrics,
    ExperimentResult,
)


class VanillaConversationRunner:
    """Runs conversations between simulated users and vanilla LLM.

    Mirrors ConversationRunner but uses VanillaLLMRunner instead of HEMA.
    """

    def __init__(
        self,
        persona: Persona,
        scenario: Scenario,
        data_context: str,
        simulated_user: Optional[SimulatedUser] = None,
        vanilla_runner: Optional[VanillaLLMRunner] = None,
        verbose: bool = True,
        opening_mode: OpeningMode = OpeningMode.CONTROLLED,
    ):
        """Initialize the vanilla conversation runner.

        Args:
            persona: User persona for simulation
            scenario: Scenario defining goals and context
            data_context: Raw CSV data as string for vanilla LLM
            simulated_user: Simulated user instance (created if not provided)
            vanilla_runner: Vanilla LLM instance (created if not provided)
            verbose: Whether to print conversation in real-time
            opening_mode: How to generate opening messages
        """
        self.persona = persona
        self.scenario = scenario
        self.verbose = verbose
        self.opening_mode = opening_mode

        # Initialize vanilla LLM with data context
        self.vanilla = vanilla_runner or VanillaLLMRunner(data_context=data_context)

        # Initialize simulated user (same as HEMA evaluation)
        self.simulated_user = simulated_user or SimulatedUser(
            persona=persona,
            scenario=scenario,
            opening_mode=opening_mode,
        )

        # Conversation state
        self.turns: List[ConversationTurn] = []
        self.goal_signaled = False

        # Initialize conversation monitor for loop/drift detection
        self.monitor = ConversationMonitor(
            similarity_threshold=0.75,
            max_consecutive_similar=3,
            drift_threshold=0.7,
            drift_window=5,
        )
        self.scenario_keywords = extract_scenario_keywords(scenario)

    def run(self, max_turns: Optional[int] = None) -> ConversationRecord:
        """Run the complete conversation.

        Args:
            max_turns: Maximum number of turns. Uses scenario default if not specified.

        Returns:
            ConversationRecord with full conversation data
        """
        if max_turns is None:
            max_turns = self.scenario.max_turns
        start_time = datetime.now()
        start_timestamp = time.time()

        if self.verbose:
            print("\n" + "=" * 60)
            print("STARTING VANILLA LLM CONVERSATION")
            print(f"Persona: {self.persona.id}")
            print(f"Scenario: {self.scenario.name}")
            print(f"Max turns: {max_turns if max_turns else 'No limit'}")
            print("=" * 60 + "\n")

        terminated_reason = "max_turns"

        try:
            # Get opening message from simulated user
            user_turn = self.simulated_user.get_opening_message()
            self._record_turn(
                "user",
                user_turn.message,
                input_tokens=user_turn.input_tokens,
                output_tokens=user_turn.output_tokens,
            )

            if self.verbose:
                print(f"[User] {user_turn.message}\n")

            # Main conversation loop
            turn_count = 1
            while max_turns is None or turn_count < max_turns:
                # Get vanilla LLM response
                vanilla_result = self._get_vanilla_response(user_turn.message)

                self._record_turn(
                    speaker="system",
                    message=vanilla_result["response"],
                    latency_ms=vanilla_result["latency_ms"],
                    had_error=vanilla_result["had_error"],
                    input_tokens=vanilla_result.get("input_tokens", 0),
                    output_tokens=vanilla_result.get("output_tokens", 0),
                )

                if self.verbose:
                    latency_info = f" ({vanilla_result['latency_ms']:.0f}ms)"
                    print(f"[Vanilla LLM]{latency_info} {vanilla_result['response']}\n")

                # Get user's response
                user_turn = self.simulated_user.respond_to_system(vanilla_result["response"])
                self._record_turn(
                    "user",
                    user_turn.message,
                    input_tokens=user_turn.input_tokens,
                    output_tokens=user_turn.output_tokens,
                )

                if self.verbose:
                    print(f"[User] {user_turn.message}\n")

                # NATURAL WRAP-UP DETECTION: Check if user message contains satisfaction signals
                if self.simulated_user.detect_wrap_up_signal(user_turn.message):
                    self.goal_signaled = True
                    terminated_reason = "goal_met"
                    if self.verbose:
                        print("[MONITOR] User signaled satisfaction. Ending conversation naturally.\n")
                    break

                turn_count += 1

                # Check for conversation loops/drift
                monitor_result = self.monitor.check_message(
                    message=user_turn.message,
                    speaker="user",
                    scenario_goal=self.scenario.primary_goal,
                    scenario_keywords=self.scenario_keywords,
                )

                if monitor_result.should_terminate:
                    terminated_reason = monitor_result.reason
                    if self.verbose:
                        print(f"\n[MONITOR] Terminating: {monitor_result.reason}")
                    break

                if monitor_result.warning and self.verbose:
                    print(f"[MONITOR] Warning: {monitor_result.warning}")

        except Exception as e:
            terminated_reason = f"error: {str(e)}"
            if self.verbose:
                print(f"\n[ERROR] Conversation terminated: {e}")

        end_time = datetime.now()
        total_duration = time.time() - start_timestamp

        if self.verbose:
            print("\n" + "=" * 60)
            print("VANILLA LLM CONVERSATION ENDED")
            print(f"Reason: {terminated_reason}")
            print(f"Total turns: {len(self.turns)}")
            print(f"Duration: {total_duration:.1f}s")
            print("=" * 60 + "\n")

        # Determine system type from runner class
        if isinstance(self.vanilla, VanillaStructuredCoTRunner):
            system_type = "vanilla_structured_cot"
        elif isinstance(self.vanilla, VanillaStructuredRunner):
            system_type = "vanilla_structured"
        else:
            system_type = "vanilla"

        return ConversationRecord(
            persona_id=self.persona.id,
            scenario_id=self.scenario.id,
            system_type=system_type,
            start_time=start_time,
            end_time=end_time,
            turns=self.turns.copy(),
            goal_signaled=self.goal_signaled,
            terminated_reason=terminated_reason,
            total_duration_seconds=total_duration,
        )

    def _get_vanilla_response(self, user_message: str) -> Dict[str, Any]:
        """Get response from the vanilla LLM.

        Returns:
            Dict with 'response', 'latency_ms', 'had_error', 'input_tokens', 'output_tokens'
        """
        had_error = False

        try:
            result = self.vanilla.invoke(user_message)
            response = result.response
            latency_ms = result.latency_ms
            input_tokens = result.input_tokens
            output_tokens = result.output_tokens

        except Exception as e:
            response = f"I encountered an error: {str(e)}"
            latency_ms = 0.0
            input_tokens = 0
            output_tokens = 0
            had_error = True

        return {
            "response": response,
            "latency_ms": latency_ms,
            "had_error": had_error,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }

    def _record_turn(
        self,
        speaker: str,
        message: str,
        latency_ms: float = 0.0,
        had_error: bool = False,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        """Record a conversation turn."""
        turn = ConversationTurn(
            turn_number=len(self.turns) + 1,
            speaker=speaker,
            message=message,
            timestamp=time.time(),
            latency_ms=latency_ms,
            had_error=had_error,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        )
        self.turns.append(turn)

    def get_history_for_evaluation(self) -> List[dict]:
        """Get conversation history in the format expected by evaluator."""
        history = []
        for turn in self.turns:
            role = "user" if turn.speaker == "user" else "assistant"
            history.append({"role": role, "content": turn.message})
        return history

    def get_turn_metrics(self) -> List[TurnMetrics]:
        """Convert conversation turns to TurnMetrics for performance analysis."""
        return [
            TurnMetrics(
                turn_number=turn.turn_number,
                speaker=turn.speaker,
                latency_ms=turn.latency_ms,
                agent_used="vanilla_llm",  # Always vanilla LLM
                tools_called=[],  # No tools in vanilla LLM
                had_error=turn.had_error,
                classification_result=None,
                input_tokens=turn.input_tokens,
                output_tokens=turn.output_tokens,
                total_tokens=turn.total_tokens,
            )
            for turn in self.turns
        ]

    def reset(self) -> None:
        """Reset the conversation state for a new run."""
        self.turns = []
        self.goal_signaled = False
        self.simulated_user.reset()
        self.vanilla.reset()
        self.monitor.reset()


def run_vanilla_experiment(
    persona: Persona,
    scenario: Scenario,
    data_file: str = "data/home_power/energy_data_sample.csv",
    data_days: int = 14,
    experiment_id: Optional[str] = None,
    evaluator: Optional[ConversationEvaluator] = None,
    verbose: bool = True,
    max_turns: Optional[int] = None,
    opening_mode: OpeningMode = OpeningMode.CONTROLLED,
    eval_runs: int = 1,
) -> ExperimentResult:
    """Run a complete vanilla LLM experiment with full metrics collection.

    This mirrors run_full_experiment() but uses VanillaLLMRunner instead of HEMA.

    Args:
        persona: User persona for simulation
        scenario: Scenario defining goals and context
        data_file: Path to energy data CSV file
        data_days: Number of days of data to include (default 14)
        experiment_id: Optional experiment ID (auto-generated if not provided)
        evaluator: Evaluator instance (created if not provided)
        verbose: Whether to print progress
        max_turns: Maximum turns for conversation
        opening_mode: How to generate opening messages
        eval_runs: Number of evaluation runs for consensus scoring (default: 1)

    Returns:
        ExperimentResult with all metrics and system_type="vanilla"
    """
    import uuid

    experiment_id = experiment_id or f"vanilla_exp_{uuid.uuid4().hex[:8]}"
    timestamp = datetime.now().isoformat()

    # Load raw data context
    data_context = load_raw_data_context(data_file, days=data_days)

    # Run the conversation
    runner = VanillaConversationRunner(
        persona=persona,
        scenario=scenario,
        data_context=data_context,
        verbose=verbose,
        opening_mode=opening_mode,
    )
    record = runner.run(max_turns=max_turns)

    # Get turn metrics for system performance calculation
    turn_metrics = runner.get_turn_metrics()

    # Evaluate conversation quality (same evaluator as HEMA)
    evaluator = evaluator or ConversationEvaluator()
    if eval_runs > 1:
        # Use consensus evaluation for more stable scores
        eval_result = evaluator.evaluate_with_consensus(
            conversation_history=runner.get_history_for_evaluation(),
            persona=persona,
            scenario=scenario,
            goal_signaled=record.goal_signaled,
            num_runs=eval_runs,
        )
    else:
        eval_result = evaluator.evaluate(
            conversation_history=runner.get_history_for_evaluation(),
            persona=persona,
            scenario=scenario,
            goal_signaled=record.goal_signaled,
        )

    # Calculate task completion metrics
    actual_max_turns = max_turns if max_turns is not None else scenario.max_turns

    # Reconcile goal_achieved and terminated_reason
    final_goal_achieved = eval_result.goal_achieved

    if eval_result.goal_achieved and record.terminated_reason != "goal_met":
        final_terminated_reason = "goal_met_implicitly"
        turns_to_completion = len(runner.turns)
    elif not eval_result.goal_achieved and record.terminated_reason == "goal_met":
        final_terminated_reason = "premature_goal_signal"
        turns_to_completion = None
    else:
        final_terminated_reason = record.terminated_reason
        turns_to_completion = len(runner.turns) if record.goal_signaled else None

    task_metrics = TaskCompletionMetrics.calculate(
        goal_achieved=final_goal_achieved,
        turns_to_completion=turns_to_completion,
        max_turns=actual_max_turns,
        terminated_reason=final_terminated_reason,
        goal_progress_score=0,
    )

    # Calculate system performance metrics
    system_metrics = SystemPerformanceMetrics.calculate(turn_metrics)

    # Build conversation quality metrics from objective metrics
    last_turn_is_user = (
        len(turn_metrics) > 0 and turn_metrics[-1].speaker == "user"
    )
    quality_metrics = ConversationQualityMetrics(
        dimension_scores={},
        llm_judge_score=0.0,
        objective_metrics=(
            eval_result.objective_metrics.to_dict(
                last_turn_is_user=last_turn_is_user,
                goal_met=final_goal_achieved,
            )
            if eval_result.objective_metrics
            else None
        ),
        evaluation_runs=eval_result.evaluation_runs,
        score_std_dev=eval_result.score_std_dev,
    )

    return ExperimentResult(
        experiment_id=experiment_id,
        persona_id=persona.id,
        scenario_id=scenario.id,
        timestamp=timestamp,
        task_metrics=task_metrics,
        system_metrics=system_metrics,
        quality_metrics=quality_metrics,
        conversation_transcript=eval_result.conversation_transcript,
        turn_details=turn_metrics,
        system_type="vanilla",
        device_state_before=None,
        device_state_after=None,
        device_state_changes=None,
        device_state_verification=None,
        action_correctness=None,
    )


def _run_vanilla_variant_experiment(
    persona: Persona,
    scenario: Scenario,
    vanilla_runner: VanillaLLMRunner,
    system_type: str,
    data_file: str = "data/home_power/energy_data_sample.csv",
    experiment_id: Optional[str] = None,
    evaluator: Optional[ConversationEvaluator] = None,
    verbose: bool = True,
    max_turns: Optional[int] = None,
    opening_mode: OpeningMode = OpeningMode.CONTROLLED,
    eval_runs: int = 1,
) -> ExperimentResult:
    """Internal helper to run a vanilla LLM variant experiment.

    Args:
        persona: User persona for simulation
        scenario: Scenario defining goals and context
        vanilla_runner: Pre-configured vanilla LLM runner instance
        system_type: System type identifier for results
        data_file: Path to energy data CSV file (for reference)
        experiment_id: Optional experiment ID (auto-generated if not provided)
        evaluator: Evaluator instance (created if not provided)
        verbose: Whether to print progress
        max_turns: Maximum turns for conversation
        opening_mode: How to generate opening messages
        eval_runs: Number of evaluation runs for consensus scoring (default: 1)

    Returns:
        ExperimentResult with all metrics and specified system_type
    """
    import uuid

    experiment_id = experiment_id or f"{system_type}_exp_{uuid.uuid4().hex[:8]}"
    timestamp = datetime.now().isoformat()

    # Run the conversation with the provided runner
    runner = VanillaConversationRunner(
        persona=persona,
        scenario=scenario,
        data_context="",  # Not used since we provide vanilla_runner
        vanilla_runner=vanilla_runner,
        verbose=verbose,
        opening_mode=opening_mode,
    )
    record = runner.run(max_turns=max_turns)

    # Get turn metrics for system performance calculation
    turn_metrics = runner.get_turn_metrics()

    # Evaluate conversation quality (same evaluator as HEMA)
    evaluator = evaluator or ConversationEvaluator()
    if eval_runs > 1:
        # Use consensus evaluation for more stable scores
        eval_result = evaluator.evaluate_with_consensus(
            conversation_history=runner.get_history_for_evaluation(),
            persona=persona,
            scenario=scenario,
            goal_signaled=record.goal_signaled,
            num_runs=eval_runs,
        )
    else:
        eval_result = evaluator.evaluate(
            conversation_history=runner.get_history_for_evaluation(),
            persona=persona,
            scenario=scenario,
            goal_signaled=record.goal_signaled,
        )

    # Calculate task completion metrics
    actual_max_turns = max_turns if max_turns is not None else scenario.max_turns

    # Reconcile goal_achieved and terminated_reason
    final_goal_achieved = eval_result.goal_achieved

    if eval_result.goal_achieved and record.terminated_reason != "goal_met":
        final_terminated_reason = "goal_met_implicitly"
        turns_to_completion = len(runner.turns)
    elif not eval_result.goal_achieved and record.terminated_reason == "goal_met":
        final_terminated_reason = "premature_goal_signal"
        turns_to_completion = None
    else:
        final_terminated_reason = record.terminated_reason
        turns_to_completion = len(runner.turns) if record.goal_signaled else None

    task_metrics = TaskCompletionMetrics.calculate(
        goal_achieved=final_goal_achieved,
        turns_to_completion=turns_to_completion,
        max_turns=actual_max_turns,
        terminated_reason=final_terminated_reason,
        goal_progress_score=0,
    )

    # Calculate system performance metrics
    system_metrics = SystemPerformanceMetrics.calculate(turn_metrics)

    # Build conversation quality metrics from objective metrics
    last_turn_is_user = (
        len(turn_metrics) > 0 and turn_metrics[-1].speaker == "user"
    )
    quality_metrics = ConversationQualityMetrics(
        dimension_scores={},
        llm_judge_score=0.0,
        objective_metrics=(
            eval_result.objective_metrics.to_dict(
                last_turn_is_user=last_turn_is_user,
                goal_met=final_goal_achieved,
            )
            if eval_result.objective_metrics
            else None
        ),
        evaluation_runs=eval_result.evaluation_runs,
        score_std_dev=eval_result.score_std_dev,
    )

    return ExperimentResult(
        experiment_id=experiment_id,
        persona_id=persona.id,
        scenario_id=scenario.id,
        timestamp=timestamp,
        task_metrics=task_metrics,
        system_metrics=system_metrics,
        quality_metrics=quality_metrics,
        conversation_transcript=eval_result.conversation_transcript,
        turn_details=turn_metrics,
        system_type=system_type,
        device_state_before=None,
        device_state_after=None,
        device_state_changes=None,
        device_state_verification=None,
        action_correctness=None,
    )


# =============================================================================
# Structured Data Variants (Minimal and CoT)
# =============================================================================


def run_vanilla_structured_experiment(
    persona: Persona,
    scenario: Scenario,
    data_file: str = "data/home_power/energy_data_sample.csv",
    data_days: int = 14,
    experiment_id: Optional[str] = None,
    evaluator: Optional[ConversationEvaluator] = None,
    verbose: bool = True,
    max_turns: Optional[int] = None,
    opening_mode: OpeningMode = OpeningMode.CONTROLLED,
    eval_runs: int = 1,
) -> ExperimentResult:
    """Run experiment with structured data context (minimal prompting).

    Uses HEMA's analysis functions to preprocess data into structured summaries.

    Args:
        persona: User persona for simulation
        scenario: Scenario defining goals and context
        data_file: Path to energy data CSV file
        data_days: Number of days of data to include (default 14)
        experiment_id: Optional experiment ID (auto-generated if not provided)
        evaluator: Evaluator instance (created if not provided)
        verbose: Whether to print progress
        max_turns: Maximum turns for conversation
        opening_mode: How to generate opening messages
        eval_runs: Number of evaluation runs for consensus scoring (default: 1)

    Returns:
        ExperimentResult with all metrics and system_type="vanilla_structured"
    """
    data_context = load_structured_data_context(data_file, days=data_days)
    vanilla_runner = VanillaStructuredRunner(data_context=data_context)

    return _run_vanilla_variant_experiment(
        persona=persona,
        scenario=scenario,
        vanilla_runner=vanilla_runner,
        system_type="vanilla_structured",
        data_file=data_file,
        experiment_id=experiment_id,
        evaluator=evaluator,
        verbose=verbose,
        max_turns=max_turns,
        opening_mode=opening_mode,
        eval_runs=eval_runs,
    )


def run_vanilla_structured_cot_experiment(
    persona: Persona,
    scenario: Scenario,
    data_file: str = "data/home_power/energy_data_sample.csv",
    data_days: int = 14,
    experiment_id: Optional[str] = None,
    evaluator: Optional[ConversationEvaluator] = None,
    verbose: bool = True,
    max_turns: Optional[int] = None,
    opening_mode: OpeningMode = OpeningMode.CONTROLLED,
    eval_runs: int = 1,
) -> ExperimentResult:
    """Run experiment with structured data AND Chain-of-Thought prompting.

    Combines preprocessed structured data with step-by-step reasoning prompts.

    Args:
        persona: User persona for simulation
        scenario: Scenario defining goals and context
        data_file: Path to energy data CSV file
        data_days: Number of days of data to include (default 14)
        experiment_id: Optional experiment ID (auto-generated if not provided)
        evaluator: Evaluator instance (created if not provided)
        verbose: Whether to print progress
        max_turns: Maximum turns for conversation
        opening_mode: How to generate opening messages
        eval_runs: Number of evaluation runs for consensus scoring (default: 1)

    Returns:
        ExperimentResult with all metrics and system_type="vanilla_structured_cot"
    """
    data_context = load_structured_data_context(data_file, days=data_days)
    vanilla_runner = VanillaStructuredCoTRunner(data_context=data_context)

    return _run_vanilla_variant_experiment(
        persona=persona,
        scenario=scenario,
        vanilla_runner=vanilla_runner,
        system_type="vanilla_structured_cot",
        data_file=data_file,
        experiment_id=experiment_id,
        evaluator=evaluator,
        verbose=verbose,
        max_turns=max_turns,
        opening_mode=opening_mode,
        eval_runs=eval_runs,
    )


# =============================================================================
# Experiment Runner Registry
# =============================================================================

# Map system types to their experiment runner functions
VANILLA_EXPERIMENT_RUNNERS = {
    "vanilla": run_vanilla_experiment,
    "vanilla_structured": run_vanilla_structured_experiment,
    "vanilla_structured_cot": run_vanilla_structured_cot_experiment,
}

ALL_VANILLA_SYSTEMS = list(VANILLA_EXPERIMENT_RUNNERS.keys())

# Default 3 systems for focused comparison:
# - vanilla: Raw CSV data with minimal prompting (baseline)
# - vanilla_structured: Effect of data preprocessing
# - vanilla_structured_cot: Effect of CoT prompting on structured data
DEFAULT_VANILLA_SYSTEMS = ["vanilla", "vanilla_structured", "vanilla_structured_cot"]
