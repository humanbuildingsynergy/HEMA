# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# scripts/test_scenarios/comparison.py
"""Ground truth comparison functions for test scenarios."""
from typing import Optional

# Global LLM instance for ground truth comparison (lazy initialized)
_ground_truth_llm = None


def _get_ground_truth_llm():
    """Get or create an LLM instance for ground truth comparison."""
    global _ground_truth_llm
    if _ground_truth_llm is None:
        try:
            # Try Ollama first (local, free)
            from langchain_ollama import ChatOllama
            _ground_truth_llm = ChatOllama(
                model="llama3.1:8b",
                base_url="http://localhost:11434",
                temperature=0,
            )
        except Exception:
            # Fall back to keyword matching
            _ground_truth_llm = "fallback"
    return _ground_truth_llm


def compute_response_accuracy(
    actual_response: str,
    expected_response: Optional[str],
) -> Optional[str]:
    """
    Compare actual response against ground truth expected response.

    Uses Ollama LLM for semantic comparison when available, with keyword
    matching as fallback.

    Returns:
    - "match": Responses convey the same core information
    - "partial": Responses share some relevant content but differ in key aspects
    - "mismatch": Responses are significantly different in meaning
    - None: No expected response provided

    Args:
        actual_response: The actual response from the system
        expected_response: The ground truth expected response

    Returns:
        Accuracy level string or None if no ground truth
    """
    if not expected_response:
        return None

    # Try LLM-based comparison first
    llm = _get_ground_truth_llm()

    if llm != "fallback":
        try:
            return _llm_compare_responses(llm, actual_response, expected_response)
        except Exception:
            # Fall through to keyword matching
            pass

    # Fallback: keyword-based comparison
    return _keyword_compare_responses(actual_response, expected_response)


def _llm_compare_responses(llm, actual_response: str, expected_response: str) -> str:
    """Use LLM to semantically compare responses."""
    prompt = f"""Compare these two responses and determine if they convey the same core information.

EXPECTED RESPONSE (ground truth):
{expected_response}

ACTUAL RESPONSE:
{actual_response}

Evaluate semantic similarity:
- "match": Both responses convey the same core information and key points, even if wording differs
- "partial": Responses share some relevant content but differ in important aspects or miss key points
- "mismatch": Responses are significantly different in meaning or the actual response is incorrect/irrelevant

Respond with ONLY one word: match, partial, or mismatch"""

    result = llm.invoke(prompt)
    answer = result.content.strip().lower()

    # Parse the response
    if "match" in answer and "mismatch" not in answer:
        return "match"
    elif "partial" in answer:
        return "partial"
    else:
        return "mismatch"


def _keyword_compare_responses(actual_response: str, expected_response: str) -> str:
    """Fallback keyword-based comparison."""
    # Normalize both responses for comparison
    actual_lower = actual_response.lower().strip()
    expected_lower = expected_response.lower().strip()

    # If responses are very similar (accounting for minor variations)
    if actual_lower == expected_lower:
        return "match"

    # Extract key phrases (words longer than 3 chars) from expected response
    expected_words = set(
        word for word in expected_lower.split()
        if len(word) > 3 and word.isalnum()
    )

    if not expected_words:
        # No meaningful words to compare, check basic similarity
        return "match" if expected_lower in actual_lower else "partial"

    # Count how many expected key words appear in actual response
    matching_words = sum(1 for word in expected_words if word in actual_lower)
    match_ratio = matching_words / len(expected_words)

    if match_ratio >= 0.8:
        return "match"
    elif match_ratio >= 0.4:
        return "partial"
    else:
        return "mismatch"
