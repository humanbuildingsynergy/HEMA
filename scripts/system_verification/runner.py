# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# scripts/test_scenarios/runner.py
"""Test execution functions for running test scenarios."""
import time
from typing import List

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from agents.graph import HEMAGraphRunner
from .models import TestScenario, TestResult
from .comparison import compute_response_accuracy


def run_single_test(
    runner: HEMAGraphRunner,
    scenario: TestScenario,
    session_id: str,
) -> TestResult:
    """Run a single test scenario.

    Pass/Fail Logic (in order of priority):
    1. Exceptions always fail
    2. Tie/clarification (needs_clarification=True) is treated as VALID behavior
       - The system correctly identified ambiguity and asked for user input
    3. Semantic comparison via LLM takes priority over keyword matching:
       - If response_accuracy is "match" or "partial", the test passes
         even if expected_contains keywords are missing
    4. If no ground truth (expected_response), fall back to keyword/agent checks
    5. Only "mismatch" on semantic comparison causes failure
    """
    start_time = time.time()

    try:
        result = runner.invoke(scenario.input_message, session_id=session_id)
        latency_ms = (time.time() - start_time) * 1000

        response = result.get("final_response", "")
        actual_agent = result.get("target_agent")
        vote_distribution = result.get("vote_distribution")
        needs_clarification = result.get("needs_clarification", False)

        # Track issues found (for reporting) vs failures (for pass/fail)
        failure_reasons = []
        warnings = []  # Issues that don't cause failure when semantic match passes
        passed = True

        # Check if system requested clarification (tie scenario)
        # This is VALID behavior - the system correctly identified ambiguity
        if needs_clarification:
            return TestResult(
                scenario_id=scenario.id,
                scenario_name=scenario.name,
                category=scenario.category,
                input_message=scenario.input_message,
                passed=True,  # Clarification is valid behavior
                response=response,
                actual_agent=actual_agent,
                vote_distribution=vote_distribution,
                latency_ms=latency_ms,
                failure_reasons=[],  # No failures
                expected_response=scenario.expected_response,
                response_accuracy="clarification_requested",  # Special status
            )

        # Compute response accuracy against ground truth FIRST
        response_accuracy = compute_response_accuracy(response, scenario.expected_response)

        # If semantic comparison shows "match" or "partial", the test passes
        # regardless of keyword mismatches
        semantic_pass = response_accuracy in ("match", "partial")

        # Check expected agent (warning if semantic passes, failure otherwise)
        if scenario.expected_agent and actual_agent != scenario.expected_agent:
            msg = f"Expected agent '{scenario.expected_agent}', got '{actual_agent}'"
            if semantic_pass:
                warnings.append(msg)
            else:
                passed = False
                failure_reasons.append(msg)

        # Check expected content (warning if semantic passes, failure otherwise)
        if scenario.expected_contains:
            for expected in scenario.expected_contains:
                if expected.lower() not in response.lower():
                    msg = f"Response missing expected content: '{expected}'"
                    if semantic_pass:
                        warnings.append(msg)
                    else:
                        passed = False
                        failure_reasons.append(msg)

        # Check content that should not be present (always a failure - errors/exceptions)
        if scenario.expected_not_contains:
            for not_expected in scenario.expected_not_contains:
                if not_expected.lower() in response.lower():
                    passed = False
                    failure_reasons.append(f"Response contains unexpected content: '{not_expected}'")

        # If ground truth exists and accuracy is "mismatch", fail
        if response_accuracy == "mismatch":
            passed = False
            failure_reasons.append(
                f"Response accuracy: mismatch with ground truth"
            )

        # Add warnings to failure_reasons with prefix for reporting
        for warning in warnings:
            failure_reasons.append(f"[WARNING] {warning}")

        return TestResult(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            category=scenario.category,
            input_message=scenario.input_message,
            passed=passed,
            response=response,
            actual_agent=actual_agent,
            vote_distribution=vote_distribution,
            latency_ms=latency_ms,
            failure_reasons=failure_reasons,
            expected_response=scenario.expected_response,
            response_accuracy=response_accuracy,
        )

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return TestResult(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            category=scenario.category,
            input_message=scenario.input_message,
            passed=False,
            response=f"ERROR: {str(e)}",
            actual_agent=None,
            vote_distribution=None,
            latency_ms=latency_ms,
            failure_reasons=[f"Exception: {str(e)}"],
            expected_response=scenario.expected_response,
            response_accuracy=None,
        )


def run_tests(
    scenarios: List[TestScenario],
    verbose: bool = False,
) -> List[TestResult]:
    """Run all test scenarios."""
    print("\n" + "=" * 70)
    print("HEMA SYSTEM TEST RUNNER")
    print("=" * 70)
    print(f"Running {len(scenarios)} test scenarios...")
    print("-" * 70 + "\n")

    # Create runner (new instance for clean state)
    runner = HEMAGraphRunner(use_persistence=False)

    results = []
    for i, scenario in enumerate(scenarios):
        # Use unique session ID per test
        session_id = f"test_{scenario.id}_{int(time.time())}"

        print(f"[{i+1}/{len(scenarios)}] {scenario.name}...", end=" ", flush=True)

        result = run_single_test(runner, scenario, session_id)
        results.append(result)

        if result.passed:
            print(f"PASS ({result.latency_ms:.0f}ms)")
        else:
            print(f"FAIL ({result.latency_ms:.0f}ms)")
            if verbose:
                for reason in result.failure_reasons:
                    print(f"       - {reason}")

        if verbose:
            print(f"       Agent: {result.actual_agent}")
            print(f"       Votes: {result.vote_distribution}")
            if len(result.response) > 100:
                print(f"       Response: {result.response[:100]}...")
            else:
                print(f"       Response: {result.response}")
            print()

    return results
