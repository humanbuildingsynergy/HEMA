#!/usr/bin/env python3
# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/run_experiment.py
"""
Entry point for running LLM-as-Simulated-User evaluation experiments.

Usage:
    python -m evaluation.run_experiment
    python -m evaluation.run_experiment --persona confused_newcomer --scenario understand_utility_rate
    python -m evaluation.run_experiment --runs 5  # Run same experiment 5 times for aggregation
    python -m evaluation.run_experiment --list-personas
    python -m evaluation.run_experiment --list-scenarios
    python -m evaluation.run_experiment --validate  # Run validation tests to validate framework
    python -m evaluation.run_experiment --validate --test novice_tou_understanding  # Run specific validation test

Opening Mode Options (for scientific evaluation):
    python -m evaluation.run_experiment --opening-mode controlled  # (default) Reproducible, paraphrases template
    python -m evaluation.run_experiment --opening-mode random      # Diverse, generates from goal/persona only
    python -m evaluation.run_experiment --opening-mode both        # Run both modes for comparison

Matrix Mode (batch evaluation):
    python -m evaluation.run_experiment --matrix                                  # All personas x all scenarios
    python -m evaluation.run_experiment --matrix --runs 5                         # 5 runs per combination
    python -m evaluation.run_experiment --matrix --personas P1,P2 --scenarios S1  # Filtered matrix
    python -m evaluation.run_experiment --matrix --system vanilla_structured_cot  # Vanilla baseline matrix

System Options (for comparative analysis):
    python -m evaluation.run_experiment --system hema     # (default) Run with HEMA multi-agent system
    python -m evaluation.run_experiment --system vanilla  # Run with vanilla LLM (raw CSV, minimal prompt)
    python -m evaluation.run_experiment --system vanilla_structured  # Vanilla LLM with structured data
    python -m evaluation.run_experiment --system vanilla_structured_cot  # Structured data + CoT
    python -m evaluation.run_experiment --system all      # Run HEMA + all vanilla variants
    python -m evaluation.run_experiment --system all_vanilla  # Run all vanilla variants only
"""

import argparse
import json
import os
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from evaluation.config import get_persona, get_scenario, PERSONAS, SCENARIOS
from evaluation.runners.conversation import (
    run_full_experiment,
)
from evaluation.runners.vanilla_conversation import (
    run_vanilla_experiment,
    run_vanilla_structured_experiment,
    run_vanilla_structured_cot_experiment,
    VANILLA_EXPERIMENT_RUNNERS,
    ALL_VANILLA_SYSTEMS,
)
from evaluation.evaluator import ConversationEvaluator
from evaluation.metrics import (
    ExperimentResult,
    AggregateMetrics,
    format_metrics_report,
    format_aggregate_report,
)
from evaluation.runners.simulated_user import OpeningMode


def list_personas():
    """List all available personas."""
    print("\n" + "=" * 60)
    print("AVAILABLE PERSONAS")
    print("=" * 60)
    for pid, persona in PERSONAS.items():
        print(f"\n  ID: {pid}")
        print(f"  Description: {persona.description}")
        print(f"  Technical Level: {persona.technical_level}")
    print()


def list_scenarios():
    """List all available scenarios."""
    print("\n" + "=" * 60)
    print("AVAILABLE SCENARIOS")
    print("=" * 60)
    for sid, scenario in SCENARIOS.items():
        print(f"\n  ID: {sid}")
        print(f"  Name: {scenario.name}")
        print(f"  Description: {scenario.description}")
        print(f"  Max Turns: {scenario.max_turns}")
        print(f"  Evaluation Dimensions: {', '.join(scenario.evaluation_dimensions)}")
    print()


def list_validation_tests():
    """List all available validation tests."""
    from evaluation.validation_tests.scenarios import VALIDATION_SCENARIOS

    print("\n" + "=" * 60)
    print("AVAILABLE VALIDATION TESTS")
    print("=" * 60)
    for scenario in VALIDATION_SCENARIOS:
        print(f"\n  ID: {scenario.id}")
        print(f"  Name: {scenario.name}")
        print(f"  Persona: {scenario.persona_id}")
        print(f"  Scenario: {scenario.scenario_id}")
        print(f"  Focus: {', '.join(scenario.validation_focus)}")
    print()


