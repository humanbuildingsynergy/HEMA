#!/usr/bin/env python3
# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/comparison/formatters.py
"""Report formatting for comparison results.

Generates human-readable comparison reports and summaries.
"""

from typing import Dict, List, Any

from evaluation.metrics import ExperimentResult
from .runners import format_multi_system_summary


def format_comparison_summary(
    hema_result: ExperimentResult,
    vanilla_result: ExperimentResult,
) -> Dict:
    """Generate comparison summary as dictionary (legacy 2-system format)."""
    return {
        "persona": hema_result.persona_id,
        "scenario": hema_result.scenario_id,
        "hema": {
            "goal_achieved": hema_result.task_metrics.goal_achieved,
            "turns": hema_result.system_metrics.total_turns,
            "avg_latency_ms": hema_result.system_metrics.avg_latency_ms,
            "total_cost_usd": hema_result.system_metrics.total_cost_usd,
            "objective_metrics": hema_result.quality_metrics.objective_metrics,
        },
        "vanilla": {
            "goal_achieved": vanilla_result.task_metrics.goal_achieved,
            "turns": vanilla_result.system_metrics.total_turns,
            "avg_latency_ms": vanilla_result.system_metrics.avg_latency_ms,
            "total_cost_usd": vanilla_result.system_metrics.total_cost_usd,
            "objective_metrics": vanilla_result.quality_metrics.objective_metrics,
        },
        "delta": {
            "turns_diff": (
                hema_result.system_metrics.total_turns -
                vanilla_result.system_metrics.total_turns
            ),
            "latency_ratio": round(
                hema_result.system_metrics.avg_latency_ms /
                vanilla_result.system_metrics.avg_latency_ms
                if vanilla_result.system_metrics.avg_latency_ms > 0 else 0, 2
            ),
            "cost_ratio": round(
                hema_result.system_metrics.total_cost_usd /
                vanilla_result.system_metrics.total_cost_usd
                if vanilla_result.system_metrics.total_cost_usd > 0 else 0, 2
            ),
        },
    }


def format_comparison_report(
    hema_result: ExperimentResult,
    vanilla_result: ExperimentResult,
) -> str:
    """Generate side-by-side comparison report."""
    summary = format_comparison_summary(hema_result, vanilla_result)

    lines = [
        "=" * 70,
        "COMPARATIVE EVALUATION REPORT",
        "=" * 70,
        f"Persona: {summary['persona']}",
        f"Scenario: {summary['scenario']}",
        "",
        "-" * 50,
        "SIDE-BY-SIDE COMPARISON",
        "-" * 50,
        "",
        f"{'Metric':<30} {'HEMA':>15} {'Vanilla':>15} {'Delta':>10}",
        "-" * 70,
        f"{'Goal Achieved':<30} {'Yes' if summary['hema']['goal_achieved'] else 'No':>15} {'Yes' if summary['vanilla']['goal_achieved'] else 'No':>15} {'':>10}",
        f"{'Total Turns':<30} {summary['hema']['turns']:>15} {summary['vanilla']['turns']:>15} {summary['delta']['turns_diff']:>+10}",
        f"{'Avg Latency (ms)':<30} {summary['hema']['avg_latency_ms']:>15.0f} {summary['vanilla']['avg_latency_ms']:>15.0f} {summary['delta']['latency_ratio']:>10.1f}x",
        f"{'Total Cost (USD)':<30} ${summary['hema']['total_cost_usd']:>14.4f} ${summary['vanilla']['total_cost_usd']:>14.4f} {summary['delta']['cost_ratio']:>10.1f}x",
        "",
        "-" * 50,
        "HEMA STRENGTHS",
        "-" * 50,
    ]
    for s in hema_result.quality_metrics.strengths[:3]:
        lines.append(f"  + {s}")

    lines.extend([
        "",
        "-" * 50,
        "VANILLA LLM STRENGTHS",
        "-" * 50,
    ])
    for s in vanilla_result.quality_metrics.strengths[:3]:
        lines.append(f"  + {s}")

    lines.extend([
        "",
        "=" * 70,
    ])

    return "\n".join(lines)


