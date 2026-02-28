# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/evaluator/objective_metrics.py
"""Objective metrics computation using three-tier approach.

Tier 1: Pure counting (no LLM needed) — turn counts, response lengths
Tier 2: LLM-based semantic extraction — questions, recommendations, jargon
Tier 3: Factual claims verification — LLM extracts claim-value pairs, error % computed arithmetically
"""

import json
import statistics
from typing import List, Optional, TYPE_CHECKING

from langchain_core.messages import HumanMessage, SystemMessage

from utils.logger import setup_logger
from .dataclasses import ObjectiveMetrics
from .prompts import SEMANTIC_EXTRACTION_PROMPT, FACTUAL_CLAIMS_PROMPT

if TYPE_CHECKING:
    from evaluation.data.ground_truth import GroundTruthSummary

logger = setup_logger(__name__)


def compute_objective_metrics(
    conversation_history: List[dict],
    llm,
    use_llm_extraction: bool = True,
    ground_truth: Optional["GroundTruthSummary"] = None,
) -> ObjectiveMetrics:
    """
    Compute objective metrics using a principled three-tier approach.

    Tier 1: Pure counting (no LLM needed) - always computed
    Tier 2: LLM-based semantic extraction - computed if use_llm_extraction=True
    Tier 3: Factual claims verification - computed if ground_truth is provided

    Args:
        conversation_history: The conversation to analyze
        llm: LLM instance for semantic extraction
        use_llm_extraction: Whether to use LLM for semantic extraction (Tier 2)
        ground_truth: Optional ground truth data for factual accuracy verification (Tier 3)

    Returns:
        ObjectiveMetrics with all tiers populated
    """
    metrics = ObjectiveMetrics()

    # === Tier 1: Pure Counting ===
    system_response_lengths = []

    for turn in conversation_history:
        content = turn["content"]

        if turn["role"] == "user":
            metrics.user_turns += 1
            # Simple presence of question mark (not semantic)
            if "?" in content:
                metrics.user_messages_with_questions += 1
        else:
            metrics.system_turns += 1
            system_response_lengths.append(len(content))

    metrics.total_turns = metrics.user_turns + metrics.system_turns

    if system_response_lengths:
        metrics.avg_system_response_length = statistics.mean(system_response_lengths)
        metrics.max_system_response_length = max(system_response_lengths)
        metrics.min_system_response_length = min(system_response_lengths)

    # === Tier 2: LLM-based Semantic Extraction ===
    if use_llm_extraction and llm is not None:
        semantic_metrics = extract_semantic_metrics(conversation_history, llm)
        # Merge semantic metrics into the ObjectiveMetrics
        metrics.user_questions = semantic_metrics.get("user_questions", [])
        metrics.questions_answered = semantic_metrics.get("questions_answered", [])
        metrics.questions_unanswered = semantic_metrics.get("questions_unanswered", [])
        metrics.data_sources_referenced = semantic_metrics.get("data_sources_referenced", [])
        metrics.actionable_recommendations = semantic_metrics.get("actionable_recommendations", [])
        metrics.general_suggestions = semantic_metrics.get("general_suggestions", [])
        metrics.technical_terms_explained = semantic_metrics.get("technical_terms_explained", [])
        metrics.unexplained_jargon = semantic_metrics.get("unexplained_jargon", [])

        # Question type classification
        metrics.data_specific_questions = semantic_metrics.get("data_specific_questions", [])
        metrics.general_knowledge_questions = semantic_metrics.get("general_knowledge_questions", [])

        # Response Appropriateness Matrix (4 cells)
        metrics.appropriate_data_backed = semantic_metrics.get("appropriate_data_backed", [])
        metrics.over_personalized = semantic_metrics.get("over_personalized", [])
        metrics.under_personalized = semantic_metrics.get("under_personalized", [])
        metrics.appropriate_general = semantic_metrics.get("appropriate_general", [])

    # === Tier 3: Factual Claims Verification ===
    if use_llm_extraction and llm is not None and ground_truth is not None:
        metrics.factual_claims = extract_factual_claims(conversation_history, llm, ground_truth)

    return metrics