def run_validation_mode(args):
    """Run validation tests to validate the evaluation framework."""
    from evaluation.validation_tests import run_validation_tests, VALIDATION_SCENARIOS
    from evaluation.validation_tests.runner import format_validation_report, validation_suite_to_dict

    print("\n" + "=" * 60)
    print("FRAMEWORK VALIDATION TESTS")
    print("=" * 60)
    print("\nValidating the LLM-as-user evaluation framework...")
    print("This runs goal-oriented multi-turn conversations to ensure")
    print("the simulated user, HEMA, and evaluator work correctly.\n")

    try:
        # Determine which tests to run
        test_ids = [args.test] if args.test else None

        # Run validation tests
        suite = run_validation_tests(
            scenario_ids=test_ids,
            verbose=not args.quiet,
        )

        # Save results if requested
        if not args.no_save:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Create a new folder for this validation run
            run_folder = os.path.join(args.output_dir, f"validation_run_{timestamp}")
            os.makedirs(run_folder, exist_ok=True)

            # Save detailed text report (includes transcripts)
            txt_filepath = os.path.join(run_folder, f"test_report_{timestamp}.txt")
            report = format_validation_report(suite, include_transcripts=True)
            with open(txt_filepath, "w") as f:
                f.write(report)
            print(f"\nResults saved to: {run_folder}/")
            print(f"  - test_report_{timestamp}.txt (full report with conversation transcripts)")

            # Save JSON with full experiment data (for analysis)
            json_filepath = os.path.join(run_folder, f"structured_data_{timestamp}.json")
            with open(json_filepath, "w") as f:
                json.dump(validation_suite_to_dict(suite), f, indent=2)
            print(f"  - structured_data_{timestamp}.json (machine-readable metrics for analysis)")

        # Return appropriate exit code
        if suite.all_passed:
            return 0
        elif suite.fail_count == 0:
            return 0  # Warnings are OK
        else:
            return 1

    except KeyboardInterrupt:
        print("\n\nValidation tests interrupted by user.")
        return 130

    except Exception as e:
        print(f"\nError during validation tests: {e}")
        import traceback
        traceback.print_exc()
        return 1


def save_experiment_result(result: ExperimentResult, output_dir: str = "evaluation/results"):
    """Save full experiment result to a folder with timestamped files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create a new folder for this evaluation run
    run_folder = os.path.join(output_dir, f"eval_run_{timestamp}")
    os.makedirs(run_folder, exist_ok=True)

    # Save structured JSON data
    json_filepath = os.path.join(run_folder, f"structured_data_{timestamp}.json")
    with open(json_filepath, "w") as f:
        json.dump(result.to_dict(), f, indent=2)

    # Save human-readable text report
    txt_filepath = os.path.join(run_folder, f"test_report_{timestamp}.txt")
    report = format_metrics_report(result)
    with open(txt_filepath, "w") as f:
        f.write(report)

    # Save device state changes if present (for Control Agent evaluation)
    if result.device_state_changes and result.device_state_changes.get("total_changes", 0) > 0:
        device_state_filepath = os.path.join(run_folder, f"device_state_changes_{timestamp}.json")
        with open(device_state_filepath, "w") as f:
            json.dump({
                "summary": {
                    "total_devices_changed": result.device_state_changes.get("total_changes", 0),
                    "devices_changed": result.device_state_changes.get("devices_changed", []),
                    "timestamp_before": result.device_state_changes.get("timestamp_before"),
                    "timestamp_after": result.device_state_changes.get("timestamp_after"),
                },
                "changes_by_device": result.device_state_changes.get("changes_by_device", {}),
                "full_state_before": result.device_state_before,
                "full_state_after": result.device_state_after,
            }, f, indent=2)

    return run_folder, timestamp


def save_aggregate_results(
    aggregate: AggregateMetrics,
    results: list,
    output_dir: str = "evaluation/results",
):
    """Save aggregate metrics and individual results to a folder with timestamped files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create a new folder for this multi-run evaluation
    run_folder = os.path.join(output_dir, f"multirun_{aggregate.num_runs}x_{timestamp}")
    os.makedirs(run_folder, exist_ok=True)

    # Save aggregate metrics summary
    aggregate_dict = {
        "num_runs": aggregate.num_runs,
        "persona_id": aggregate.persona_id,
        "scenario_id": aggregate.scenario_id,
        "goal_achievement_rate": aggregate.goal_achievement_rate,
        "avg_turns_to_completion": aggregate.avg_turns_to_completion,
        "avg_task_efficiency": aggregate.avg_task_efficiency,
        "avg_latency_ms": aggregate.avg_latency_ms,
        "avg_error_rate": aggregate.avg_error_rate,
        "agent_usage_distribution": aggregate.agent_usage_distribution,
        "avg_llm_judge_score": aggregate.avg_llm_judge_score,
        "avg_dimension_scores": aggregate.avg_dimension_scores,
        "score_std_dev": aggregate.score_std_dev,
        "timestamp": timestamp,
    }
    aggregate_file = os.path.join(run_folder, f"aggregate_summary_{timestamp}.json")
    with open(aggregate_file, "w") as f:
        json.dump(aggregate_dict, f, indent=2)

    # Save individual run results
    results_list = [r.to_dict() for r in results]
    results_file = os.path.join(run_folder, f"individual_runs_{timestamp}.json")
    with open(results_file, "w") as f:
        json.dump(results_list, f, indent=2)

    # Save human-readable text report
    txt_filepath = os.path.join(run_folder, f"test_report_{timestamp}.txt")
    report = format_aggregate_report(aggregate)
    with open(txt_filepath, "w") as f:
        f.write(report)

    return run_folder, timestamp


