# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/metrics/formatters.py
"""Report formatting utilities for experiment results."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .experiment import ExperimentResult
    from .performance import AggregateMetrics


def format_metrics_report(result: "ExperimentResult") -> str:
    """Format experiment result as a readable report."""
    lines = [
        "=" * 70,
        "EXPERIMENT METRICS REPORT",
        "=" * 70,
        f"Experiment ID: {result.experiment_id}",
        f"Persona: {result.persona_id}",
        f"Scenario: {result.scenario_id}",
        f"Timestamp: {result.timestamp}",
        "",
        "-" * 50,
        "TASK COMPLETION METRICS",
        "-" * 50,
        f"  Goal Achieved: {'Yes' if result.task_metrics.goal_achieved else 'No'}",
        f"  Turns to Completion: {result.task_metrics.turns_to_completion or 'N/A'}",
        f"  Max Turns Allowed: {result.task_metrics.max_turns_allowed or 'No limit'}",
        f"  Task Efficiency: {result.task_metrics.task_efficiency:.2f}",
        f"  Goal Progress Score: {result.task_metrics.goal_progress_score}/5",
        f"  Termination Reason: {result.task_metrics.terminated_reason}",
        "",
        "-" * 50,
        "SYSTEM PERFORMANCE METRICS",
        "-" * 50,
        f"  Avg Latency: {result.system_metrics.avg_latency_ms:.0f}ms",
        f"  Min/Max Latency: {result.system_metrics.min_latency_ms:.0f}ms / {result.system_metrics.max_latency_ms:.0f}ms",
        f"  P95 Latency: {result.system_metrics.p95_latency_ms:.0f}ms",
        f"  Total Turns: {result.system_metrics.total_turns}",
        f"  Error Rate: {result.system_metrics.error_rate:.1%}",
        "",
        "  Agent Distribution:",
    ]

    for agent, count in result.system_metrics.agent_distribution.items():
        lines.append(f"    - {agent}: {count} turns")

    lines.extend([
        "",
        f"  Tools Used: {', '.join(result.system_metrics.tools_used) or 'None'}",
        f"  Total Tool Calls: {result.system_metrics.tool_call_count}",
        "",
        "-" * 50,
        "TOKEN USAGE & COST",
        "-" * 50,
        f"  Model: {result.system_metrics.model_used}",
        f"  Total Tokens: {result.system_metrics.total_tokens:,}",
        f"    - Input: {result.system_metrics.total_input_tokens:,}",
        f"    - Output: {result.system_metrics.total_output_tokens:,}",
        "",
        f"  HEMA System: {result.system_metrics.hema_input_tokens:,} in / {result.system_metrics.hema_output_tokens:,} out",
        f"  Simulated User: {result.system_metrics.simulated_user_input_tokens:,} in / {result.system_metrics.simulated_user_output_tokens:,} out",
        "",
        f"  Total Cost: ${result.system_metrics.total_cost_usd:.4f}",
        f"    - HEMA: ${result.system_metrics.hema_cost_usd:.4f}",
        f"    - Simulated User: ${result.system_metrics.simulated_user_cost_usd:.4f}",
        "",
        "-" * 50,
        "CONVERSATION QUALITY",
        "-" * 50,
    ])

    obj = result.quality_metrics.objective_metrics
    if obj:
        lines.extend([
            f"  Question Answer Rate: {obj.get('question_answer_rate', 0):.2f}",
            f"  Actionable Recommendations: {obj.get('actionable_recommendations_count', 0)}",
            f"  General Suggestions: {obj.get('general_suggestions_count', 0)}",
            f"  Jargon Explanation Rate: {obj.get('jargon_explanation_rate', 0):.2f}",
        ])
        if obj.get('num_factual_claims', 0) > 0:
            lines.extend([
                f"  Factual Accuracy Rate: {obj.get('factual_accuracy_rate', 0):.2f}",
                f"  Mean Factual Error: {obj.get('mean_error_pct', 0):.1f}%",
            ])

    lines.extend([
        "",
        "  Strengths:",
    ])
    for s in result.quality_metrics.strengths[:3]:
        lines.append(f"    + {s}")

    lines.extend([
        "",
        "  Weaknesses:",
    ])
    for w in result.quality_metrics.weaknesses[:3]:
        lines.append(f"    - {w}")

    # Device state verification (for Control Agent scenarios)
    if result.device_state_verification:
        v = result.device_state_verification
        status = "PASSED" if v.verification_passed else "FAILED"
        lines.extend([
            "",
            "-" * 50,
            "DEVICE STATE VERIFICATION",
            "-" * 50,
            f"  Status: {status}",
            f"  Checks: {v.passed_checks}/{v.total_checks} passed",
            "",
            "  Verification Details:",
        ])
        for device, props in v.check_details.items():
            for prop, details in props.items():
                check_status = "✓" if details["passed"] else "✗"
                # Handle _any_of checks which have different structure
                if details.get("check_type") == "any_of":
                    # Show which alternatives were checked
                    alt_count = len(details.get("alternatives", []))
                    passed_alts = sum(1 for a in details.get("alternatives", []) if a.get("passed"))
                    lines.append(
                        f"    {check_status} {device}.{prop}: "
                        f"{passed_alts}/{alt_count} alternatives matched"
                    )
                else:
                    # Regular check with before/after values
                    before = details.get('before', 'N/A')
                    after = details.get('after', 'N/A')
                    lines.append(
                        f"    {check_status} {device}.{prop}: "
                        f"{before} → {after} "
                        f"(expected: {details['check_type']})"
                    )

    # Action correctness evaluation (for Control Agent scenarios)
    if result.action_correctness:
        ac = result.action_correctness
        lines.extend([
            "",
            "-" * 50,
            "ACTION CORRECTNESS",
            "-" * 50,
            f"  Overall Score: {ac.correctness_score:.1f}%",
            f"  Actions Evaluated: {ac.actions_evaluated}",
            f"  Actions Correct: {ac.actions_correct}",
            f"  Actions Suboptimal: {ac.actions_suboptimal}",
        ])

        if ac.schedule_correctness is not None:
            lines.append(f"  Schedule Correctness (off-peak): {ac.schedule_correctness:.1f}%")
        if ac.temperature_correctness is not None:
            lines.append(f"  Temperature Correctness (efficient range): {ac.temperature_correctness:.1f}%")

        if ac.action_details:
            lines.append("")
            lines.append("  Action Details:")
            for detail in ac.action_details:
                icon = "✓" if detail["is_optimal"] else ("△" if detail["is_correct"] else "✗")
                lines.append(
                    f"    {icon} {detail['device']}.{detail['action']}: "
                    f"{detail['value']} - {detail['reason']}"
                )

    # Objective metrics (LLM-extracted semantic metrics)
    if result.quality_metrics.objective_metrics:
        m = result.quality_metrics.objective_metrics
        lines.extend([
            "",
            "-" * 50,
            "OBJECTIVE METRICS (LLM-Extracted)",
            "-" * 50,
            "",
            "  Tier 1: Basic Counts (Pure Counting)",
            f"    Total turns: {m.get('total_turns', 0)}",
            f"    System turns: {m.get('system_turns', 0)}",
            f"    User turns: {m.get('user_turns', 0)}",
            f"    User messages with questions: {m.get('user_messages_with_questions', 0)}",
            f"    Avg system response length: {m.get('avg_system_response_length', 0):.0f} chars",
            f"    Min/Max response length: {m.get('min_system_response_length', 0)} / {m.get('max_system_response_length', 0)} chars",
            "",
            "  Tier 2: Question/Answer Metrics",
            f"    User questions: {m.get('user_questions_count', 0)}",
            f"    Questions answered: {m.get('questions_answered_count', 0)}",
            f"    Questions unanswered: {m.get('questions_unanswered_count', 0)}",
            f"    Question answer rate: {m.get('question_answer_rate', 0):.2f}",
            "",
            "  Question Type Classification:",
            f"    Data-specific questions: {m.get('data_specific_questions_count', 0)}",
            f"    General knowledge questions: {m.get('general_knowledge_questions_count', 0)}",
            "",
            "  Data Usage Metrics:",
            f"    Data sources referenced: {m.get('data_sources_referenced_count', 0)}",
            "",
            "  Recommendation Metrics:",
            f"    Actionable recommendations: {m.get('actionable_recommendations_count', 0)}",
            f"    General suggestions: {m.get('general_suggestions_count', 0)}",
            f"    Actionable ratio: {m.get('actionable_ratio', 0):.2f}",
            "",
            "  Response Appropriateness Matrix:",
            "                           | Data Question | General Question |",
            "    -----------------------|---------------|------------------|",
        ])
        adb = m.get('appropriate_data_backed_count', 0)
        op = m.get('over_personalized_count', 0)
        up = m.get('under_personalized_count', 0)
        ag = m.get('appropriate_general_count', 0)
        lines.append(f"    Data-Backed Response   |      {adb:2d} ✅    |       {op:2d} ⚠️       |")
        lines.append(f"    General Response       |      {up:2d} ❌    |       {ag:2d} ✅       |")
        lines.extend([
            "",
            f"    Appropriate response rate: {m.get('appropriate_response_rate', 0):.2f}",
            "",
            "  Communication Quality:",
            f"    Technical terms explained: {m.get('technical_terms_explained_count', 0)}",
            f"    Unexplained jargon: {m.get('unexplained_jargon_count', 0)}",
            f"    Jargon explanation rate: {m.get('jargon_explanation_rate', 0):.2f}",
        ])
        # Show unexplained jargon items if any
        jargon = m.get('unexplained_jargon', [])
        if jargon:
            lines.append("    Unexplained terms: " + ", ".join(jargon[:5]))

        # Tier 3: Factual Accuracy (from claim verification)
        num_claims = m.get('num_factual_claims', 0)
        if num_claims > 0:
            lines.extend([
                "",
                "  Factual Accuracy (Tier 3 — Claim Verification):",
                f"    Total claims verified: {num_claims}",
                f"    Accurate claims (<=5% error): {m.get('num_accurate_claims', 0)}",
                f"    Factual accuracy rate: {m.get('factual_accuracy_rate', 0):.2f}",
                f"    Mean error: {m.get('mean_error_pct', 0):.1f}%",
                f"    Max error: {m.get('max_error_pct', 0):.1f}%",
            ])
            # Show sample claims for auditability
            claims = m.get('factual_claims', [])
            if claims:
                lines.append("")
                lines.append("    Sample Claims:")
                for c in claims[:5]:
                    icon = "✓" if c.get('error_pct', 100) <= 5 else "✗"
                    lines.append(
                        f"      {icon} {c.get('claim_text', '')[:60]}: "
                        f"claimed={c.get('claimed_value')}, actual={c.get('ground_truth_value')}, "
                        f"error={c.get('error_pct', 0):.1f}%"
                    )

        # Show sample extracted items for auditability
        lines.append("")
        lines.append("  Sample Extracted Items:")
        user_qs = m.get('user_questions_list', [])
        if user_qs:
            lines.append(f"    User questions: {user_qs[0][:50]}{'...' if len(user_qs[0]) > 50 else ''}" +
                        (f" (+{len(user_qs)-1} more)" if len(user_qs) > 1 else ""))
        recs = m.get('actionable_recommendations', [])
        if recs:
            lines.append(f"    Recommendation: {recs[0][:50]}{'...' if len(recs[0]) > 50 else ''}" +
                        (f" (+{len(recs)-1} more)" if len(recs) > 1 else ""))

    lines.extend([
        "",
        "=" * 70,
    ])

    return "\n".join(lines)


def format_aggregate_report(agg: "AggregateMetrics") -> str:
    """Format aggregate metrics as a readable report."""
    lines = [
        "=" * 70,
        "AGGREGATE METRICS REPORT",
        "=" * 70,
        f"Persona: {agg.persona_id}",
        f"Scenario: {agg.scenario_id}",
        f"Number of Runs: {agg.num_runs}",
        "",
        "-" * 50,
        "TASK COMPLETION (Aggregated)",
        "-" * 50,
        f"  Goal Achievement Rate: {agg.goal_achievement_rate:.1%}",
        f"  Avg Turns to Completion: {agg.avg_turns_to_completion:.1f}",
        f"  Avg Task Efficiency: {agg.avg_task_efficiency:.2f}",
        "",
        "-" * 50,
        "SYSTEM PERFORMANCE (Aggregated)",
        "-" * 50,
        f"  Avg Latency: {agg.avg_latency_ms:.0f}ms",
        f"  Avg Error Rate: {agg.avg_error_rate:.1%}",
        "",
        "  Agent Usage Distribution:",
    ]

    for agent, pct in sorted(agg.agent_usage_distribution.items(), key=lambda x: -x[1]):
        lines.append(f"    - {agent}: {pct:.1%}")

    lines.extend([
        "",
        "-" * 50,
        "QUALITY METRICS (Aggregated)",
        "-" * 50,
        f"  Goal Achievement Rate: {agg.goal_achievement_rate:.1%}",
    ])

    lines.extend([
        "",
        "=" * 70,
    ])

    return "\n".join(lines)
