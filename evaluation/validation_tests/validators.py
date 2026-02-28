# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/validation_tests/validators.py
"""
Validators for framework validation tests.

Provides validation functions for technical, reasoning, and semantic
correctness of the evaluation framework.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from ..metrics import ExperimentResult, TurnMetrics
from ..config.personas import Persona


@dataclass
class ValidationResult:
    """Result of a validation check."""

    passed: bool
    category: str  # "technical", "reasoning", "semantic"
    check_name: str
    message: str
    details: Optional[Dict[str, Any]] = None
    severity: str = "error"  # "error", "warning", "info"


@dataclass
class ValidationReport:
    """Complete validation report for a pilot test."""

    results: List[ValidationResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Check if all validations passed (no errors)."""
        return all(r.passed or r.severity != "error" for r in self.results)

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return any(not r.passed and r.severity == "warning" for r in self.results)

    @property
    def errors(self) -> List[ValidationResult]:
        """Get all failed checks with error severity."""
        return [r for r in self.results if not r.passed and r.severity == "error"]

    @property
    def warnings(self) -> List[ValidationResult]:
        """Get all failed checks with warning severity."""
        return [r for r in self.results if not r.passed and r.severity == "warning"]

    def add(self, result: ValidationResult) -> None:
        """Add a validation result."""
        self.results.append(result)

    def summary(self) -> str:
        """Get summary status."""
        if not self.passed:
            return "FAIL"
        elif self.has_warnings:
            return "WARN"
        else:
            return "PASS"


# =============================================================================
# TECHNICAL VALIDATORS
# =============================================================================

def validate_technical(
    result: ExperimentResult,
    max_acceptable_errors: int = 0,
    max_latency_ms: float = 60000,  # 60 seconds
) -> List[ValidationResult]:
    """
    Validate technical correctness of the experiment.

    Checks:
    - No exceptions during conversation
    - API calls succeeded
    - Latency within bounds
    - Evaluator produced valid output
    """
    validations = []

    # Check for errors in turns
    error_count = result.system_metrics.error_count
    validations.append(ValidationResult(
        passed=error_count <= max_acceptable_errors,
        category="technical",
        check_name="error_count",
        message=f"Found {error_count} errors (max acceptable: {max_acceptable_errors})",
        details={"error_count": error_count, "max_acceptable": max_acceptable_errors},
        severity="error" if error_count > max_acceptable_errors else "info",
    ))

    # Check latency
    max_observed = result.system_metrics.max_latency_ms
    validations.append(ValidationResult(
        passed=max_observed <= max_latency_ms,
        category="technical",
        check_name="latency_bounds",
        message=f"Max latency: {max_observed:.0f}ms (limit: {max_latency_ms:.0f}ms)",
        details={"max_latency_ms": max_observed, "limit_ms": max_latency_ms},
        severity="error" if max_observed > max_latency_ms else "info",
    ))

    # Check evaluator output validity
    has_scores = len(result.quality_metrics.dimension_scores) > 0
    validations.append(ValidationResult(
        passed=has_scores,
        category="technical",
        check_name="evaluator_output",
        message="Evaluator produced dimension scores" if has_scores else "Evaluator failed to produce scores",
        details={"dimension_count": len(result.quality_metrics.dimension_scores)},
        severity="error" if not has_scores else "info",
    ))

    # Check score ranges (1-5)
    scores_valid = all(
        1 <= score <= 5
        for score in result.quality_metrics.dimension_scores.values()
    )
    validations.append(ValidationResult(
        passed=scores_valid,
        category="technical",
        check_name="score_ranges",
        message="All scores within 1-5 range" if scores_valid else "Some scores outside valid range",
        details={"scores": result.quality_metrics.dimension_scores},
        severity="error" if not scores_valid else "info",
    ))

    # Check that conversation has content
    has_turns = result.system_metrics.total_turns > 0
    validations.append(ValidationResult(
        passed=has_turns,
        category="technical",
        check_name="conversation_exists",
        message=f"Conversation has {result.system_metrics.total_turns} turns",
        details={"total_turns": result.system_metrics.total_turns},
        severity="error" if not has_turns else "info",
    ))

    return validations


