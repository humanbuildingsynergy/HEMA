# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/metrics/performance.py
"""Performance and system metrics for evaluation.

Contains dataclasses for task completion, turn-level, and system performance metrics.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import statistics


@dataclass
class TaskCompletionMetrics:
    """Metrics related to goal/task completion."""

    # Core completion metrics
    goal_achieved: bool
    turns_to_completion: Optional[int]  # None if goal not achieved
    max_turns_allowed: Optional[int]  # None means no limit was set
    terminated_reason: str  # "goal_met", "max_turns", "error"

    # Efficiency metrics
    task_efficiency: float  # max_turns / turns_to_completion (higher = better), 0 if not achieved or no limit

    # Partial progress (from LLM judge, 1-5 scale)
    goal_progress_score: int  # How close did user get to goal? 1=no progress, 5=fully achieved

    @classmethod
    def calculate(
        cls,
        goal_achieved: bool,
        turns_to_completion: Optional[int],
        max_turns: Optional[int],
        terminated_reason: str,
        goal_progress_score: int = 0,
    ) -> "TaskCompletionMetrics":
        """Calculate task completion metrics."""
        # Efficiency only makes sense when there's a max_turns limit
        if goal_achieved and turns_to_completion and max_turns:
            efficiency = max_turns / turns_to_completion
        else:
            efficiency = 0.0

        return cls(
            goal_achieved=goal_achieved,
            turns_to_completion=turns_to_completion,
            max_turns_allowed=max_turns,
            terminated_reason=terminated_reason,
            task_efficiency=round(efficiency, 2),
            goal_progress_score=goal_progress_score,
        )


@dataclass
class TurnMetrics:
    """Metrics for a single conversation turn."""

    turn_number: int
    speaker: str  # "user" or "system"
    latency_ms: float  # Response time in milliseconds
    agent_used: Optional[str]  # Which agent handled this turn (for system turns)
    tools_called: List[str]  # Tools invoked during this turn
    had_error: bool
    classification_result: Optional[Dict]  # Classifier output if available

    # Token usage (for LLM calls)
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


# Model pricing per 1M tokens (USD) - as of January 2025
MODEL_PRICING = {
    # OpenAI models
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    # Anthropic models
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    # Google models
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    # Ollama models (free/local)
    "llama3.1:8b": {"input": 0.0, "output": 0.0},
    "llama2:7b-chat": {"input": 0.0, "output": 0.0},
    # Default for unknown models
    "default": {"input": 0.50, "output": 1.50},
}


def calculate_cost(input_tokens: int, output_tokens: int, model: str = "gpt-4o-mini") -> float:
    """Calculate cost in USD for given token usage."""
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


@dataclass
class SystemPerformanceMetrics:
    """System-level performance metrics."""

    # Latency metrics (system turns only)
    per_turn_latency_ms: List[float]
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p95_latency_ms: float  # 95th percentile

    # Routing metrics
    agent_distribution: Dict[str, int]  # {"knowledge_agent": 3, "analysis_agent": 2, ...}
    primary_agent: str  # Most frequently used agent

    # Tool usage metrics
    tools_used: List[str]  # All unique tools called
    tool_call_count: int  # Total tool invocations
    tool_distribution: Dict[str, int]  # {"get_current_weather": 2, ...}

    # Error metrics
    error_count: int
    error_rate: float  # errors / total_system_turns

    # Turn counts
    total_turns: int
    system_turns: int
    user_turns: int

    # Token usage metrics
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    hema_input_tokens: int = 0  # Tokens used by HEMA system
    hema_output_tokens: int = 0
    simulated_user_input_tokens: int = 0  # Tokens used by simulated user
    simulated_user_output_tokens: int = 0

    # Cost metrics (USD)
    total_cost_usd: float = 0.0
    hema_cost_usd: float = 0.0
    simulated_user_cost_usd: float = 0.0
    model_used: str = "gpt-4o-mini"

    @classmethod
    def calculate(
        cls,
        turn_metrics: List[TurnMetrics],
        model: str = "gpt-4o-mini",
    ) -> "SystemPerformanceMetrics":
        """Calculate system performance metrics from turn-level data."""
        system_turns = [t for t in turn_metrics if t.speaker == "system"]
        user_turns = [t for t in turn_metrics if t.speaker == "user"]

        # Latency calculations
        latencies = [t.latency_ms for t in system_turns if t.latency_ms > 0]
        if latencies:
            avg_latency = statistics.mean(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            # Calculate 95th percentile
            sorted_latencies = sorted(latencies)
            p95_idx = int(len(sorted_latencies) * 0.95)
            p95_latency = sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)]
        else:
            avg_latency = min_latency = max_latency = p95_latency = 0.0

        # Agent distribution
        agent_dist: Dict[str, int] = {}
        for t in system_turns:
            if t.agent_used:
                agent_dist[t.agent_used] = agent_dist.get(t.agent_used, 0) + 1
        primary_agent = max(agent_dist, key=agent_dist.get) if agent_dist else "unknown"

        # Tool distribution
        tool_dist: Dict[str, int] = {}
        all_tools: List[str] = []
        for t in system_turns:
            for tool in t.tools_called:
                tool_dist[tool] = tool_dist.get(tool, 0) + 1
                if tool not in all_tools:
                    all_tools.append(tool)
        tool_count = sum(tool_dist.values())

        # Error metrics
        errors = sum(1 for t in system_turns if t.had_error)
        error_rate = errors / len(system_turns) if system_turns else 0.0

        # Token usage calculations
        hema_input = sum(t.input_tokens for t in system_turns)
        hema_output = sum(t.output_tokens for t in system_turns)
        user_input = sum(t.input_tokens for t in user_turns)
        user_output = sum(t.output_tokens for t in user_turns)

        total_input = hema_input + user_input
        total_output = hema_output + user_output
        total_tokens = total_input + total_output

        # Cost calculations
        hema_cost = calculate_cost(hema_input, hema_output, model)
        user_cost = calculate_cost(user_input, user_output, model)
        total_cost = hema_cost + user_cost

        return cls(
            per_turn_latency_ms=latencies,
            avg_latency_ms=round(avg_latency, 2),
            min_latency_ms=round(min_latency, 2),
            max_latency_ms=round(max_latency, 2),
            p95_latency_ms=round(p95_latency, 2),
            agent_distribution=agent_dist,
            primary_agent=primary_agent,
            tools_used=all_tools,
            tool_call_count=tool_count,
            tool_distribution=tool_dist,
            error_count=errors,
            error_rate=round(error_rate, 4),
            total_turns=len(turn_metrics),
            system_turns=len(system_turns),
            user_turns=len(user_turns),
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_tokens=total_tokens,
            hema_input_tokens=hema_input,
            hema_output_tokens=hema_output,
            simulated_user_input_tokens=user_input,
            simulated_user_output_tokens=user_output,
            total_cost_usd=total_cost,
            hema_cost_usd=hema_cost,
            simulated_user_cost_usd=user_cost,
            model_used=model,
        )


@dataclass
class ConversationQualityMetrics:
    """Conversation quality metrics based on objective metrics only.

    All metrics are automatically counted (no subjective LLM judgment).
    """

    # Empty dimension scores (no longer using LLM judgment)
    dimension_scores: Dict[str, float]  # Empty dict (kept for backward compat)
    llm_judge_score: float  # Always 0.0 (no longer using LLM judgment)

    # No longer using subjective evaluations or qualitative feedback
    dimension_evaluations: Optional[Dict] = None

    # Objective metrics (the only metrics now used for evaluation)
    objective_metrics: Optional[Dict[str, any]] = None

    # Metadata
    strengths: List[str] = None
    weaknesses: List[str] = None
    improvement_suggestions: List[str] = None
    evaluation_runs: int = 1
    score_std_dev: float = 0.0

    def __post_init__(self):
        """Ensure lists are initialized."""
        if self.strengths is None:
            self.strengths = []
        if self.weaknesses is None:
            self.weaknesses = []
        if self.improvement_suggestions is None:
            self.improvement_suggestions = []


@dataclass
class AggregateMetrics:
    """Aggregated metrics across multiple experiment runs."""

    num_runs: int
    persona_id: str
    scenario_id: str

    # Task completion aggregates
    goal_achievement_rate: float  # % of runs where goal was achieved
    avg_turns_to_completion: float  # Average turns (only for successful runs)
    avg_task_efficiency: float

    # System performance aggregates
    avg_latency_ms: float
    avg_error_rate: float
    agent_usage_distribution: Dict[str, float]  # Normalized distribution

    # Objective metrics aggregates (no longer using subjective LLM judgment)
    avg_llm_judge_score: float = 0.0  # Always 0.0 (kept for backward compat)
    avg_dimension_scores: Dict[str, float] = None  # Always empty (kept for backward compat)
    score_std_dev: float = 0.0

    def __post_init__(self):
        """Ensure dict fields are initialized."""
        if self.avg_dimension_scores is None:
            self.avg_dimension_scores = {}

    @classmethod
    def aggregate(
        cls,
        results: List["ExperimentResult"],
        persona_id: str,
        scenario_id: str,
    ) -> "AggregateMetrics":
        """Aggregate metrics from multiple experiment results."""
        # Import here to avoid circular imports
        from .experiment import ExperimentResult

        if not results:
            raise ValueError("Cannot aggregate empty results list")

        num_runs = len(results)

        # Task completion
        achieved = [r for r in results if r.task_metrics.goal_achieved]
        goal_rate = len(achieved) / num_runs

        turns_list = [
            r.task_metrics.turns_to_completion
            for r in achieved
            if r.task_metrics.turns_to_completion
        ]
        avg_turns = statistics.mean(turns_list) if turns_list else 0.0

        efficiencies = [r.task_metrics.task_efficiency for r in results]
        avg_efficiency = statistics.mean(efficiencies)

        # System performance
        latencies = [r.system_metrics.avg_latency_ms for r in results]
        avg_latency = statistics.mean(latencies)

        error_rates = [r.system_metrics.error_rate for r in results]
        avg_error = statistics.mean(error_rates)

        # Agent usage (normalized)
        total_agent_counts: Dict[str, int] = {}
        for r in results:
            for agent, count in r.system_metrics.agent_distribution.items():
                total_agent_counts[agent] = total_agent_counts.get(agent, 0) + count
        total_agent_calls = sum(total_agent_counts.values())
        agent_dist = {
            agent: count / total_agent_calls
            for agent, count in total_agent_counts.items()
        } if total_agent_calls > 0 else {}

        # No longer aggregating LLM judge scores (objective metrics only now)
        return cls(
            num_runs=num_runs,
            persona_id=persona_id,
            scenario_id=scenario_id,
            goal_achievement_rate=round(goal_rate, 4),
            avg_turns_to_completion=round(avg_turns, 2),
            avg_task_efficiency=round(avg_efficiency, 2),
            avg_latency_ms=round(avg_latency, 2),
            avg_error_rate=round(avg_error, 4),
            agent_usage_distribution={k: round(v, 4) for k, v in agent_dist.items()},
            avg_llm_judge_score=0.0,
            avg_dimension_scores={},
            score_std_dev=0.0,
        )
