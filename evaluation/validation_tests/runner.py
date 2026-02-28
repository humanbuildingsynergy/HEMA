# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/validation_tests/runner.py
"""
Validation test runner for the evaluation framework.

Runs goal-oriented multi-turn conversations and validates that the
simulated user, HEMA, and evaluator interact correctly.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any

from ..config import get_persona, get_scenario
from ..runners.conversation import run_full_experiment
from ..evaluator import ConversationEvaluator
from ..metrics import ExperimentResult
from ..runners.simulated_user import OpeningMode

from .scenarios import ValidationScenario, VALIDATION_SCENARIOS, get_validation_scenario
from .validators import ValidationReport, run_all_validations


@dataclass
class ValidationTestResult:
    """Result of a single validation test."""

    scenario_id: str
    scenario_name: str
    persona_id: str
    scenario_config_id: str

    # Validation results
    validation_report: ValidationReport

    # Experiment data
    experiment_result: Optional[ExperimentResult]
    total_turns: int
    goal_achieved: bool
    llm_judge_score: float
    avg_latency_ms: float

    # Timing
    duration_seconds: float

    # Error if test failed to run
    error: Optional[str] = None

    @property
    def passed(self) -> bool:
        """Check if test passed."""
        return self.error is None and self.validation_report.passed

    @property
    def status(self) -> str:
        """Get test status string."""
        if self.error:
            return "ERROR"
        return self.validation_report.summary()


@dataclass
class ValidationTestSuite:
    """Collection of validation test results."""

    results: List[ValidationTestResult] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @property
    def total_tests(self) -> int:
        return len(self.results)

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.status == "PASS")

    @property
    def warn_count(self) -> int:
        return sum(1 for r in self.results if r.status == "WARN")

    @property
    def fail_count(self) -> int:
        return sum(1 for r in self.results if r.status in ("FAIL", "ERROR"))

    @property
    def all_passed(self) -> bool:
        return self.fail_count == 0

    def add(self, result: ValidationTestResult) -> None:
        self.results.append(result)


def run_single_validation_test(
    validation_scenario: ValidationScenario,
    verbose: bool = True,
) -> ValidationTestResult:
    """
    Run a single validation test.

    Args:
        validation_scenario: The validation scenario to run
        verbose: Whether to print progress

    Returns:
        ValidationTestResult with validation report
    """
    import time

    start_time = time.time()

    # Get persona and scenario from config
    persona = get_persona(validation_scenario.persona_id)
    scenario = get_scenario(validation_scenario.scenario_id)

    if not persona:
        return ValidationTestResult(
            scenario_id=validation_scenario.id,
            scenario_name=validation_scenario.name,
            persona_id=validation_scenario.persona_id,
            scenario_config_id=validation_scenario.scenario_id,
            validation_report=ValidationReport(),
            experiment_result=None,
            total_turns=0,
            goal_achieved=False,
            llm_judge_score=0.0,
            avg_latency_ms=0.0,
            duration_seconds=time.time() - start_time,
            error=f"Persona '{validation_scenario.persona_id}' not found",
        )

    if not scenario:
        return ValidationTestResult(
            scenario_id=validation_scenario.id,
            scenario_name=validation_scenario.name,
            persona_id=validation_scenario.persona_id,
            scenario_config_id=validation_scenario.scenario_id,
            validation_report=ValidationReport(),
            experiment_result=None,
            total_turns=0,
            goal_achieved=False,
            llm_judge_score=0.0,
            avg_latency_ms=0.0,
            duration_seconds=time.time() - start_time,
            error=f"Scenario '{validation_scenario.scenario_id}' not found",
        )

    try:
        # Run the full experiment with a fixed max_turns limit for validation tests
        # Validation tests always use max_turns=10 regardless of scenario settings
        # Validation tests always use CONTROLLED mode for reproducibility
        VALIDATION_MAX_TURNS = 10
        evaluator = ConversationEvaluator()
        experiment_result = run_full_experiment(
            persona=persona,
            scenario=scenario,
            experiment_id=f"validate_{validation_scenario.id}",
            evaluator=evaluator,
            verbose=verbose,
            max_turns=VALIDATION_MAX_TURNS,
            opening_mode=OpeningMode.CONTROLLED,
        )

        # Run validations
        validation_report = run_all_validations(
            result=experiment_result,
            persona=persona,
            expect_goal_completion=validation_scenario.expect_goal_completion,
            max_acceptable_errors=validation_scenario.max_acceptable_errors,
        )

        return ValidationTestResult(
            scenario_id=validation_scenario.id,
            scenario_name=validation_scenario.name,
            persona_id=validation_scenario.persona_id,
            scenario_config_id=validation_scenario.scenario_id,
            validation_report=validation_report,
            experiment_result=experiment_result,
            total_turns=experiment_result.system_metrics.total_turns,
            goal_achieved=experiment_result.task_metrics.goal_achieved,
            llm_judge_score=experiment_result.quality_metrics.llm_judge_score,
            avg_latency_ms=experiment_result.system_metrics.avg_latency_ms,
            duration_seconds=time.time() - start_time,
        )

    except Exception as e:
        return ValidationTestResult(
            scenario_id=validation_scenario.id,
            scenario_name=validation_scenario.name,
            persona_id=validation_scenario.persona_id,
            scenario_config_id=validation_scenario.scenario_id,
            validation_report=ValidationReport(),
            experiment_result=None,
            total_turns=0,
            goal_achieved=False,
            llm_judge_score=0.0,
            avg_latency_ms=0.0,
            duration_seconds=time.time() - start_time,
            error=str(e),
        )


def run_validation_tests(
    scenario_ids: Optional[List[str]] = None,
    verbose: bool = True,
) -> ValidationTestSuite:
    """
    Run validation tests.

    Args:
        scenario_ids: Specific scenarios to run (runs all if None)
        verbose: Whether to print progress

    Returns:
        ValidationTestSuite with all results
    """
    suite = ValidationTestSuite(start_time=datetime.now())

    # Determine which scenarios to run
    if scenario_ids:
        scenarios = [get_validation_scenario(sid) for sid in scenario_ids]
        scenarios = [s for s in scenarios if s is not None]
    else:
        scenarios = VALIDATION_SCENARIOS

    total = len(scenarios)

    for i, scenario in enumerate(scenarios, 1):
        if verbose:
            print(f"\n{'='*60}")
            print(f"VALIDATION TEST [{i}/{total}]: {scenario.name}")
            print(f"{'='*60}")
            print(f"Persona: {scenario.persona_id}")
            print(f"Scenario: {scenario.scenario_id}")
            print(f"Focus: {', '.join(scenario.validation_focus)}")
            print("-" * 60)

        result = run_single_validation_test(scenario, verbose=verbose)
        suite.add(result)

        if verbose:
            _print_test_result(result)

    suite.end_time = datetime.now()

    if verbose:
        _print_suite_summary(suite)

    return suite


def _print_test_result(result: ValidationTestResult) -> None:
    """Print a single test result."""
    print(f"\n{'-'*40}")
    print(f"RESULT: {result.status}")
    print(f"{'-'*40}")

    if result.error:
        print(f"Error: {result.error}")
        return

    print(f"Turns: {result.total_turns}")
    print(f"Goal Achieved: {'Yes' if result.goal_achieved else 'No'}")
    print(f"Quality Score: {result.llm_judge_score:.2f}/5.0")
    print(f"Avg Latency: {result.avg_latency_ms:.0f}ms")
    print(f"Duration: {result.duration_seconds:.1f}s")

    # Print validation details
    print(f"\nValidation Results:")
    for category in ["technical", "reasoning", "semantic"]:
        category_results = [
            r for r in result.validation_report.results
            if r.category == category
        ]
        passed = sum(1 for r in category_results if r.passed)
        total = len(category_results)

        failed = [r for r in category_results if not r.passed]
        status = "PASS" if not failed else ("WARN" if all(f.severity == "warning" for f in failed) else "FAIL")

        print(f"  {category.capitalize()}: {status} ({passed}/{total} checks)")

        # Show failures/warnings
        for f in failed:
            prefix = "!" if f.severity == "error" else "?"
            print(f"    {prefix} {f.check_name}: {f.message}")


def _print_suite_summary(suite: ValidationTestSuite) -> None:
    """Print summary of all validation tests."""
    print(f"\n{'='*60}")
    print("VALIDATION TEST SUMMARY")
    print(f"{'='*60}")

    duration = (suite.end_time - suite.start_time).total_seconds() if suite.end_time and suite.start_time else 0

    print(f"\nTotal Tests: {suite.total_tests}")
    print(f"  Passed: {suite.passed_count}")
    print(f"  Warnings: {suite.warn_count}")
    print(f"  Failed: {suite.fail_count}")
    print(f"\nTotal Duration: {duration:.1f}s")

    if suite.all_passed:
        print(f"\nOVERALL: PASS")
        print("Framework is ready for full evaluation.")
    else:
        print(f"\nOVERALL: {'WARN' if suite.fail_count == 0 else 'FAIL'}")
        if suite.fail_count > 0:
            print("Review failed tests before running full evaluation.")
        else:
            print("Review warnings - framework may work but has minor issues.")

    # List individual results
    print(f"\n{'-'*40}")
    print("Individual Results:")
    print(f"{'-'*40}")
    for result in suite.results:
        status_icon = {
            "PASS": "[OK]",
            "WARN": "[??]",
            "FAIL": "[XX]",
            "ERROR": "[!!]",
        }.get(result.status, "[??]")
        print(f"  {status_icon} {result.scenario_id}: {result.status}")
        if result.error:
            print(f"       Error: {result.error[:50]}...")

    print(f"\n{'='*60}")


def format_validation_report(suite: ValidationTestSuite, include_transcripts: bool = True) -> str:
    """Format validation test suite as a detailed report string.

    Args:
        suite: The validation test suite to format
        include_transcripts: Whether to include full conversation transcripts
    """
    lines = [
        "=" * 70,
        "FRAMEWORK VALIDATION TEST REPORT",
        "=" * 70,
        f"Start Time: {suite.start_time.isoformat() if suite.start_time else 'N/A'}",
        f"End Time: {suite.end_time.isoformat() if suite.end_time else 'N/A'}",
        "",
        "-" * 50,
        "SUMMARY",
        "-" * 50,
        f"Total Tests: {suite.total_tests}",
        f"Passed: {suite.passed_count}",
        f"Warnings: {suite.warn_count}",
        f"Failed: {suite.fail_count}",
        f"Overall: {'PASS' if suite.all_passed else ('WARN' if suite.fail_count == 0 else 'FAIL')}",
        "",
    ]

    for result in suite.results:
        lines.extend([
            "=" * 70,
            f"TEST: {result.scenario_name}",
            "=" * 70,
            f"ID: {result.scenario_id}",
            f"Persona: {result.persona_id}",
            f"Scenario: {result.scenario_config_id}",
            f"Status: {result.status}",
            "",
        ])

        if result.error:
            lines.append(f"Error: {result.error}")
        else:
            exp = result.experiment_result

            # Task Completion Metrics
            lines.extend([
                "-" * 50,
                "TASK COMPLETION METRICS",
                "-" * 50,
                f"  Goal Achieved: {'Yes' if result.goal_achieved else 'No'}",
                f"  Turns to Completion: {exp.task_metrics.turns_to_completion or 'N/A'}",
                f"  Max Turns Allowed: {exp.task_metrics.max_turns_allowed or 'No limit'}",
                f"  Task Efficiency: {exp.task_metrics.task_efficiency:.2f}",
                f"  Termination Reason: {exp.task_metrics.terminated_reason}",
                "",
            ])

            # System Performance Metrics
            lines.extend([
                "-" * 50,
                "SYSTEM PERFORMANCE METRICS",
                "-" * 50,
                f"  Total Turns: {exp.system_metrics.total_turns}",
                f"  Avg Latency: {exp.system_metrics.avg_latency_ms:.0f}ms",
                f"  Min Latency: {exp.system_metrics.min_latency_ms:.0f}ms",
                f"  Max Latency: {exp.system_metrics.max_latency_ms:.0f}ms",
                f"  P95 Latency: {exp.system_metrics.p95_latency_ms:.0f}ms",
                f"  Error Count: {exp.system_metrics.error_count}",
                f"  Error Rate: {exp.system_metrics.error_rate:.1%}",
                "",
                "  Agent Distribution:",
            ])
            for agent, count in exp.system_metrics.agent_distribution.items():
                lines.append(f"    - {agent}: {count} turns")

            lines.extend([
                "",
                f"  Tools Used: {', '.join(exp.system_metrics.tools_used) or 'None'}",
                f"  Total Tool Calls: {exp.system_metrics.tool_call_count}",
                "",
            ])

            # Quality Metrics
            lines.extend([
                "-" * 50,
                "CONVERSATION QUALITY METRICS",
                "-" * 50,
                f"  LLM Judge Score: {exp.quality_metrics.llm_judge_score:.2f}/5.0",
                "",
                "  Dimension Scores:",
            ])
            for dim, score in exp.quality_metrics.dimension_scores.items():
                lines.append(f"    - {dim}: {score}/5")

            lines.extend([
                "",
                "  Strengths:",
            ])
            for s in exp.quality_metrics.strengths[:5]:
                lines.append(f"    + {s}")

            lines.extend([
                "",
                "  Weaknesses:",
            ])
            for w in exp.quality_metrics.weaknesses[:5]:
                lines.append(f"    - {w}")

            lines.extend([
                "",
                "  Improvement Suggestions:",
            ])
            for suggestion in exp.quality_metrics.improvement_suggestions[:5]:
                lines.append(f"    * {suggestion}")

            # Validation Results
            lines.extend([
                "",
                "-" * 50,
                "VALIDATION RESULTS",
                "-" * 50,
            ])
            for v in result.validation_report.results:
                status = "PASS" if v.passed else v.severity.upper()
                lines.append(f"  [{status}] {v.category}/{v.check_name}: {v.message}")

            # Full Conversation Transcript
            if include_transcripts and exp.conversation_transcript:
                lines.extend([
                    "",
                    "-" * 50,
                    "FULL CONVERSATION TRANSCRIPT",
                    "-" * 50,
                    "",
                    exp.conversation_transcript,
                ])

        lines.extend(["", ""])

    lines.extend([
        "=" * 70,
        "END OF REPORT",
        "=" * 70,
    ])

    return "\n".join(lines)


def validation_result_to_dict(result: ValidationTestResult) -> Dict[str, Any]:
    """Convert a ValidationTestResult to a dictionary for JSON serialization."""
    data = {
        "scenario_id": result.scenario_id,
        "scenario_name": result.scenario_name,
        "persona_id": result.persona_id,
        "scenario_config_id": result.scenario_config_id,
        "status": result.status,
        "total_turns": result.total_turns,
        "goal_achieved": result.goal_achieved,
        "llm_judge_score": result.llm_judge_score,
        "avg_latency_ms": result.avg_latency_ms,
        "duration_seconds": result.duration_seconds,
        "error": result.error,
        "validation_results": [
            {
                "category": v.category,
                "check_name": v.check_name,
                "passed": v.passed,
                "message": v.message,
                "severity": v.severity,
                "details": v.details,
            }
            for v in result.validation_report.results
        ],
    }

    # Include full experiment result if available
    if result.experiment_result:
        data["experiment"] = result.experiment_result.to_dict()

    return data


def validation_suite_to_dict(suite: ValidationTestSuite) -> Dict[str, Any]:
    """Convert a ValidationTestSuite to a dictionary for JSON serialization."""
    return {
        "start_time": suite.start_time.isoformat() if suite.start_time else None,
        "end_time": suite.end_time.isoformat() if suite.end_time else None,
        "total_tests": suite.total_tests,
        "passed_count": suite.passed_count,
        "warn_count": suite.warn_count,
        "fail_count": suite.fail_count,
        "all_passed": suite.all_passed,
        "results": [validation_result_to_dict(r) for r in suite.results],
    }
