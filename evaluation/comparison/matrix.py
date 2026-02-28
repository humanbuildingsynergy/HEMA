#!/usr/bin/env python3
# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/comparison/matrix.py
"""Matrix evaluation runners for comprehensive comparisons.

Implements all-scenarios and full-matrix comparison modes.
"""

import json
import os
import statistics
from datetime import datetime
from typing import Dict, List, Optional

from evaluation.config import PERSONAS, SCENARIOS, get_scenario
from evaluation.metrics import ExperimentResult
from .runners import (
    run_comparison,
    format_multi_system_summary,
    DEFAULT_COMPARISON_SYSTEMS,
)
from .formatters import format_multi_system_report


# Scenarios to include in comparison (Core Analysis + Knowledge scenarios only, no Control Agent)
# These represent the streamlined core scenarios for reproducibility
COMPARISON_SCENARIOS = [
    "understand_utility_rate",
    "appliance_analysis",
    "peak_reduction_strategy",
    "multi_step_investigation",
    "rebate_inquiry",
]


def run_all_scenarios(
    persona_id: str,
    systems: Optional[List[str]] = None,
    num_runs: int = 1,
    data_file: str = "data/home_power/energy_data_sample.csv",
    data_days: int = 14,
    output_dir: str = "evaluation/results",
    verbose: bool = True,
    eval_runs: int = 1,
) -> List[Dict]:
    """Run comparison for all scenarios with one persona.

    Args:
        persona_id: Persona ID to use
        systems: List of system types to compare (default: 4 focused systems)
        num_runs: Number of runs per system (default: 1)
        data_file: Path to energy data CSV
        data_days: Number of days of data
        output_dir: Output directory for results
        verbose: Whether to print progress
        eval_runs: Number of LLM evaluation runs for consensus scoring (default: 1)

    Returns:
        List of comparison summaries
    """
    if systems is None:
        systems = DEFAULT_COMPARISON_SYSTEMS

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_folder = os.path.join(output_dir, f"comparison_{persona_id}_{timestamp}")
    runs_folder = os.path.join(run_folder, "runs")
    aggregated_folder = os.path.join(run_folder, "aggregated")
    os.makedirs(runs_folder, exist_ok=True)
    os.makedirs(aggregated_folder, exist_ok=True)

    all_summaries = []
    total = len(COMPARISON_SCENARIOS)

    print(f"\n{'='*70}")
    print(f"RUNNING ALL SCENARIOS FOR {persona_id}")
    print(f"{'='*70}")
    print(f"Scenarios: {total}")
    print(f"Systems: {', '.join(systems)}")
    print(f"Runs per system: {num_runs}")
    print(f"Output: {run_folder}")
    print(f"{'='*70}\n")

    for i, scenario_id in enumerate(COMPARISON_SCENARIOS, 1):
        print(f"\n[{i}/{total}] {scenario_id}")

        try:
            results = run_comparison(
                persona_id=persona_id,
                scenario_id=scenario_id,
                systems=systems,
                num_runs=num_runs,
                data_file=data_file,
                data_days=data_days,
                verbose=verbose,
                eval_runs=eval_runs,
            )

            # Save individual run results
            for system_type, system_results in results.items():
                for run_idx, result in enumerate(system_results, 1):
                    filename = f"{system_type}_{persona_id}_{scenario_id}_run{run_idx}.json"
                    filepath = os.path.join(runs_folder, filename)
                    with open(filepath, "w") as f:
                        json.dump(result.to_dict(), f, indent=2)

            # Save aggregated results
            summary = format_multi_system_summary(results)
            agg_file = os.path.join(aggregated_folder, f"{persona_id}_{scenario_id}_aggregated.json")
            with open(agg_file, "w") as f:
                json.dump(summary, f, indent=2)

            # Save comparison report
            report = format_multi_system_report(results, num_runs=num_runs)
            report_file = os.path.join(run_folder, f"comparison_{scenario_id}.txt")
            with open(report_file, "w") as f:
                f.write(report)

            all_summaries.append(summary)

        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
            all_summaries.append({
                "persona_id": persona_id,
                "scenario_id": scenario_id,
                "error": str(e),
            })

    # Save overall summary
    summary_file = os.path.join(run_folder, "summary.json")
    with open(summary_file, "w") as f:
        json.dump({
            "timestamp": timestamp,
            "persona_id": persona_id,
            "systems": systems,
            "num_runs": num_runs,
            "eval_runs": eval_runs,
            "total_scenarios": total,
            "results": all_summaries,
        }, f, indent=2)

    print(f"\n{'='*70}")
    print(f"COMPLETED")
    print(f"Results saved to: {run_folder}")
    print(f"{'='*70}\n")

    return all_summaries


