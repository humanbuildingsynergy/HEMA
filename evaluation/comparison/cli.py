#!/usr/bin/env python3
# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/comparison/cli.py
"""Command-line interface for comparative evaluation.

Handles argument parsing and execution of comparison modes.
"""

import argparse
import json
import os
import sys
from datetime import datetime

from evaluation.config import get_scenario
from .runners import (
    run_comparison,
    DEFAULT_COMPARISON_SYSTEMS,
    ALL_SYSTEM_TYPES,
    RAW_CSV_SYSTEMS,
    STRUCTURED_SYSTEMS,
)
from .matrix import (
    run_all_scenarios,
    run_full_matrix,
    COMPARISON_SCENARIOS,
)
from .formatters import format_multi_system_report, format_multi_system_summary


def main():
    parser = argparse.ArgumentParser(
        description="Run comparative evaluation between HEMA and Vanilla LLM variants"
    )

    parser.add_argument(
        "--persona",
        type=str,
        default="confused_newcomer",
        help="Persona ID (default: confused_newcomer)",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        help="Scenario ID (required unless --all-scenarios or --full-matrix)",
    )
    parser.add_argument(
        "--all-scenarios",
        action="store_true",
        help="Run all scenarios for the specified persona",
    )
    parser.add_argument(
        "--full-matrix",
        action="store_true",
        help="Run all persona × scenario combinations",
    )

    # System selection arguments
    parser.add_argument(
        "--systems",
        type=str,
        help="Comma-separated list of systems (default: vanilla,vanilla_structured,vanilla_structured_cot,hema)",
    )
    parser.add_argument(
        "--all-systems",
        action="store_true",
        help="Compare all 7 systems (HEMA + 6 vanilla variants)",
    )
    parser.add_argument(
        "--raw-only",
        action="store_true",
        help="Compare HEMA + raw CSV variants only (4 systems)",
    )
    parser.add_argument(
        "--structured-only",
        action="store_true",
        help="Compare HEMA + structured data variants only (4 systems)",
    )

    # Statistical rigor
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of runs per system for statistical rigor (default: 1, recommended: 3)",
    )
    parser.add_argument(
        "--eval-runs",
        type=int,
        default=1,
        help="Number of LLM evaluation runs for consensus scoring (default: 1, recommended: 3). "
             "Evaluates each conversation multiple times and averages scores to reduce variance.",
    )

    parser.add_argument(
        "--data-file",
        type=str,
        default="data/home_power/energy_data_sample.csv",
        help="Path to energy data CSV",
    )
    parser.add_argument(
        "--data-days",
        type=int,
        default=14,
        help="Number of days of data for vanilla LLM (default: 14)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="evaluation/results",
        help="Output directory for results",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose output",
    )
    parser.add_argument(
        "--list-scenarios",
        action="store_true",
        help="List available scenarios for comparison",
    )
    parser.add_argument(
        "--list-systems",
        action="store_true",
        help="List available systems for comparison",
    )

    args = parser.parse_args()

    if args.list_scenarios:
        print("\nScenarios included in comparison (Analysis + Knowledge):\n")
        for s in COMPARISON_SCENARIOS:
            scenario = get_scenario(s)
            print(f"  {s}: {scenario.name}")
        print()
        return

    if args.list_systems:
        print("\nAvailable systems for comparison:\n")
        print("  DEFAULT (4 systems - recommended for standard comparison):")
        print("    vanilla                  - Raw CSV, minimal prompting")
        print("    vanilla_structured       - Structured data, minimal prompting")
        print("    vanilla_structured_cot   - Structured data, Chain-of-Thought")
        print("    hema                     - Multi-agent architecture with tools")
        print("\n  This tests: preprocessing effect → CoT effect → multi-agent gap")
        print("\n  Shortcuts:")
        print("    (no flag)           : Default 4 systems (recommended)")
        print("    --all-systems       : All 5 systems")
        print("    --raw-only          : hema + raw CSV variants (3 systems)")
        print("    --structured-only   : hema + structured variants (3 systems)")
        print()
        return

    # Determine which systems to run
    if args.all_systems:
        systems = ALL_SYSTEM_TYPES
    elif args.raw_only:
        systems = RAW_CSV_SYSTEMS
    elif args.structured_only:
        systems = STRUCTURED_SYSTEMS
    elif args.systems:
        systems = [s.strip() for s in args.systems.split(",")]
        # Validate systems
        invalid = [s for s in systems if s not in ALL_SYSTEM_TYPES]
        if invalid:
            print(f"Error: Unknown system(s): {', '.join(invalid)}")
            print(f"Valid systems: {', '.join(ALL_SYSTEM_TYPES)}")
            sys.exit(1)
    else:
        systems = DEFAULT_COMPARISON_SYSTEMS  # Default: 4 focused systems

    verbose = not args.quiet

    if args.full_matrix:
        run_full_matrix(
            systems=systems,
            num_runs=args.runs,
            data_file=args.data_file,
            data_days=args.data_days,
            output_dir=args.output_dir,
            verbose=verbose,
            eval_runs=args.eval_runs,
        )
    elif args.all_scenarios:
        run_all_scenarios(
            persona_id=args.persona,
            systems=systems,
            num_runs=args.runs,
            data_file=args.data_file,
            data_days=args.data_days,
            output_dir=args.output_dir,
            verbose=verbose,
            eval_runs=args.eval_runs,
        )
    elif args.scenario:
        results = run_comparison(
            persona_id=args.persona,
            scenario_id=args.scenario,
            systems=systems,
            num_runs=args.runs,
            data_file=args.data_file,
            data_days=args.data_days,
            verbose=verbose,
            eval_runs=args.eval_runs,
        )

        # Print comparison report
        report = format_multi_system_report(results, num_runs=args.runs)
        print(report)

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_folder = os.path.join(args.output_dir, f"comparison_{timestamp}")
        runs_folder = os.path.join(run_folder, "runs")
        os.makedirs(runs_folder, exist_ok=True)

        # Save individual run results
        for system_type, system_results in results.items():
            for run_idx, result in enumerate(system_results, 1):
                filename = f"{system_type}_{args.persona}_{args.scenario}_run{run_idx}.json"
                filepath = os.path.join(runs_folder, filename)
                with open(filepath, "w") as f:
                    json.dump(result.to_dict(), f, indent=2)

        # Save aggregated summary
        summary = format_multi_system_summary(results)
        with open(os.path.join(run_folder, "comparison_summary.json"), "w") as f:
            json.dump(summary, f, indent=2)

        # Save report
        with open(os.path.join(run_folder, "comparison_report.txt"), "w") as f:
            f.write(report)

        print(f"\nResults saved to: {run_folder}")
    else:
        print("Error: Please specify --scenario, --all-scenarios, or --full-matrix")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