# =============================================================================
# REASONING VALIDATORS
# =============================================================================

# Patterns that indicate AI/LLM breaking character
CHARACTER_BREAK_PATTERNS = [
    r"as an ai",
    r"as a language model",
    r"i am an ai",
    r"i'm an ai",
    r"i cannot actually",
    r"i don't have feelings",
    r"i was trained",
    r"my training data",
    r"i apologize, but as",
    r"i'm not able to",
    r"as a helpful assistant",
]


def validate_reasoning(
    result: ExperimentResult,
    persona: Persona,
    expect_goal_completion: bool = True,
) -> List[ValidationResult]:
    """
    Validate reasoning correctness of the conversation.

    Checks:
    - Simulated user stays in character
    - Goal signaling is appropriate
    - User messages are coherent
    """
    validations = []

    # Extract user messages from transcript
    user_messages = _extract_user_messages(result.conversation_transcript)

    # Check for character breaks in user messages
    character_breaks = []
    for i, msg in enumerate(user_messages):
        msg_lower = msg.lower()
        for pattern in CHARACTER_BREAK_PATTERNS:
            if re.search(pattern, msg_lower):
                character_breaks.append((i + 1, pattern, msg[:100]))
                break

    validations.append(ValidationResult(
        passed=len(character_breaks) == 0,
        category="reasoning",
        check_name="persona_consistency",
        message=(
            "User stayed in character"
            if len(character_breaks) == 0
            else f"User broke character {len(character_breaks)} time(s)"
        ),
        details={"breaks": character_breaks} if character_breaks else None,
        severity="error" if character_breaks else "info",
    ))

    # Check goal completion matches expectation
    goal_achieved = result.task_metrics.goal_achieved
    if expect_goal_completion:
        validations.append(ValidationResult(
            passed=goal_achieved,
            category="reasoning",
            check_name="goal_completion",
            message="User signaled goal completion" if goal_achieved else "User did not signal goal completion",
            details={
                "goal_achieved": goal_achieved,
                "terminated_reason": result.task_metrics.terminated_reason,
            },
            severity="warning" if not goal_achieved else "info",
        ))
    else:
        validations.append(ValidationResult(
            passed=True,
            category="reasoning",
            check_name="goal_completion",
            message="Goal completion not expected for this scenario",
            severity="info",
        ))

    # Check evaluator reasoning is present
    has_reasoning = (
        len(result.quality_metrics.strengths) > 0 or
        len(result.quality_metrics.weaknesses) > 0
    )
    validations.append(ValidationResult(
        passed=has_reasoning,
        category="reasoning",
        check_name="evaluator_reasoning",
        message="Evaluator provided reasoning" if has_reasoning else "Evaluator provided no reasoning",
        details={
            "strengths_count": len(result.quality_metrics.strengths),
            "weaknesses_count": len(result.quality_metrics.weaknesses),
        },
        severity="warning" if not has_reasoning else "info",
    ))

    # Check user messages are non-empty and coherent (basic check)
    empty_messages = sum(1 for msg in user_messages if len(msg.strip()) < 5)
    validations.append(ValidationResult(
        passed=empty_messages == 0,
        category="reasoning",
        check_name="message_coherence",
        message=(
            "All user messages have content"
            if empty_messages == 0
            else f"{empty_messages} user message(s) are too short"
        ),
        details={"empty_count": empty_messages},
        severity="warning" if empty_messages > 0 else "info",
    ))

    return validations


# =============================================================================
# SEMANTIC VALIDATORS
# =============================================================================

