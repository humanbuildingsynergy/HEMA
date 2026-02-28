# evaluation/evaluator/__init__.py
"""
Conversation evaluation module using objective metrics only.

All evaluation is based on automatically-counted metrics:
- Tier 1: Pure counting (turns, questions, response length)
- Tier 2: LLM-extracted metrics (questions, recommendations, jargon, etc.)
- Tier 3: Factual claim verification (when ground truth available)

LLM is used ONLY for extraction, not for subjective judgment.

Components:
- ConversationEvaluator: Main evaluator class
- ObjectiveMetrics: Three-tier objective metrics (counting + LLM extraction + factual claims)
- EvaluationResult: Complete evaluation result

Functions:
- compute_objective_metrics: Compute objective metrics from conversation
- extract_semantic_metrics: Extract semantic metrics using LLM
- extract_factual_claims: Extract and verify factual claims against ground truth
"""

# Dataclasses
from .dataclasses import (
    ObjectiveMetrics,
    EvaluationResult,
)

# Prompts
from .prompts import (
    SEMANTIC_EXTRACTION_PROMPT,
    FACTUAL_CLAIMS_PROMPT,
)

# Objective metrics functions
from .objective_metrics import (
    compute_objective_metrics,
    extract_semantic_metrics,
    extract_factual_claims,
    format_transcript,
)

# Main evaluator class
from .evaluator import ConversationEvaluator

__all__ = [
    # Dataclasses
    "ObjectiveMetrics",
    "EvaluationResult",
    # Prompts
    "SEMANTIC_EXTRACTION_PROMPT",
    "FACTUAL_CLAIMS_PROMPT",
    # Functions
    "compute_objective_metrics",
    "extract_semantic_metrics",
    "extract_factual_claims",
    "format_transcript",
    # Main class
    "ConversationEvaluator",
]
