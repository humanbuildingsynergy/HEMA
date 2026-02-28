# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/graph/routing.py
"""Conditional routing logic for the multi-agent energy analysis graph."""
from typing import Dict, Any, List, Literal, Optional, Tuple
from utils.logger import setup_logger

logger = setup_logger()

# Type alias for agent routing destinations
AgentDestination = Literal["analysis_agent", "knowledge_agent", "control_agent", "fallback_handler"]

# Type alias for classification results
ClassificationOutput = Tuple[Optional[str], Optional[str], bool, Optional[List[Dict[str, str]]]]


def route_to_agent(state: Dict[str, Any]) -> AgentDestination:
    """
    Route to the appropriate specialized agent based on query classification.

    This is the primary router in the multi-agent architecture.

    Args:
        state: Current graph state with target_agent set by classifier

    Returns:
        Name of the agent node to execute
    """
    target_agent = state.get("target_agent", "fallback_handler")
    query_type = state.get("query_type", "general")

    logger.info(f"Routing to agent: target_agent={target_agent}, query_type={query_type}")

    # Map query types to agents if target_agent not explicitly set
    if not target_agent or target_agent == "fallback_handler":
        if query_type in ["data_load", "analysis", "recommendation"]:
            return "analysis_agent"
        elif query_type in ["knowledge", "concept", "how_to"]:
            return "knowledge_agent"
        elif query_type in ["control", "device", "thermostat", "schedule"]:
            return "control_agent"
        else:
            # Default to fallback_handler for general queries
            return "fallback_handler"

    return target_agent


def classify_with_self_consistency(
    user_query: str,
    conversation_context: Optional[str] = None
) -> ClassificationOutput:
    """
    Classify user query using self-consistency voting (N=4).

    Uses multiple LLM calls with temperature > 0 to get diverse reasoning paths,
    then votes on agent. Ties trigger user clarification.

    Args:
        user_query: The user's query string
        conversation_context: Optional summary of recent conversation for context

    Returns:
        Tuple of (agent, intent, needs_clarification, clarification_options)
        - If needs_clarification is True, agent and intent are None
        - clarification_options contains user-friendly choices for disambiguation
    """
    from agents.graph.self_consistency_classifier import classify_query as sc_classify
    return sc_classify(user_query, conversation_context)


def classify_with_self_consistency_full(
    user_query: str,
    conversation_context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Classify user query using self-consistency voting with full result.

    Returns all classification details including vote distribution and
    personalization intent for logging and data-aware routing.

    Args:
        user_query: The user's query string
        conversation_context: Optional summary of recent conversation for context

    Returns:
        Dict with agent, intent, personalization_intent, vote distributions,
        needs_clarification, etc.
    """
    from agents.graph.self_consistency_classifier import classify_query_full
    result = classify_query_full(user_query, conversation_context)

    return {
        "agent": result.agent,
        "intent": result.intent,
        "personalization_intent": result.personalization_intent,
        "vote_distribution": result.vote_distribution,
        "personalization_distribution": result.personalization_distribution,
        "needs_clarification": result.needs_clarification,
        "clarification_options": result.clarification_options,
        "is_consensus": result.is_consensus,
    }


def resolve_user_clarification(
    selected_agent: str,
    original_results: List[Any]
) -> Tuple[str, str]:
    """
    Resolve classification after user selects from clarification options.

    Args:
        selected_agent: The agent selected by the user (e.g., "analysis_agent", "knowledge_agent")
        original_results: The original classification results from self-consistency

    Returns:
        Tuple of (agent, intent)
    """
    from agents.graph.self_consistency_classifier import resolve_clarification
    return resolve_clarification(selected_agent, original_results)


def should_continue_after_node(state: Dict[str, Any]) -> Literal["continue", "end"]:
    """
    Determine if the graph should continue or end after a node.

    Args:
        state: Current graph state

    Returns:
        "continue" to proceed to response node, "end" to finish
    """
    # If there's an error, end the flow
    if state.get("error"):
        logger.info("Error detected, ending flow")
        return "end"

    # If there's a final response, end the flow
    if state.get("final_response"):
        return "end"

    # Continue to response node
    return "continue"
