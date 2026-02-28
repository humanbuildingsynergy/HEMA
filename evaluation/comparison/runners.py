#!/usr/bin/env python3
# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/comparison/runners.py
"""System runners for comparative evaluation.

Implements core experiment execution and result aggregation for HEMA and vanilla variants.
"""

import statistics
from typing import Dict, List, Optional, Any

from evaluation.config import get_persona, get_scenario
from evaluation.runners.conversation import run_full_experiment
from evaluation.runners.vanilla_conversation import (
    run_vanilla_experiment,
    VANILLA_EXPERIMENT_RUNNERS,
    ALL_VANILLA_SYSTEMS,
)
from evaluation.metrics import ExperimentResult


# All 7 system types (for --all-systems flag)
ALL_SYSTEM_TYPES = ["hema"] + ALL_VANILLA_SYSTEMS

# Default 4 focused systems for comparison
# Tests: preprocessing effect, CoT effect, multi-agent architecture gap
DEFAULT_COMPARISON_SYSTEMS = ["vanilla", "vanilla_structured", "vanilla_structured_cot", "hema"]

# Subsets for targeted comparisons (legacy, kept for backward compatibility)
RAW_CSV_SYSTEMS = ["hema", "vanilla"]
STRUCTURED_SYSTEMS = ["hema", "vanilla_structured", "vanilla_structured_cot"]

# Experiment runners for all systems
EXPERIMENT_RUNNERS = {
    "hema": run_full_experiment,
    **VANILLA_EXPERIMENT_RUNNERS,
}


def run_comparison(
    persona_id: str,
    scenario_id: str,
    systems: Optional[List[str]] = None,
    num_runs: int = 1,
    data_file: str = "data/home_power/energy_data_sample.csv",
    data_days: int = 14,
    verbose: bool = True,
    eval_runs: int = 1,
) -> Dict[str, List[ExperimentResult]]:
    """Run same test case on specified systems with multiple runs.

    Args:
        persona_id: Persona ID to use
        scenario_id: Scenario ID to use
        systems: List of system types to run (default: ["hema", "vanilla"])
        num_runs: Number of runs per system (default: 1)
        data_file: Path to energy data CSV
        data_days: Number of days of data for vanilla LLM
        verbose: Whether to print progress
        eval_runs: Number of evaluation runs for consensus scoring (default: 1).
                   Use 3+ for more stable scores by averaging LLM evaluations.

    Returns:
        Dict mapping system_type -> list of ExperimentResults (one per run)
    """
    if systems is None:
        systems = DEFAULT_COMPARISON_SYSTEMS

    persona = get_persona(persona_id)
    scenario = get_scenario(scenario_id)

    if verbose:
        print(f"\n{'='*70}")
        print(f"COMPARATIVE EVALUATION")
        print(f"{'='*70}")
        print(f"Persona: {persona_id}")
        print(f"Scenario: {scenario.name} ({scenario_id})")
        print(f"Systems: {', '.join(systems)}")
        print(f"Runs per system: {num_runs}")
        print(f"Data: {data_file} ({data_days} days)")
        print(f"{'='*70}\n")

    results = {system: [] for system in systems}

    for run_idx in range(num_runs):
        if num_runs > 1 and verbose:
            print(f"\n{'='*50}")
            print(f"RUN {run_idx + 1} OF {num_runs}")
            print(f"{'='*50}")

        for system_type in systems:
            if verbose:
                system_label = system_type.upper().replace("_", " ")
                print(f"\n{'-'*50}")
                print(f"Running {system_label}...")
                print(f"{'-'*50}")

            runner_func = EXPERIMENT_RUNNERS[system_type]
            experiment_id = f"{system_type}_{persona_id}_{scenario_id}_run{run_idx + 1}"

            if system_type == "hema":
                result = runner_func(
                    persona=persona,
                    scenario=scenario,
                    experiment_id=experiment_id,
                    verbose=verbose,
                    data_days=data_days,
                    eval_runs=eval_runs,
                )
            else:
                result = runner_func(
                    persona=persona,
                    scenario=scenario,
                    data_file=data_file,
                    data_days=data_days,
                    experiment_id=experiment_id,
                    verbose=verbose,
                    eval_runs=eval_runs,
                )

            results[system_type].append(result)

            if verbose:
                obj = result.quality_metrics.objective_metrics or {}
                print(f"  QA Rate: {obj.get('question_answer_rate', 0):.2f}")
                print(f"  Goal: {'Achieved' if result.task_metrics.goal_achieved else 'Not achieved'}")

    return results


