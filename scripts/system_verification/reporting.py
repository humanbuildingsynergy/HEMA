# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# scripts/test_scenarios/reporting.py
"""Summary and reporting functions for test scenarios."""
import json
import os
from datetime import datetime
from typing import List

from .models import TestResult


def print_summary(results: List[TestResult]) -> None:
    """Print test summary."""
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    # Count clarification requests (these are passing but worth noting)
    clarification_count = sum(
        1 for r in results
        if r.response_accuracy == "clarification_requested"
    )

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Total: {total} | Passed: {passed} | Failed: {failed}")
    print(f"Pass Rate: {100 * passed / total:.1f}%")

    if clarification_count > 0:
        print(f"  (includes {clarification_count} clarification requests - valid behavior)")

    # Ground truth accuracy stats
    with_ground_truth = [
        r for r in results
        if r.response_accuracy is not None and r.response_accuracy != "clarification_requested"
    ]
    if with_ground_truth:
        match_count = sum(1 for r in with_ground_truth if r.response_accuracy == "match")
        partial_count = sum(1 for r in with_ground_truth if r.response_accuracy == "partial")
        mismatch_count = sum(1 for r in with_ground_truth if r.response_accuracy == "mismatch")
        print(f"\nGround Truth Accuracy ({len(with_ground_truth)} scenarios with expected responses):")
        print(f"  Match: {match_count} | Partial: {partial_count} | Mismatch: {mismatch_count}")
        if len(with_ground_truth) > 0:
            accuracy_pct = 100 * (match_count + partial_count) / len(with_ground_truth)
            print(f"  Acceptable (match+partial): {accuracy_pct:.1f}%")

    # Group by category
    categories = {}
    for r in results:
        if r.category not in categories:
            categories[r.category] = {"passed": 0, "failed": 0, "clarification": 0}
        if r.passed:
            categories[r.category]["passed"] += 1
            if r.response_accuracy == "clarification_requested":
                categories[r.category]["clarification"] += 1
        else:
            categories[r.category]["failed"] += 1

    print("\nBy Category:")
    for cat, counts in sorted(categories.items()):
        cat_total = counts["passed"] + counts["failed"]
        clarif = counts["clarification"]
        if clarif > 0:
            print(f"  {cat}: {counts['passed']}/{cat_total} passed ({clarif} via clarification)")
        else:
            print(f"  {cat}: {counts['passed']}/{cat_total} passed")

    # List failures
    failures = [r for r in results if not r.passed]
    if failures:
        print("\nFailed Tests:")
        for f in failures:
            print(f"  - [{f.scenario_id}] {f.scenario_name}")
            for reason in f.failure_reasons:
                # Don't show [WARNING] items as they didn't cause failure
                if not reason.startswith("[WARNING]"):
                    print(f"      {reason}")

    # List tests with warnings (passed but had issues)
    warnings_tests = [
        r for r in results
        if r.passed and any(reason.startswith("[WARNING]") for reason in r.failure_reasons)
    ]
    if warnings_tests:
        print("\nPassed with Warnings (semantic match overrode keyword/routing checks):")
        for w in warnings_tests:
            print(f"  - [{w.scenario_id}] {w.scenario_name}")
            for reason in w.failure_reasons:
                if reason.startswith("[WARNING]"):
                    print(f"      {reason}")

    # List clarification requests
    clarification_tests = [
        r for r in results if r.response_accuracy == "clarification_requested"
    ]
    if clarification_tests:
        print("\nClarification Requested (tie detected, valid behavior):")
        for c in clarification_tests:
            print(f"  - [{c.scenario_id}] {c.scenario_name}")
            print(f"      Votes: {c.vote_distribution}")

    # Latency stats
    latencies = [r.latency_ms for r in results]
    print(f"\nLatency: avg={sum(latencies)/len(latencies):.0f}ms, "
          f"min={min(latencies):.0f}ms, max={max(latencies):.0f}ms")

    print("=" * 70 + "\n")


def save_results(results: List[TestResult], output_dir: str = "logs/test_results") -> str:
    """Save test results to JSON file."""
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_run_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    clarification_count = sum(
        1 for r in results if r.response_accuracy == "clarification_requested"
    )

    # Ground truth accuracy stats (exclude clarification_requested)
    with_ground_truth = [
        r for r in results
        if r.response_accuracy is not None and r.response_accuracy != "clarification_requested"
    ]
    accuracy_stats = None
    if with_ground_truth:
        accuracy_stats = {
            "total_with_ground_truth": len(with_ground_truth),
            "match": sum(1 for r in with_ground_truth if r.response_accuracy == "match"),
            "partial": sum(1 for r in with_ground_truth if r.response_accuracy == "partial"),
            "mismatch": sum(1 for r in with_ground_truth if r.response_accuracy == "mismatch"),
        }

    output = {
        "timestamp": timestamp,
        "total_tests": total,
        "passed": passed,
        "failed": total - passed,
        "clarification_requests": clarification_count,
        "pass_rate": round(100 * passed / total, 2),
        "ground_truth_accuracy": accuracy_stats,
        "results": [
            {
                "scenario_id": r.scenario_id,
                "scenario_name": r.scenario_name,
                "category": r.category,
                "input": r.input_message,
                "passed": r.passed,
                "actual_agent": r.actual_agent,
                "actual_scope": r.actual_scope,
                "vote_distribution": r.vote_distribution,
                "latency_ms": round(r.latency_ms, 2),
                "failure_reasons": r.failure_reasons,
                "response": r.response[:500] if len(r.response) > 500 else r.response,
                "expected_response": r.expected_response,
                "response_accuracy": r.response_accuracy,
            }
            for r in results
        ],
    }

    with open(filepath, "w") as f:
        json.dump(output, f, indent=2)

    return filepath
