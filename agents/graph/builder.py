# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/graph/builder.py
"""Graph builder for the multi-agent energy analysis workflow.

This module orchestrates the graph topology, combining node implementations
from dedicated modules (message_utils, nodes, runner).
"""
from typing import Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from utils.logger import setup_logger
from .state import HEMAGraphState
from .routing import route_to_agent
from .message_utils import extract_tool_calls_from_messages, _generate_conversation_summary
from .nodes import (
    create_classifier_node,
    create_analysis_agent_node,
    create_knowledge_agent_node,
    create_control_agent_node,
    fallback_handler_node,
    clarification_node,
    route_after_classification,
)

logger = setup_logger()


def build_multi_agent_graph(
    checkpointer: Optional[MemorySaver] = None,
):
    """
    Build and compile the multi-agent energy analysis graph.

    Architecture:
        [START] -> [classifier] -> route_to_agent -> [agent] -> [END]

    Agents:
        - analysis_agent: Energy data analysis (load, analyze, recommend)
        - knowledge_agent: Theoretical Q&A about energy topics
        - control_agent: Device control and automation
        - fallback_handler: General conversation handling (lightweight LLM)

    Args:
        checkpointer: Optional SQLite checkpointer for state persistence

    Returns:
        Compiled StateGraph ready for invocation
    """
    from agents.specialized import (
        create_analysis_agent,
        create_knowledge_agent,
        create_control_agent,
    )

    logger.info("Building multi-agent energy analysis graph")

    # Create the graph with our state schema
    graph = StateGraph(HEMAGraphState)

    # Create specialized agents
    analysis_agent = create_analysis_agent()
    knowledge_agent = create_knowledge_agent()
    control_agent = create_control_agent()

    # === Node Functions ===
    # Create node functions with agent dependencies
    classifier_node = create_classifier_node(analysis_agent, knowledge_agent, control_agent)
    analysis_agent_node = create_analysis_agent_node(analysis_agent)
    knowledge_agent_node = create_knowledge_agent_node(knowledge_agent)
    control_agent_node = create_control_agent_node(control_agent)

    # === Build the Graph ===

    # Add nodes
    graph.add_node("classifier", classifier_node)
    graph.add_node("clarification", clarification_node)
    graph.add_node("analysis_agent", analysis_agent_node)
    graph.add_node("knowledge_agent", knowledge_agent_node)
    graph.add_node("control_agent", control_agent_node)
    graph.add_node("fallback_handler", fallback_handler_node)

    # Set entry point
    graph.set_entry_point("classifier")

    # Add conditional edges from classifier
    graph.add_conditional_edges(
        "classifier",
        route_after_classification,
        {
            "clarification": "clarification",
            "analysis_agent": "analysis_agent",
            "knowledge_agent": "knowledge_agent",
            "control_agent": "control_agent",
            "fallback_handler": "fallback_handler",
        }
    )

    # All agents and clarification go to END
    graph.add_edge("analysis_agent", END)
    graph.add_edge("knowledge_agent", END)
    graph.add_edge("control_agent", END)
    graph.add_edge("fallback_handler", END)
    graph.add_edge("clarification", END)

    # Compile the graph
    if checkpointer:
        compiled = graph.compile(checkpointer=checkpointer)
        logger.info("Multi-agent graph compiled with checkpointer")
    else:
        compiled = graph.compile()
        logger.info("Multi-agent graph compiled without checkpointer")

    return compiled


# Legacy function for backwards compatibility
def build_energy_graph(checkpointer: Optional[MemorySaver] = None):
    """Legacy function - redirects to build_multi_agent_graph."""
    return build_multi_agent_graph(checkpointer)


# Re-export public symbols for backward compatibility
# Import these at the end to avoid circular imports
def __getattr__(name):
    """Lazy load runner exports to avoid circular imports."""
    if name == "HEMAGraphRunner":
        from .runner import HEMAGraphRunner
        return HEMAGraphRunner
    elif name == "get_default_checkpointer":
        from .runner import get_default_checkpointer
        return get_default_checkpointer
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "build_multi_agent_graph",
    "build_energy_graph",
    "HEMAGraphRunner",
    "get_default_checkpointer",
    "extract_tool_calls_from_messages",
    "_generate_conversation_summary",
]
