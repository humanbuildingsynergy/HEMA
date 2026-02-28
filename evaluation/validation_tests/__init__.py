# evaluation/validation_tests/__init__.py
"""
Framework Validation Tests for LLM-as-Simulated-User Evaluation.

This package validates that the evaluation framework produces meaningful,
realistic multi-turn conversations before running full-scale evaluations.

Unlike system_verification (which tests HEMA responses to specific inputs),
validation tests verify the entire evaluation pipeline:

- Simulated user generates coherent, persona-consistent messages
- HEMA responds appropriately to multi-turn conversations
- Conversations flow naturally without loops or semantic errors
- Evaluator produces valid, meaningful judgments
- No technical errors occur during the full pipeline

Usage:
    python -m evaluation.run_experiment --validate
    python -m evaluation.run_experiment --validate --verbose
"""

from .scenarios import VALIDATION_SCENARIOS, ValidationScenario
from .validators import (
    ValidationResult,
    validate_technical,
    validate_reasoning,
    validate_semantic,
)
from .runner import run_validation_tests, ValidationTestResult

__all__ = [
    # Scenarios
    "VALIDATION_SCENARIOS",
    "ValidationScenario",
    # Validators
    "ValidationResult",
    "validate_technical",
    "validate_reasoning",
    "validate_semantic",
    # Runner
    "run_validation_tests",
    "ValidationTestResult",
]