def run_multi_experiment(
    persona,
    scenario,
    num_runs: int,
    verbose: bool = True,
    opening_mode: OpeningMode = OpeningMode.CONTROLLED,
    system_type: str = "hema",
    data_file: str = "data/home_power/energy_data_sample.csv",
    data_days: int = 14,
):
    """Run multiple experiments and aggregate results.

    Args:
        persona: User persona for simulation
        scenario: Scenario defining goals and context
        num_runs: Number of experiment runs
        verbose: Whether to print progress
        opening_mode: How to generate opening messages
        system_type: System to evaluate ("hema" or vanilla variants)
        data_file: Path to energy data CSV for vanilla LLM
        data_days: Number of days of data for vanilla LLM context
    """
    results = []
    evaluator = ConversationEvaluator()

    for i in range(num_runs):
        if verbose:
            print(f"\n{'='*60}")
            print(f"RUN {i + 1} OF {num_runs}")
            print(f"{'='*60}")

        try:
            if system_type == "hema":
                result = run_full_experiment(
                    persona=persona,
                    scenario=scenario,
                    experiment_id=f"exp_{i+1}_{datetime.now().strftime('%H%M%S')}",
                    evaluator=evaluator,
                    verbose=verbose,
                    opening_mode=opening_mode,
                )
            else:
                # Use the appropriate vanilla experiment runner
                runner_func = VANILLA_EXPERIMENT_RUNNERS[system_type]
                result = runner_func(
                    persona=persona,
                    scenario=scenario,
                    data_file=data_file,
                    data_days=data_days,
                    experiment_id=f"{system_type}_exp_{i+1}_{datetime.now().strftime('%H%M%S')}",
                    evaluator=evaluator,
                    verbose=verbose,
                    opening_mode=opening_mode,
                )
            results.append(result)

            if verbose:
                print(f"\nRun {i + 1} complete:")
                print(f"  Goal achieved: {result.task_metrics.goal_achieved}")
                print(f"  LLM judge score: {result.quality_metrics.llm_judge_score}/5.0")
                print(f"  Avg latency: {result.system_metrics.avg_latency_ms:.0f}ms")

        except Exception as e:
            print(f"\nError in run {i + 1}: {e}")
            continue

    if not results:
        raise RuntimeError("All experiment runs failed")

    # Aggregate results
    aggregate = AggregateMetrics.aggregate(
        results=results,
        persona_id=persona.id,
        scenario_id=scenario.id,
    )

    return aggregate, results