def aggregate_system_results(results: List[ExperimentResult]) -> Dict[str, Any]:
    """Compute aggregated statistics across multiple runs.

    Args:
        results: List of ExperimentResults from multiple runs

    Returns:
        Dict with mean, std for all metrics including:
        - System efficiency (tokens, latency, cost, error_rate)
        - Objective quality metrics (question_answer_rate, jargon_explanation_rate, etc.)
        - Task metrics (goal_achieved, task_efficiency)
    """
    if not results:
        return {}

    def safe_stdev(values):
        return statistics.stdev(values) if len(values) > 1 else 0

    def safe_mean(values):
        return statistics.mean(values) if values else 0

    # === Task Completion Metrics ===
    goals_achieved = [1 if r.task_metrics.goal_achieved else 0 for r in results]
    task_efficiencies = [r.task_metrics.task_efficiency for r in results]
    goal_progress_scores = [r.task_metrics.goal_progress_score for r in results]

    # === System Performance Metrics ===
    latencies = [r.system_metrics.avg_latency_ms for r in results]
    p95_latencies = [r.system_metrics.p95_latency_ms for r in results]
    costs = [r.system_metrics.total_cost_usd for r in results]
    turns = [r.system_metrics.total_turns for r in results]
    tool_calls = [r.system_metrics.tool_call_count for r in results]
    total_tokens = [r.system_metrics.total_tokens for r in results]
    input_tokens = [r.system_metrics.total_input_tokens for r in results]
    output_tokens = [r.system_metrics.total_output_tokens for r in results]
    error_rates = [r.system_metrics.error_rate for r in results]

    # === Objective Quality Metrics (from quality_metrics.objective_metrics) ===
    objective_metrics_agg = {}
    all_obj_metrics = set()
    for r in results:
        if r.quality_metrics.objective_metrics:
            all_obj_metrics.update(r.quality_metrics.objective_metrics.keys())

    for metric in all_obj_metrics:
        values = []
        for r in results:
            if r.quality_metrics.objective_metrics:
                val = r.quality_metrics.objective_metrics.get(metric)
                if val is not None and isinstance(val, (int, float)):
                    values.append(val)
        if values:
            objective_metrics_agg[metric] = {
                "mean": safe_mean(values),
                "std": safe_stdev(values),
            }

    return {
        # Identifiers
        "system_type": results[0].system_type,
        "persona_id": results[0].persona_id,
        "scenario_id": results[0].scenario_id,
        "n_runs": len(results),

        # Task completion metrics
        "goal_achieved": {
            "success_rate": statistics.mean(goals_achieved),
            "count": sum(goals_achieved),
            "total": len(goals_achieved),
        },
        "task_efficiency": {
            "mean": safe_mean(task_efficiencies),
            "std": safe_stdev(task_efficiencies),
        },
        "goal_progress_score": {
            "mean": safe_mean(goal_progress_scores),
            "std": safe_stdev(goal_progress_scores),
        },

        # System performance metrics
        "latency_ms": {
            "mean": statistics.mean(latencies),
            "std": safe_stdev(latencies),
        },
        "p95_latency_ms": {
            "mean": safe_mean(p95_latencies),
            "std": safe_stdev(p95_latencies),
        },
        "total_cost_usd": {
            "mean": statistics.mean(costs),
            "std": safe_stdev(costs),
        },
        "total_turns": {
            "mean": statistics.mean(turns),
            "std": safe_stdev(turns),
        },
        "tool_call_count": {
            "mean": statistics.mean(tool_calls),
            "std": safe_stdev(tool_calls),
        },
        "total_tokens": {
            "mean": safe_mean(total_tokens),
            "std": safe_stdev(total_tokens),
        },
        "input_tokens": {
            "mean": safe_mean(input_tokens),
            "std": safe_stdev(input_tokens),
        },
        "output_tokens": {
            "mean": safe_mean(output_tokens),
            "std": safe_stdev(output_tokens),
        },
        "error_rate": {
            "mean": safe_mean(error_rates),
            "std": safe_stdev(error_rates),
        },

        # Objective quality metrics (countable, not LLM-judged)
        "objective_metrics": objective_metrics_agg,

        # Individual run references
        "individual_run_ids": [r.experiment_id for r in results],
    }


def format_multi_system_summary(
    results: Dict[str, List[ExperimentResult]],
) -> Dict[str, Any]:
    """Generate summary with aggregated statistics for multiple systems.

    Args:
        results: Dict mapping system_type -> list of ExperimentResults

    Returns:
        Dict with aggregated stats for each system and comparisons
    """
    summary = {
        "persona_id": None,
        "scenario_id": None,
        "systems": {},
    }

    # Aggregate each system's results
    for system_type, system_results in results.items():
        if system_results:
            agg = aggregate_system_results(system_results)
            summary["systems"][system_type] = agg
            if summary["persona_id"] is None:
                summary["persona_id"] = agg["persona_id"]
                summary["scenario_id"] = agg["scenario_id"]

    return summary
