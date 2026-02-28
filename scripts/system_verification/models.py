# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# scripts/test_scenarios/models.py
"""Data models for test scenarios."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TestScenario:
    """A single test scenario."""

    id: str
    name: str
    category: str
    input_message: str
    expected_agent: Optional[str] = None
    expected_scope: Optional[str] = None  # Deprecated, kept for backward compatibility
    expected_contains: Optional[List[str]] = None  # Response should contain these
    expected_not_contains: Optional[List[str]] = None  # Response should not contain these
    expected_response: Optional[str] = None  # Ground truth response for accuracy comparison
    description: str = ""


@dataclass
class TestResult:
    """Result of running a single test."""

    scenario_id: str
    scenario_name: str
    category: str
    input_message: str
    passed: bool
    response: str
    actual_agent: Optional[str]
    vote_distribution: Optional[Dict[str, int]]
    latency_ms: float
    failure_reasons: List[str] = field(default_factory=list)
    expected_response: Optional[str] = None  # Ground truth for reference
    response_accuracy: Optional[str] = None  # "match", "partial", "mismatch", or None
    actual_scope: Optional[str] = None  # Deprecated, kept for backward compatibility