def validate_semantic(
    result: ExperimentResult,
    persona: Persona,
) -> List[ValidationResult]:
    """
    Validate semantic correctness of the conversation.

    Checks:
    - Conversation progresses (no repetition loops)
    - Responses relate to questions (topical coherence)
    - Natural conclusion
    """
    validations = []

    # Extract messages
    user_messages = _extract_user_messages(result.conversation_transcript)
    system_messages = _extract_system_messages(result.conversation_transcript)

    # Check for repetition loops (user repeating same message)
    repetition_count = _count_repetitions(user_messages)
    validations.append(ValidationResult(
        passed=repetition_count == 0,
        category="semantic",
        check_name="no_repetition_loops",
        message=(
            "No repetition loops detected"
            if repetition_count == 0
            else f"Detected {repetition_count} repeated message(s)"
        ),
        details={"repetition_count": repetition_count},
        severity="error" if repetition_count > 1 else ("warning" if repetition_count == 1 else "info"),
    ))

    # Check conversation progresses (messages get shorter near end or conclude)
    progression_ok = _check_conversation_progression(user_messages)
    validations.append(ValidationResult(
        passed=progression_ok,
        category="semantic",
        check_name="conversation_progression",
        message="Conversation shows natural progression" if progression_ok else "Conversation may be stuck",
        severity="warning" if not progression_ok else "info",
    ))

    # Check for nonsensical exchanges (very basic heuristic)
    # This is a placeholder - could be enhanced with semantic similarity
    has_content = all(len(msg) > 10 for msg in system_messages)
    validations.append(ValidationResult(
        passed=has_content,
        category="semantic",
        check_name="response_substance",
        message="System responses have substance" if has_content else "Some system responses lack content",
        severity="warning" if not has_content else "info",
    ))

    # Check overall quality score is reasonable
    llm_judge_score = result.quality_metrics.llm_judge_score
    validations.append(ValidationResult(
        passed=llm_judge_score >= 2.0,
        category="semantic",
        check_name="quality_threshold",
        message=f"LLM judge score: {llm_judge_score:.2f}/5.0",
        details={"llm_judge_score": llm_judge_score},
        severity="warning" if llm_judge_score < 2.0 else "info",
    ))

    return validations


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _extract_user_messages(transcript: str) -> List[str]:
    """Extract user messages from transcript."""
    messages = []
    # Pattern: [Turn N] User: message
    pattern = r"\[Turn \d+\] User: (.+?)(?=\[Turn \d+\]|$)"
    matches = re.findall(pattern, transcript, re.DOTALL)
    return [m.strip() for m in matches]


def _extract_system_messages(transcript: str) -> List[str]:
    """Extract system (HEMA) messages from transcript."""
    messages = []
    # Pattern: [Turn N] HEMA: message
    pattern = r"\[Turn \d+\] HEMA: (.+?)(?=\[Turn \d+\]|$)"
    matches = re.findall(pattern, transcript, re.DOTALL)
    return [m.strip() for m in matches]


def _count_repetitions(messages: List[str]) -> int:
    """Count how many messages are near-duplicates of previous messages."""
    if len(messages) < 2:
        return 0

    repetitions = 0
    for i in range(1, len(messages)):
        # Simple similarity check - could be enhanced
        if _is_similar(messages[i], messages[i - 1]):
            repetitions += 1

    return repetitions


def _is_similar(msg1: str, msg2: str, threshold: float = 0.8) -> bool:
    """Check if two messages are similar (simple word overlap)."""
    words1 = set(msg1.lower().split())
    words2 = set(msg2.lower().split())

    if not words1 or not words2:
        return False

    intersection = words1 & words2
    union = words1 | words2

    jaccard = len(intersection) / len(union) if union else 0
    return jaccard > threshold


def _check_conversation_progression(messages: List[str]) -> bool:
    """Check if conversation shows natural progression."""
    if len(messages) < 3:
        return True  # Too short to judge

    # Check that not all messages are the same length (indicates variety)
    lengths = [len(m) for m in messages]
    length_variance = max(lengths) - min(lengths)

    # Some variance in message length suggests natural conversation
    return length_variance > 20


def run_all_validations(
    result: ExperimentResult,
    persona: Persona,
    expect_goal_completion: bool = True,
    max_acceptable_errors: int = 0,
) -> ValidationReport:
    """Run all validations and return a complete report."""
    report = ValidationReport()

    # Technical validations
    for v in validate_technical(result, max_acceptable_errors):
        report.add(v)

    # Reasoning validations
    for v in validate_reasoning(result, persona, expect_goal_completion):
        report.add(v)

    # Semantic validations
    for v in validate_semantic(result, persona):
        report.add(v)

    return report
