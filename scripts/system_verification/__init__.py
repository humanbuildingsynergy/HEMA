# scripts/system_verification/__init__.py
"""System verification test scenarios for HEMA.

This package contains single-turn test cases that verify the HEMA system
responds correctly to specific inputs - essentially unit/integration tests.
"""
from .models import TestScenario, TestResult
from .scenarios import TEST_SCENARIOS, CATEGORIES
from .comparison import compute_response_accuracy
from .runner import run_single_test, run_tests
from .reporting import print_summary, save_results

__all__ = [
    # Models
    "TestScenario",
    "TestResult",
    # Scenarios
    "TEST_SCENARIOS",
    "CATEGORIES",
    # Functions
    "compute_response_accuracy",
    "run_single_test",
    "run_tests",
    "print_summary",
    "save_results",
]