def run_full_matrix(
    systems: Optional[List[str]] = None,
    num_runs: int = 1,
    data_file: str = "data/home_power/energy_data_sample.csv",
    data_days: int = 14,
    output_dir: str = "evaluation/results",
    verbose: bool = False,
    eval_runs: int = 1,
) -> List[Dict]:
    """Run comparison for all persona × scenario combinations.

    Args:
        systems: List of system types to compare (default: 4 focused systems)
        num_runs: Number of runs per system (default: 1)
        data_file: Path to energy data CSV
        data_days: Number of days of data
        output_dir: Output directory for results
        verbose: Whether to print progress
        eval_runs: Number of LLM evaluation runs for consensus scoring (default: 1)

    Returns:
        List of all comparison summaries
    """
    if systems is None:
        systems = DEFAULT_COMPARISON_SYSTEMS

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_folder = os.path.join(output_dir, f"comparison_matrix_{timestamp}")
    runs_folder = os.path.join(run_folder, "runs")
    aggregated_folder = os.path.join(run_folder, "aggregated")
    os.makedirs(runs_folder, exist_ok=True)
    os.makedirs(aggregated_folder, exist_ok=True)

    personas = list(PERSONAS.keys())
    total = len(personas) * len(COMPARISON_SCENARIOS)
    total_experiments = total * len(systems) * num_runs

    print(f"\n{'='*70}")
    print(f"FULL COMPARISON MATRIX")
    print(f"{'='*70}")
    print(f"Personas: {len(personas)}")
    print(f"Scenarios: {len(COMPARISON_SCENARIOS)}")
    print(f"Systems: {', '.join(systems)}")
    print(f"Runs per system: {num_runs}")
    print(f"Total combinations: {total}")
    print(f"Total experiments: {total_experiments}")
    print(f"Output: {run_folder}")
    print(f"{'='*70}\n")

    all_summaries = []
    count = 0

    for persona_id in personas:
        for scenario_id in COMPARISON_SCENARIOS:
            count += 1
            print(f"\n[{count}/{total}] {persona_id} × {scenario_id}")

            try:
                results = run_comparison(
                    persona_id=persona_id,
                    scenario_id=scenario_id,
                    systems=systems,
                    num_runs=num_runs,
                    data_file=data_file,
                    data_days=data_days,
                    verbose=verbose,
                    eval_runs=eval_runs,
                )

                # Save individual run results
                for system_type, system_results in results.items():
                    for run_idx, result in enumerate(system_results, 1):
                        filename = f"{system_type}_{persona_id}_{scenario_id}_run{run_idx}.json"
                        filepath = os.path.join(runs_folder, filename)
                        with open(filepath, "w") as f:
                            json.dump(result.to_dict(), f, indent=2)

                # Save aggregated results
                summary = format_multi_system_summary(results)
                agg_file = os.path.join(aggregated_folder, f"{persona_id}_{scenario_id}_aggregated.json")
                with open(agg_file, "w") as f:
                    json.dump(summary, f, indent=2)

                all_summaries.append(summary)

                # Print quick summary
                parts = []
                for sys in systems:
                    if sys in summary.get("systems", {}):
                        obj = summary["systems"][sys].get("objective_metrics", {})
                        qa = obj.get("question_answer_rate", {}).get("mean", 0)
                        goal = summary["systems"][sys].get("goal_achieved", {}).get("success_rate", 0)
                        parts.append(f"{sys}: QA={qa:.0%} Goal={goal:.0%}")
                print(f"  {' | '.join(parts)}")

            except Exception as e:
                print(f"  ERROR: {e}")
                import traceback
                traceback.print_exc()
                all_summaries.append({
                    "persona_id": persona_id,
                    "scenario_id": scenario_id,
                    "error": str(e),
                })

    # Save overall summary
    summary_file = os.path.join(run_folder, "summary.json")
    with open(summary_file, "w") as f:
        json.dump({
            "timestamp": timestamp,
            "systems": systems,
            "num_runs": num_runs,
            "eval_runs": eval_runs,
            "total_combinations": total,
            "completed": len([r for r in all_summaries if "error" not in r]),
            "results": all_summaries,
        }, f, indent=2)

    # Calculate and display aggregate statistics
    valid_summaries = [s for s in all_summaries if "error" not in s]
    if valid_summaries:
        print(f"\n{'='*70}")
        print(f"AGGREGATE RESULTS")
        print(f"{'='*70}")
        print(f"Completed: {len(valid_summaries)}/{total}")

        for system in systems:
            qa_rates = []
            goal_rates = []
            for s in valid_summaries:
                if system in s.get("systems", {}):
                    obj = s["systems"][system].get("objective_metrics", {})
                    qa = obj.get("question_answer_rate", {})
                    if qa:
                        qa_rates.append(qa["mean"])
                    goal = s["systems"][system].get("goal_achieved", {})
                    if goal:
                        goal_rates.append(goal["success_rate"])
            if qa_rates:
                print(f"{system.upper()}: QA Rate={statistics.mean(qa_rates):.1%}, "
                      f"Goal Rate={statistics.mean(goal_rates):.1%}")

        print(f"\nResults saved to: {run_folder}")
        print(f"{'='*70}\n")

    return all_summaries