def format_multi_system_report(
    results: Dict[str, List[ExperimentResult]],
    num_runs: int = 1,
) -> str:
    """Generate comparison report for multiple systems with aggregated stats.

    Args:
        results: Dict mapping system_type -> list of ExperimentResults
        num_runs: Number of runs per system

    Returns:
        Formatted text report
    """
    summary = format_multi_system_summary(results)
    systems = list(results.keys())

    lines = [
        "=" * 90,
        "MULTI-SYSTEM COMPARATIVE EVALUATION REPORT",
        "=" * 90,
        f"Persona: {summary['persona_id']}",
        f"Scenario: {summary['scenario_id']}",
        f"Systems: {len(systems)}",
        f"Runs per system: {num_runs}",
        "",
        "-" * 90,
        "AGGREGATED SCORES (mean ± std)",
        "-" * 90,
        "",
    ]

    # Build header row
    header = f"{'Metric':<25}"
    for system in systems:
        header += f" {system:>12}"
    lines.append(header)
    lines.append("-" * 90)

    # Goal success rate row
    row = f"{'Goal Success Rate':<25}"
    for system in systems:
        if system in summary["systems"]:
            goal = summary["systems"][system]["goal_achieved"]
            row += f" {goal['success_rate']*100:>11.0f}%"
        else:
            row += f" {'N/A':>12}"
    lines.append(row)

    # Latency row
    row = f"{'Avg Latency (ms)':<25}"
    for system in systems:
        if system in summary["systems"]:
            lat = summary["systems"][system]["latency_ms"]
            row += f" {lat['mean']:>12.0f}"
        else:
            row += f" {'N/A':>12}"
    lines.append(row)

    # Cost row
    row = f"{'Total Cost (USD)':<25}"
    for system in systems:
        if system in summary["systems"]:
            cost = summary["systems"][system]["total_cost_usd"]
            row += f" ${cost['mean']:>11.4f}"
        else:
            row += f" {'N/A':>12}"
    lines.append(row)

    # Turns row
    row = f"{'Total Turns':<25}"
    for system in systems:
        if system in summary["systems"]:
            turns = summary["systems"][system]["total_turns"]
            row += f" {turns['mean']:>12.1f}"
        else:
            row += f" {'N/A':>12}"
    lines.append(row)

    # Tool invocations row
    row = f"{'Tool Invocations':<25}"
    for system in systems:
        if system in summary["systems"]:
            tools = summary["systems"][system].get("tool_call_count", {"mean": 0})
            row += f" {tools['mean']:>12.1f}"
        else:
            row += f" {'N/A':>12}"
    lines.append(row)

    # System Efficiency section
    lines.extend([
        "",
        "-" * 90,
        "SYSTEM EFFICIENCY METRICS",
        "-" * 90,
    ])

    # Total tokens row
    row = f"{'Total Tokens':<25}"
    for system in systems:
        if system in summary["systems"]:
            tokens = summary["systems"][system].get("total_tokens", {"mean": 0})
            row += f" {tokens['mean']:>12,.0f}"
        else:
            row += f" {'N/A':>12}"
    lines.append(row)

    # Error rate row
    row = f"{'Error Rate':<25}"
    for system in systems:
        if system in summary["systems"]:
            err = summary["systems"][system].get("error_rate", {"mean": 0})
            row += f" {err['mean']*100:>11.1f}%"
        else:
            row += f" {'N/A':>12}"
    lines.append(row)

    # P95 Latency row
    row = f"{'P95 Latency (ms)':<25}"
    for system in systems:
        if system in summary["systems"]:
            p95 = summary["systems"][system].get("p95_latency_ms", {"mean": 0})
            row += f" {p95['mean']:>12,.0f}"
        else:
            row += f" {'N/A':>12}"
    lines.append(row)

    # Objective Quality Metrics section
    lines.extend([
        "",
        "-" * 90,
        "OBJECTIVE QUALITY METRICS (mean)",
        "-" * 90,
    ])

    # Key objective metrics to display
    key_objective_metrics = [
        ("question_answer_rate", "Question Answer Rate", "pct"),
        ("actionable_recommendations_count", "Actionable Recs", "count"),
        ("general_suggestions_count", "General Suggestions", "count"),
        ("appropriate_response_rate", "Appropriate Response %", "pct"),
        ("jargon_explanation_rate", "Jargon Explanation Rate", "pct"),
        ("factual_accuracy_rate", "Factual Accuracy Rate", "pct"),
        ("mean_error_pct", "Mean Factual Error %", "float"),
        ("num_factual_claims", "Factual Claims Verified", "count"),
    ]

    for metric_key, metric_label, fmt in key_objective_metrics:
        row = f"  {metric_label:<25}"
        for system in systems:
            if system in summary["systems"]:
                obj_metrics = summary["systems"][system].get("objective_metrics", {})
                metric_data = obj_metrics.get(metric_key)
                if metric_data:
                    if fmt == "pct":
                        row += f" {metric_data['mean']*100:>11.1f}%"
                    elif fmt == "count":
                        row += f" {metric_data['mean']:>12.1f}"
                    else:
                        row += f" {metric_data['mean']:>12.2f}"
                else:
                    row += f" {'N/A':>12}"
            else:
                row += f" {'N/A':>12}"
        lines.append(row)

    lines.extend([
        "",
        "=" * 90,
    ])

    return "\n".join(lines)
