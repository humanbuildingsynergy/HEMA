# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/runners/conversation.py
"""
Conversation Runner for LLM-as-Simulated-User evaluation.

Orchestrates multi-turn conversations between the simulated user
and the HEMA system, collecting data for evaluation.
"""

import time
from datetime import datetime
from typing import Dict, List, Optional, Any

from ..config import Persona, Scenario
from .dataclasses import ConversationTurn, ConversationRecord
from .simulated_user import SimulatedUser, OpeningMode
from ..evaluator import ConversationEvaluator, EvaluationResult
from ..evaluator.objective_metrics import extract_control_semantic_metrics
from .conversation_monitor import ConversationMonitor, extract_scenario_keywords
from ..metrics import (
    TurnMetrics,
    TaskCompletionMetrics,
    SystemPerformanceMetrics,
    ConversationQualityMetrics,
    ExperimentResult,
    verify_device_state_changes,
    evaluate_action_correctness,
)
from ..metrics.control_process import compute_control_process_metrics

# Import the HEMA system
from agents.graph import HEMAGraphRunner


class ConversationRunner:
    """
    Runs and records conversations between simulated users and HEMA.

    Manages the dialogue loop, tracks state, and prepares data for evaluation.
    """

    def __init__(
        self,
        persona: Persona,
        scenario: Scenario,
        hema_runner: Optional[HEMAGraphRunner] = None,
        simulated_user: Optional[SimulatedUser] = None,
        verbose: bool = True,
        opening_mode: OpeningMode = OpeningMode.CONTROLLED,
    ):
        """
        Initialize the conversation runner.

        Args:
            persona: User persona for simulation
            scenario: Scenario defining goals and context
            hema_runner: HEMA system instance (created if not provided)
            simulated_user: Simulated user instance (created if not provided)
            verbose: Whether to print conversation in real-time
            opening_mode: How to generate opening messages:
                - CONTROLLED: Paraphrase scenario's opening_message template
                - RANDOM: Generate purely from goal and persona
        """
        self.persona = persona
        self.scenario = scenario
        self.verbose = verbose
        self.opening_mode = opening_mode

        # Initialize HEMA system
        self.hema = hema_runner or HEMAGraphRunner(use_persistence=True)

        # Initialize simulated user
        self.simulated_user = simulated_user or SimulatedUser(
            persona=persona,
            scenario=scenario,
            opening_mode=opening_mode,
        )

        # Session ID for HEMA
        self.session_id = f"eval_{persona.id}_{scenario.id}_{int(time.time())}"

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
        """
        Run the complete conversation.

        Args:
            max_turns: Maximum number of turns. If not specified, uses scenario default.
                       If None (no limit), conversation continues until goal is met.

        Returns:
            ConversationRecord with full conversation data
        """
        # Use provided max_turns, fall back to scenario setting (which may be None for no limit)
        if max_turns is None:
            max_turns = self.scenario.max_turns
        start_time = datetime.now()
        start_timestamp = time.time()

        if self.verbose:
            print("\n" + "=" * 60)
            print(f"STARTING CONVERSATION")
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
            # If max_turns is None, loop indefinitely until goal is met
            turn_count = 1
            while max_turns is None or turn_count < max_turns:
                # Get HEMA's response with performance tracking
                bear_result = self._get_bear_response(user_turn.message)
                bear_response = bear_result["response"]

                self._record_turn(
                    speaker="system",
                    message=bear_response,
                    latency_ms=bear_result["latency_ms"],
                    agent_used=bear_result["agent_used"],
                    tools_called=bear_result["tools_called"],
                    had_error=bear_result["had_error"],
                    classification_result=bear_result["classification_result"],
                    input_tokens=bear_result.get("input_tokens", 0),
                    output_tokens=bear_result.get("output_tokens", 0),
                )

                if self.verbose:
                    latency_info = f" ({bear_result['latency_ms']:.0f}ms"
                    if bear_result["agent_used"]:
                        latency_info += f", {bear_result['agent_used']}"
                    latency_info += ")"
                    print(f"[HEMA]{latency_info} {bear_response}\n")

                # Get user's next response (natural follow-ups or wrap-up)
                user_turn = self.simulated_user.respond_to_system(bear_response)
                self._record_turn(
                    "user",
                    user_turn.message,
                    input_tokens=user_turn.input_tokens,
                    output_tokens=user_turn.output_tokens,
                )

                if self.verbose:
                    print(f"[User] {user_turn.message}\n")

                # NATURAL WRAP-UP DETECTION: Check if user message contains satisfaction signals
                # This allows natural conversation flow while detecting when user is satisfied
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
            print(f"CONVERSATION ENDED")
            print(f"Reason: {terminated_reason}")
            print(f"Total turns: {len(self.turns)}")
            print(f"Duration: {total_duration:.1f}s")
            print("=" * 60 + "\n")

        return ConversationRecord(
            persona_id=self.persona.id,
            scenario_id=self.scenario.id,
            system_type="hema",
            start_time=start_time,
            end_time=end_time,
            turns=self.turns.copy(),
            goal_signaled=self.goal_signaled,
            terminated_reason=terminated_reason,
            total_duration_seconds=total_duration,
        )

    def _get_bear_response(self, user_message: str) -> Dict[str, Any]:
        """
        Get response from the HEMA system with performance tracking.

        Returns:
            Dict with 'response', 'latency_ms', 'agent_used', 'tools_called',
            'had_error', 'classification_result', 'input_tokens', 'output_tokens'
        """
        start_time = time.time()
        had_error = False
        agent_used = None
        tools_called = []
        classification_result = None
        input_tokens = 0
        output_tokens = 0

        try:
            result = self.hema.invoke(user_message, session_id=self.session_id)
            response = result.get("final_response", "I'm sorry, I couldn't process that.")

            # Extract agent routing information
            # The graph uses "target_agent" from the classifier node
            agent_used = result.get("target_agent", result.get("selected_agent", result.get("agent_type")))

            # Extract classification result if available
            classification_result = result.get("classification_result")

            # Extract tools called from agent response
            # The graph result may include tool invocations
            if "tool_calls" in result:
                tools_called = [tc.get("name", str(tc)) for tc in result["tool_calls"]]
            elif "tools_used" in result:
                tools_called = result["tools_used"]

            # Extract token usage from graph result
            input_tokens = result.get("input_tokens", 0)
            output_tokens = result.get("output_tokens", 0)

            # Handle clarification requests from HEMA
            if result.get("needs_clarification"):
                # For evaluation, we'll let the simulated user handle clarification naturally
                pass

        except Exception as e:
            response = f"I encountered an error: {str(e)}"
            had_error = True

        latency_ms = (time.time() - start_time) * 1000

        return {
            "response": response,
            "latency_ms": latency_ms,
            "agent_used": agent_used,
            "tools_called": tools_called,
            "had_error": had_error,
            "classification_result": classification_result,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }

    def _record_turn(
        self,
        speaker: str,
        message: str,
        latency_ms: float = 0.0,
        agent_used: Optional[str] = None,
        tools_called: Optional[List[str]] = None,
        had_error: bool = False,
        classification_result: Optional[Dict] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        """Record a conversation turn with optional performance metrics."""
        turn = ConversationTurn(
            turn_number=len(self.turns) + 1,
            speaker=speaker,
            message=message,
            timestamp=time.time(),
            latency_ms=latency_ms,
            agent_used=agent_used,
            tools_called=tools_called or [],
            had_error=had_error,
            classification_result=classification_result,
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
                agent_used=turn.agent_used,
                tools_called=turn.tools_called,
                had_error=turn.had_error,
                classification_result=turn.classification_result,
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
        self.monitor.reset()
        self.session_id = f"eval_{self.persona.id}_{self.scenario.id}_{int(time.time())}"


def run_single_evaluation(
    persona: Persona,
    scenario: Scenario,
    evaluator: Optional[ConversationEvaluator] = None,
    verbose: bool = True,
    opening_mode: OpeningMode = OpeningMode.CONTROLLED,
) -> EvaluationResult:
    """
    Run a single conversation and evaluate it.

    Convenience function that combines conversation running and evaluation.

    Args:
        persona: User persona for simulation
        scenario: Scenario defining goals and context
        evaluator: Evaluator instance (created if not provided)
        verbose: Whether to print progress
        opening_mode: How to generate opening messages (CONTROLLED or RANDOM)

    Returns:
        EvaluationResult with scores and analysis
    """
    # Run the conversation
    runner = ConversationRunner(
        persona=persona,
        scenario=scenario,
        verbose=verbose,
        opening_mode=opening_mode,
    )
    record = runner.run()

    # Evaluate the conversation
    evaluator = evaluator or ConversationEvaluator()
    result = evaluator.evaluate(
        conversation_history=runner.get_history_for_evaluation(),
        persona=persona,
        scenario=scenario,
        goal_signaled=record.goal_signaled,
    )

    return result


def run_full_experiment(
    persona: Persona,
    scenario: Scenario,
    experiment_id: Optional[str] = None,
    evaluator: Optional[ConversationEvaluator] = None,
    verbose: bool = True,
    max_turns: Optional[int] = None,
    opening_mode: OpeningMode = OpeningMode.CONTROLLED,
    data_days: int = 14,
    eval_runs: int = 1,
) -> ExperimentResult:
    """
    Run a complete experiment with full metrics collection.

    This is the main entry point for running evaluations with comprehensive
    task completion, system performance, and quality metrics.

    Args:
        persona: User persona for simulation
        scenario: Scenario defining goals and context
        experiment_id: Optional experiment ID (auto-generated if not provided)
        evaluator: Evaluator instance (created if not provided)
        verbose: Whether to print progress
        max_turns: Maximum turns for conversation. If not specified, uses scenario
                   default (which may be None for no limit).
        opening_mode: How to generate opening messages:
            - CONTROLLED: Paraphrase scenario's opening_message template (reproducible)
            - RANDOM: Generate purely from goal and persona (diverse)
        data_days: Number of days of data to use from start of dataset (default: 14).
                   Ensures consistency with vanilla LLM baselines.
        eval_runs: Number of evaluation runs for consensus scoring (default: 1).
                   Use 3+ for more stable scores by averaging across multiple LLM evaluations.

    Returns:
        ExperimentResult with all metrics and conversation data
    """
    import uuid
    from agents.tools.analysis_tools.cache import set_eval_data_days, clear_data_cache

    experiment_id = experiment_id or f"exp_{uuid.uuid4().hex[:8]}"
    timestamp = datetime.now().isoformat()

    # Clear data cache and set evaluation data window for consistency
    clear_data_cache()
    set_eval_data_days(data_days)

    # Capture device state before conversation (for Control Agent evaluation)
    device_state_before = None
    device_state_after = None
    device_state_changes = None

    try:
        from agents.tools.control_tools.device_state import (
            reset_device_state,
            get_device_state_snapshot,
            compare_device_states,
        )
        # Reset device state to ensure clean slate from JSON config
        reset_device_state()
        device_state_before = get_device_state_snapshot()
    except Exception as e:
        if verbose:
            print(f"[INFO] Device state tracking not available: {e}")

    # Run the conversation
    runner = ConversationRunner(
        persona=persona,
        scenario=scenario,
        verbose=verbose,
        opening_mode=opening_mode,
    )
    record = runner.run(max_turns=max_turns)

    # Capture device state after conversation
    if device_state_before is not None:
        try:
            device_state_after = get_device_state_snapshot()
            device_state_changes = compare_device_states(device_state_before, device_state_after)
        except Exception as e:
            if verbose:
                print(f"[INFO] Could not capture device state after: {e}")

    # Get turn metrics for system performance calculation
    turn_metrics = runner.get_turn_metrics()

    # Evaluate conversation using objective metrics
    evaluator = evaluator or ConversationEvaluator()
    eval_result = evaluator.evaluate(
        conversation_history=runner.get_history_for_evaluation(),
        persona=persona,
        scenario=scenario,
        goal_signaled=record.goal_signaled,
    )

    # Calculate task completion metrics
    # Use the actual max_turns used (parameter overrides scenario default)
    actual_max_turns = max_turns if max_turns is not None else scenario.max_turns

    # Goal achievement is determined by whether the user signaled goal completion
    # (no longer using subjective LLM judgment)
    final_goal_achieved = record.goal_signaled
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

    # Build conversation quality metrics from objective metrics only
    # (no longer using subjective LLM judgment)
    last_turn_is_user = (
        len(turn_metrics) > 0 and turn_metrics[-1].speaker == "user"
    )
    quality_metrics = ConversationQualityMetrics(
        dimension_scores={},  # No longer using dimension scores
        llm_judge_score=0.0,  # No longer using LLM judge scores
        dimension_evaluations=None,
        strengths=[],
        weaknesses=[],
        improvement_suggestions=[],
        # Include objective metrics for analysis
        objective_metrics=(
            eval_result.objective_metrics.to_dict(
                last_turn_is_user=last_turn_is_user,
                goal_met=final_goal_achieved,
            )
            if eval_result.objective_metrics
            else None
        ),
        evaluation_runs=1,
        score_std_dev=0.0,
    )

    # Build transcript
    transcript = eval_result.conversation_transcript

    # Get household profile from data cache (if data was loaded during conversation)
    household_profile = None
    try:
        from agents.tools.analysis_tools import get_data_cache
        cache = get_data_cache()
        household_profile = cache.get("household_profile")
    except Exception:
        pass  # Household profile is optional

    # Verify device state changes against expected changes (for Control Agent scenarios)
    device_state_verification = None
    if scenario.expected_device_changes:
        device_state_verification = verify_device_state_changes(
            expected_changes=scenario.expected_device_changes,
            device_state_changes=device_state_changes,
            device_state_before=device_state_before,
            device_state_after=device_state_after,
        )
        if verbose and device_state_verification:
            status = "PASSED" if device_state_verification.verification_passed else "FAILED"
            print(f"\n[DEVICE STATE VERIFICATION: {status}]")
            print(f"  Checks: {device_state_verification.passed_checks}/{device_state_verification.total_checks} passed")

    # Evaluate action correctness (for Control Agent scenarios)
    action_correctness = None
    if device_state_changes:
        action_correctness = evaluate_action_correctness(
            device_state_changes=device_state_changes,
            device_state_after=device_state_after,
        )
        if verbose and action_correctness:
            print(f"\n[ACTION CORRECTNESS: {action_correctness.correctness_score:.1f}%]")
            print(f"  Evaluated: {action_correctness.actions_evaluated}, Correct: {action_correctness.actions_correct}, Suboptimal: {action_correctness.actions_suboptimal}")
            if action_correctness.schedule_correctness is not None:
                print(f"  Schedule (off-peak): {action_correctness.schedule_correctness:.1f}%")
            if action_correctness.temperature_correctness is not None:
                print(f"  Temperature (efficient): {action_correctness.temperature_correctness:.1f}%")

    # Compute control process metrics (for Control Agent scenarios)
    control_process_metrics = None
    if turn_metrics:
        # Convert TurnMetrics to dicts for the computation
        turn_details_dicts = [
            {
                "turn_number": t.turn_number,
                "speaker": t.speaker,
                "tools_called": t.tools_called,
            }
            for t in turn_metrics
        ]

        # Check if there are control actions (for semantic metric extraction)
        has_control_actions = any(
            any(
                tool.split("(")[0].strip() in {"control_device", "schedule_device_action"}
                for tool in t.get("tools_called", [])
            )
            for t in turn_details_dicts
        )

        # Extract control-specific semantic metrics if there were control actions
        control_semantic_metrics = None
        if has_control_actions:
            try:
                control_semantic_metrics = extract_control_semantic_metrics(
                    conversation_history=runner.get_history_for_evaluation(),
                    llm=evaluator.llm,
                )
            except Exception as e:
                if verbose:
                    print(f"[INFO] Control semantic extraction failed: {e}")

        control_process_metrics = compute_control_process_metrics(
            turn_details_dicts,
            semantic_metrics=control_semantic_metrics,
        )
        if verbose and control_process_metrics and control_process_metrics.control_tools_called > 0:
            print(f"\n[CONTROL PROCESS METRICS]")
            print(f"  Info-before-action rate: {control_process_metrics.info_before_action_rate:.1%}")
            print(f"  Info tools called: {control_process_metrics.info_tools_called}, Control tools called: {control_process_metrics.control_tools_called}")
            if control_process_metrics.action_confirmation_rate > 0 or control_process_metrics.action_explanation_rate > 0:
                print(f"  Action confirmation rate: {control_process_metrics.action_confirmation_rate:.1%}, Explanation rate: {control_process_metrics.action_explanation_rate:.1%}")

    return ExperimentResult(
        experiment_id=experiment_id,
        persona_id=persona.id,
        scenario_id=scenario.id,
        timestamp=timestamp,
        task_metrics=task_metrics,
        system_metrics=system_metrics,
        quality_metrics=quality_metrics,
        conversation_transcript=transcript,
        turn_details=turn_metrics,
        household_profile=household_profile,
        device_state_before=device_state_before,
        device_state_after=device_state_after,
        device_state_changes=device_state_changes,
        device_state_verification=device_state_verification,
        action_correctness=action_correctness,
        control_process_metrics=control_process_metrics,
    )