def extract_semantic_metrics(conversation_history: List[dict], llm) -> dict:
    """
    Use LLM to extract semantic metrics that require understanding.

    This provides accurate extraction of:
    - User questions (actual questions, not just sentences with "?")
    - Whether questions were answered
    - Actionable vs generic recommendations
    - Technical terms and whether they were explained

    Args:
        conversation_history: The conversation to analyze
        llm: LLM instance for extraction

    Returns:
        Dict with extracted items for each metric category
    """
    transcript = format_transcript(conversation_history)

    messages = [
        SystemMessage(content="You are a precise conversation analyzer. Extract exactly what is asked."),
        HumanMessage(content=SEMANTIC_EXTRACTION_PROMPT.format(transcript=transcript)),
    ]

    try:
        response = llm.invoke(messages)
        raw_response = response.content

        # Parse JSON response
        json_str = extract_json(raw_response)
        data = json.loads(json_str)

        # Validate and return
        return {
            "user_questions": data.get("user_questions", [])[:20],  # Cap at 20 items
            "questions_answered": data.get("questions_answered", [])[:20],
            "questions_unanswered": data.get("questions_unanswered", [])[:20],
            "data_sources_referenced": data.get("data_sources_referenced", [])[:10],
            "actionable_recommendations": data.get("actionable_recommendations", [])[:20],
            "general_suggestions": data.get("general_suggestions", [])[:20],
            "technical_terms_explained": data.get("technical_terms_explained", [])[:15],
            "unexplained_jargon": data.get("unexplained_jargon", [])[:15],
            # Question type classification
            "data_specific_questions": data.get("data_specific_questions", [])[:20],
            "general_knowledge_questions": data.get("general_knowledge_questions", [])[:20],
            # Response Appropriateness Matrix (4 cells)
            "appropriate_data_backed": data.get("appropriate_data_backed", [])[:20],
            "over_personalized": data.get("over_personalized", [])[:20],
            "under_personalized": data.get("under_personalized", [])[:20],
            "appropriate_general": data.get("appropriate_general", [])[:20],
        }

    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"Semantic metric extraction failed: {e}")
        # Return empty dict on failure - Tier 1 metrics will still be valid
        return {}


def format_transcript(conversation_history: List[dict]) -> str:
    """Format conversation history as a readable transcript."""
    lines = []
    for i, turn in enumerate(conversation_history):
        role = "User" if turn["role"] == "user" else "HEMA"
        lines.append(f"[Turn {i+1}] {role}: {turn['content']}")
    return "\n\n".join(lines)


def extract_json(raw_response: str) -> str:
    """Extract JSON from raw LLM response."""
    json_str = raw_response

    if "```json" in raw_response:
        start = raw_response.index("```json") + 7
        end = raw_response.find("```", start)
        if end == -1:
            # No closing ``` - take everything after ```json
            json_str = raw_response[start:].strip()
        else:
            json_str = raw_response[start:end].strip()
    elif "```" in raw_response:
        start = raw_response.index("```") + 3
        end = raw_response.find("```", start)
        if end == -1:
            json_str = raw_response[start:].strip()
        else:
            json_str = raw_response[start:end].strip()
    elif "{" in raw_response:
        start = raw_response.index("{")
        end = raw_response.rfind("}")
        if end != -1:
            json_str = raw_response[start:end + 1]
        else:
            # No closing brace - take everything from first {
            json_str = raw_response[start:]

    return json_str