def run_matrix(
    personas: List[str],
    scenarios: List[str],
    num_runs: int = 1,
    output_dir: str = "evaluation/results",
    verbose: bool = True,
    system_type: str = "hema",
    data_file: str = "data/home_power/energy_data_sample.csv",
    data_days: int = 14,
):
    """Run all persona x scenario combinations.

    Args:
        personas: List of persona IDs
        scenarios: List of scenario IDs
        num_runs: Number of runs per combination
        output_dir: Directory to save results
        verbose: Whether to print detailed conversation output
        system_type: System to evaluate ("hema" or vanilla variants)
        data_file: Path to energy data CSV for vanilla LLM
        data_days: Number of days of data for vanilla LLM context
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"matrix_{len(personas)}p_{len(scenarios)}s_{num_runs}r_{system_type}_{timestamp}"
    run_folder = os.path.join(output_dir, folder_name)
    os.makedirs(run_folder, exist_ok=True)

    total_combinations = len(personas) * len(scenarios)
    total_runs = total_combinations * num_runs

    print(f"\n{'='*70}")
    print("EVALUATION MATRIX")
    print(f"{'='*70}")
    print(f"System: {system_type.upper()}")
    print(f"Personas: {len(personas)} - {', '.join(personas)}")
    print(f"Scenarios: {len(scenarios)} - {', '.join(scenarios)}")
    print(f"Runs per combination: {num_runs}")
    print(f"Total combinations: {total_combinations}")
    print(f"Total runs: {total_runs}")
    print(f"Output directory: {run_folder}")
    print(f"{'='*70}\n")

    evaluator = ConversationEvaluator()
    all_results = []
    summary_rows = []

    current_combo = 0
    for persona_id in personas:
        for scenario_id in scenarios:
            current_combo += 1
            persona = get_persona(persona_id)
            scenario = get_scenario(scenario_id)

            if not persona:
                print(f"Warning: Unknown persona '{persona_id}', skipping")
                continue
            if not scenario:
                print(f"Warning: Unknown scenario '{scenario_id}', skipping")
                continue

            print(f"\n[{current_combo}/{total_combinations}] {persona_id} x {scenario_id}")
            print("-" * 50)

            combo_results = []
            for run_num in range(1, num_runs + 1):
                run_label = f"Run {run_num}/{num_runs}" if num_runs > 1 else ""
                if run_label:
                    print(f"  {run_label}...")

                try:
                    if system_type == "hema":
                        result = run_full_experiment(
                            persona=persona,
                            scenario=scenario,
                            experiment_id=f"{persona_id}_{scenario_id}_r{run_num}",
                            evaluator=evaluator,
                            verbose=verbose,
                        )
                    else:
                        runner_func = VANILLA_EXPERIMENT_RUNNERS[system_type]
                        result = runner_func(
                            persona=persona,
                            scenario=scenario,
                            data_file=data_file,
                            data_days=data_days,
                            experiment_id=f"{persona_id}_{scenario_id}_r{run_num}",
                            evaluator=evaluator,
                            verbose=verbose,
                        )

                    combo_results.append(result)
                    all_results.append(result)

                    # Save individual run result
                    run_file = os.path.join(
                        run_folder,
                        f"{persona_id}_{scenario_id}_run{run_num}.json"
                    )
                    with open(run_file, "w") as f:
                        json.dump(result.to_dict(), f, indent=2)

                except Exception as e:
                    print(f"    ERROR in run {run_num}: {str(e)[:80]}")

            # Print combination summary
            if combo_results:
                if num_runs > 1:
                    aggregate = AggregateMetrics.aggregate(
                        results=combo_results,
                        persona_id=persona_id,
                        scenario_id=scenario_id,
                    )
                    summary_rows.append({
                        "persona": persona_id,
                        "scenario": scenario_id,
                        "num_runs": len(combo_results),
                        "goal_achievement_rate": aggregate.goal_achievement_rate,
                        "avg_turns": aggregate.avg_turns_to_completion,
                    })
                    print(f"  Summary: {aggregate.goal_achievement_rate:.0%} goal rate, "
                          f"{aggregate.avg_turns_to_completion:.1f} avg turns")
                else:
                    r = combo_results[0]
                    goal_str = "Yes" if r.task_metrics.goal_achieved else "No"
                    print(f"  Goal: {goal_str}, Turns: {r.system_metrics.total_turns}")
                    summary_rows.append({
                        "persona": persona_id,
                        "scenario": scenario_id,
                        "num_runs": 1,
                        "goal_achieved": r.task_metrics.goal_achieved,
                        "turns": r.system_metrics.total_turns,
                    })

    # Save summary
    summary_data = {
        "timestamp": timestamp,
        "system_type": system_type,
        "personas": personas,
        "scenarios": scenarios,
        "runs_per_combination": num_runs,
        "total_combinations": total_combinations,
        "total_runs": len(all_results),
        "results": summary_rows,
    }

    if all_results:
        goals = [r.task_metrics.goal_achieved for r in all_results]
        turns = [r.system_metrics.total_turns for r in all_results]
        summary_data["overall_statistics"] = {
            "goal_achievement_rate": sum(goals) / len(goals),
            "avg_turns": statistics.mean(turns),
        }

    summary_file = os.path.join(run_folder, "summary.json")
    with open(summary_file, "w") as f:
        json.dump(summary_data, f, indent=2)

    # Print final summary
    print(f"\n{'='*70}")
    print("EVALUATION COMPLETE")
    print(f"{'='*70}")
    print(f"Results saved to: {run_folder}/")

    if "overall_statistics" in summary_data:
        stats = summary_data["overall_statistics"]
        print(f"\nOverall Statistics ({len(all_results)} runs):")
        print(f"  Goal Achievement Rate: {stats['goal_achievement_rate']:.1%}")
        print(f"  Average Turns: {stats['avg_turns']:.1f}")

    return all_results, run_folder


def main():
    parser = argparse.ArgumentParser(
        description="Run LLM-as-Simulated-User evaluation experiments"
    )
    parser.add_argument(
        "--persona",
        type=str,
        default="confused_newcomer",
        help="Persona ID to use (default: confused_newcomer)",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default="understand_utility_rate",
        help="Scenario ID to use (default: understand_utility_rate)",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=None,
        help="Override max turns (default: use scenario setting)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of experiment runs for aggregation (default: 1)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="evaluation/results",
        help="Directory to save results (default: evaluation/results)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress real-time conversation output",
    )
    parser.add_argument(
        "--list-personas",
        action="store_true",
        help="List available personas and exit",
    )
    parser.add_argument(
        "--list-scenarios",
        action="store_true",
        help="List available scenarios and exit",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to file",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run validation tests to validate the evaluation framework",
    )
    parser.add_argument(
        "--test",
        type=str,
        default=None,
        help="Specific validation test ID to run (use with --validate)",
    )
    parser.add_argument(
        "--list-validation-tests",
        action="store_true",
        help="List available validation tests and exit",
    )
    parser.add_argument(
        "--opening-mode",
        type=str,
        choices=["controlled", "random", "both"],
        default="controlled",
        help=(
            "Opening message generation mode:\n"
            "  controlled - Paraphrase scenario's template (reproducible)\n"
            "  random - Generate purely from goal/persona (diverse)\n"
            "  both - Run twice with each mode for comparison\n"
            "(default: controlled)"
        ),
    )
    parser.add_argument(
        "--system",
        type=str,
        choices=["hema"] + ALL_VANILLA_SYSTEMS + ["all", "all_vanilla"],
        default="hema",
        help=(
            "System to evaluate:\n"
            "  hema - HEMA multi-agent system (default)\n"
            "  vanilla - Vanilla LLM with raw CSV data, minimal prompt\n"
            "  vanilla_structured - Vanilla LLM with structured data, minimal prompt\n"
            "  vanilla_structured_cot - Vanilla LLM with structured data, CoT prompt\n"
            "  all - Run HEMA + all vanilla variants (4 systems)\n"
            "  all_vanilla - Run all vanilla variants only (3 systems)\n"
        ),
    )
    parser.add_argument(
        "--data-file",
        type=str,
        default="data/home_power/energy_data_sample.csv",
        help="Path to energy data CSV for vanilla LLM (default: energy_data_sample.csv)",
    )
    parser.add_argument(
        "--data-days",
        type=int,
        default=14,
        help="Number of days of data for vanilla LLM context (default: 14)",
    )
    parser.add_argument(
        "--matrix",
        action="store_true",
        help="Run all persona x scenario combinations (evaluation matrix)",
    )
    parser.add_argument(
        "--personas",
        type=str,
        default=None,
        help="Comma-separated list of persona IDs for --matrix (default: all)",
    )
    parser.add_argument(
        "--scenarios",
        type=str,
        default=None,
        help="Comma-separated list of scenario IDs for --matrix (default: all)",
    )

    args = parser.parse_args()

    # Handle list commands
    if args.list_personas:
        list_personas()
        return 0

    if args.list_scenarios:
        list_scenarios()
        return 0

    if args.list_validation_tests:
        list_validation_tests()
        return 0

    # Handle validation test mode
    if args.validate:
        return run_validation_mode(args)

    # Handle matrix mode
    if args.matrix:
        # Parse personas
        if args.personas:
            persona_ids = [p.strip() for p in args.personas.split(",")]
            for p in persona_ids:
                if p not in PERSONAS:
                    print(f"Error: Unknown persona '{p}'")
                    print("Use --list-personas to see available options")
                    return 1
        else:
            persona_ids = list(PERSONAS.keys())

        # Parse scenarios
        if args.scenarios:
            scenario_ids = [s.strip() for s in args.scenarios.split(",")]
            for s in scenario_ids:
                if s not in SCENARIOS:
                    print(f"Error: Unknown scenario '{s}'")
                    print("Use --list-scenarios to see available options")
                    return 1
        else:
            scenario_ids = list(SCENARIOS.keys())

        # Parse system type (single system for matrix mode)
        system_type = args.system
        if system_type in ("all", "all_vanilla"):
            print("Warning: Matrix mode supports a single system type.")
            print("Use run_comparison.py for multi-system comparisons.")
            system_type = "hema" if args.system == "all" else ALL_VANILLA_SYSTEMS[0]
            print(f"Running with: {system_type}")

        try:
            run_matrix(
                personas=persona_ids,
                scenarios=scenario_ids,
                num_runs=args.runs,
                output_dir=args.output_dir,
                verbose=not args.quiet,
                system_type=system_type,
                data_file=args.data_file,
                data_days=args.data_days,
            )
            return 0
        except KeyboardInterrupt:
            print("\n\nInterrupted by user.")
            return 130
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
            return 1

    # Get persona and scenario
    persona = get_persona(args.persona)
    if not persona:
        print(f"Error: Unknown persona '{args.persona}'")
        print("Use --list-personas to see available options")
        return 1

    scenario = get_scenario(args.scenario)
    if not scenario:
        print(f"Error: Unknown scenario '{args.scenario}'")
        print("Use --list-scenarios to see available options")
        return 1

    # Parse opening mode
    if args.opening_mode == "controlled":
        opening_modes = [OpeningMode.CONTROLLED]
    elif args.opening_mode == "random":
        opening_modes = [OpeningMode.RANDOM]
    else:  # "both"
        opening_modes = [OpeningMode.CONTROLLED, OpeningMode.RANDOM]

    # Parse system mode
    if args.system == "all":
        systems_to_run = ["hema"] + ALL_VANILLA_SYSTEMS
    elif args.system == "all_vanilla":
        systems_to_run = ALL_VANILLA_SYSTEMS
    elif args.system in ALL_VANILLA_SYSTEMS or args.system == "hema":
        systems_to_run = [args.system]
    else:
        systems_to_run = [args.system]

    # Print experiment info
    print("\n" + "=" * 60)
    print("LLM-AS-SIMULATED-USER EVALUATION")
    print("=" * 60)
    print(f"\nPersona: {persona.id}")
    print(f"Scenario: {scenario.name} ({scenario.id})")
    print(f"Max Turns: {args.max_turns or scenario.max_turns or 'No limit'}")
    print(f"Number of Runs: {args.runs}")
    print(f"Opening Mode: {args.opening_mode}")
    print(f"System: {args.system}")
    if "vanilla" in systems_to_run:
        print(f"Vanilla Data: {args.data_file} ({args.data_days} days)")
    print(f"Verbose: {not args.quiet}")
    print("\n" + "-" * 60)
    print("Starting experiment...")
    print("-" * 60 + "\n")

    try:
        # Multi-run mode (implies full metrics)
        if args.runs > 1:
            # Multi-run only supports a single system type
            # (use run_comparison.py for multi-system comparisons)
            if len(systems_to_run) > 1:
                print("Warning: Multi-run mode only supports a single system type.")
                print(f"Running with first system: {systems_to_run[0]}")
            system_type = systems_to_run[0]

            # For "both" mode with multi-run, run half with each mode
            if len(opening_modes) == 2:
                runs_per_mode = max(1, args.runs // 2)
                all_results = []
                for mode in opening_modes:
                    print(f"\n{'='*60}")
                    print(f"RUNNING WITH {mode.value.upper()} OPENING MODE")
                    print(f"{'='*60}")
                    _, mode_results = run_multi_experiment(
                        persona=persona,
                        scenario=scenario,
                        num_runs=runs_per_mode,
                        verbose=not args.quiet,
                        opening_mode=mode,
                        system_type=system_type,
                        data_file=args.data_file,
                        data_days=args.data_days,
                    )
                    all_results.extend(mode_results)
                # Aggregate all results together
                aggregate = AggregateMetrics.aggregate(
                    results=all_results,
                    persona_id=persona.id,
                    scenario_id=scenario.id,
                )
                results = all_results
            else:
                aggregate, results = run_multi_experiment(
                    persona=persona,
                    scenario=scenario,
                    num_runs=args.runs,
                    verbose=not args.quiet,
                    opening_mode=opening_modes[0],
                    system_type=system_type,
                    data_file=args.data_file,
                    data_days=args.data_days,
                )

            # Print aggregate report
            print("\n" + format_aggregate_report(aggregate))

            # Save results
            if not args.no_save:
                run_folder, timestamp = save_aggregate_results(
                    aggregate, results, args.output_dir
                )
                print(f"\nResults saved to: {run_folder}/")
                print(f"  - aggregate_summary_{timestamp}.json")
                print(f"  - individual_runs_{timestamp}.json")
                print(f"  - test_report_{timestamp}.txt")

        # Single run with full metrics
        else:
            evaluator = ConversationEvaluator()

            # Handle system comparison mode
            for system_type in systems_to_run:
                # Generate readable system label
                if system_type == "hema":
                    system_label = "HEMA"
                else:
                    system_label = system_type.upper().replace("_", " ")

                # Handle opening mode comparison
                for mode in opening_modes:
                    if len(systems_to_run) > 1 or len(opening_modes) == 2:
                        print(f"\n{'='*60}")
                        if len(systems_to_run) > 1:
                            print(f"RUNNING {system_label}")
                        if len(opening_modes) == 2:
                            print(f"RUNNING WITH {mode.value.upper()} OPENING MODE")
                        print(f"{'='*60}")

                    if system_type == "hema":
                        result = run_full_experiment(
                            persona=persona,
                            scenario=scenario,
                            evaluator=evaluator,
                            verbose=not args.quiet,
                            opening_mode=mode,
                        )
                    else:
                        # Use the appropriate vanilla experiment runner
                        runner_func = VANILLA_EXPERIMENT_RUNNERS[system_type]
                        result = runner_func(
                            persona=persona,
                            scenario=scenario,
                            data_file=args.data_file,
                            data_days=args.data_days,
                            evaluator=evaluator,
                            verbose=not args.quiet,
                            opening_mode=mode,
                        )

                    print("\n" + format_metrics_report(result))

                    if not args.no_save:
                        # Add suffixes for comparison runs
                        suffix = ""
                        if len(systems_to_run) > 1:
                            suffix += f"_{system_type}"

                        run_folder, timestamp = save_experiment_result(result, args.output_dir)
                        # Rename folder with suffix if comparing
                        if suffix:
                            import shutil
                            new_folder = run_folder.rstrip('/') + suffix
                            if os.path.exists(run_folder) and not os.path.exists(new_folder):
                                shutil.move(run_folder, new_folder)
                                run_folder = new_folder
                        print(f"\nResults saved to: {run_folder}/")
                        print(f"  - structured_data_{timestamp}.json")
                        print(f"  - test_report_{timestamp}.txt")

        return 0

    except KeyboardInterrupt:
        print("\n\nExperiment interrupted by user.")
        return 130

    except Exception as e:
        print(f"\nError during experiment: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