def extract_factual_claims(
    conversation_history: List[dict],
    llm,
    ground_truth: "GroundTruthSummary",
) -> List[dict]:
    """
    Extract factual claims from HEMA's responses and compute error % against ground truth.

    Uses LLM to identify numerical claims and pair them with ground truth values,
    then computes error percentage arithmetically (deterministic).

    Args:
        conversation_history: The conversation to analyze
        llm: LLM instance for claim extraction
        ground_truth: Verified ground truth data for comparison

    Returns:
        List of claim dicts, each with:
        - claim_text: The original claim text
        - claimed_value: The numerical value HEMA claimed
        - ground_truth_value: The corresponding ground truth value
        - unit: Type of value (kwh, percentage, rank, dollars, etc.)
        - category: Claim category (consumption, appliance_share, ranking, etc.)
        - error_pct: |claimed - actual| / actual * 100 (computed arithmetically)
    """
    transcript = format_transcript(conversation_history)
    ground_truth_context = ground_truth.to_evaluation_context()

    messages = [
        SystemMessage(content="You are a precise fact-checker. Extract numerical claims and match them to ground truth."),
        HumanMessage(content=FACTUAL_CLAIMS_PROMPT.format(
            transcript=transcript,
            ground_truth=ground_truth_context,
        )),
    ]

    try:
        response = llm.invoke(messages)
        raw_response = response.content

        # Parse JSON response
        json_str = extract_json(raw_response)
        data = json.loads(json_str)

        raw_claims = data.get("factual_claims", [])[:30]  # Cap at 30 claims

        # Compute error % for each claim (pure arithmetic)
        verified_claims = []
        for claim in raw_claims:
            try:
                claimed = float(claim.get("claimed_value", 0))
                actual = float(claim.get("ground_truth_value", 0))

                # Compute error percentage
                if actual != 0:
                    error_pct = abs(claimed - actual) / abs(actual) * 100
                elif claimed == 0:
                    error_pct = 0.0  # Both zero — no error
                else:
                    error_pct = 100.0  # Claimed nonzero, actual is zero

                verified_claims.append({
                    "claim_text": str(claim.get("claim_text", ""))[:100],
                    "claimed_value": claimed,
                    "ground_truth_value": actual,
                    "unit": str(claim.get("unit", "other")),
                    "category": str(claim.get("category", "other")),
                    "error_pct": round(error_pct, 2),
                })
            except (ValueError, TypeError) as e:
                logger.debug(f"Skipping claim with invalid values: {claim} ({e})")
                continue

        logger.info(f"Factual claims extracted: {len(verified_claims)} claims verified")
        return verified_claims

    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"Factual claims extraction failed: {e}")
        return []


def extract_control_semantic_metrics(
    conversation_history: List[dict],
    llm,
) -> dict:
    """
    Extract control-specific semantic metrics from a conversation.

    This extracts:
    - Action confirmations (explicit confirmation of completed actions)
    - Action explanations (reasoning for why a setting/action was chosen)
    - User control requests and fulfillment status
    - Device status provided

    Args:
        conversation_history: The conversation to analyze
        llm: LLM instance for extraction

    Returns:
        Dict with extracted control metrics
    """
    from .prompts import CONTROL_SEMANTIC_EXTRACTION_PROMPT

    transcript = format_transcript(conversation_history)

    messages = [
        SystemMessage(content="You are a precise conversation analyzer for device control interactions."),
        HumanMessage(content=CONTROL_SEMANTIC_EXTRACTION_PROMPT.format(transcript=transcript)),
    ]

    try:
        response = llm.invoke(messages)
        raw_response = response.content

        # Parse JSON response
        json_str = extract_json(raw_response)
        data = json.loads(json_str)

        return {
            "action_confirmations": data.get("action_confirmations", [])[:20],
            "action_explanations": data.get("action_explanations", [])[:20],
            "user_control_requests": data.get("user_control_requests", [])[:20],
            "control_requests_fulfilled": data.get("control_requests_fulfilled", [])[:20],
            "control_requests_not_fulfilled": data.get("control_requests_not_fulfilled", [])[:20],
            "device_status_provided": data.get("device_status_provided", [])[:20],
        }

    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"Control semantic metric extraction failed: {e}")
        return {
            "action_confirmations": [],
            "action_explanations": [],
            "user_control_requests": [],
            "control_requests_fulfilled": [],
            "control_requests_not_fulfilled": [],
            "device_status_provided": [],
        }
