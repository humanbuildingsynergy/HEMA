# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/graph/state.py
"""State schema for the LangGraph energy analysis system."""
from typing import TypedDict, Annotated, Optional, List, Dict, Any
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


def merge_dicts(left: Dict, right: Dict) -> Dict:
    """Reducer for merging dictionaries."""
    if left is None:
        return right or {}
    if right is None:
        return left
    return {**left, **right}


def update_or_keep(left: Any, right: Any) -> Any:
    """Reducer that updates if right is not None."""
    return right if right is not None else left


def accumulate_list(left: List, right: List) -> List:
    """Reducer that accumulates lists."""
    if left is None:
        return right or []
    if right is None:
        return left
    return left + right


def accumulate_count(left: int, right: int) -> int:
    """Reducer that accumulates counts."""
    return (left or 0) + (right or 0)


class UserProfile(TypedDict, total=False):
    """User profile structure for personalization."""
    technical_level: str  # beginner, intermediate, expert
    communication_style: str  # detailed, balanced, concise
    priorities: Dict[str, float]  # cost_savings, environmental, comfort, convenience
    constraints: Dict[str, str]  # schedule_flexibility, budget_flexibility
    preferences: Dict[str, str]  # explanation_depth, recommendation_count
    interaction_history: List[Dict[str, Any]]
    created: str  # ISO timestamp
    last_updated: str  # ISO timestamp
    interaction_count: int


class AnalysisResults(TypedDict, total=False):
    """Energy analysis results structure."""
    consumption_analysis: Dict[str, Any]
    appliance_analysis: Dict[str, Any]
    tou_analysis: Dict[str, Any]
    pattern_analysis: str  # LLM-enhanced analysis narrative


class HEMAGraphState(TypedDict):
    """
    Main state schema for the LangGraph HEMA (Home Energy Management Assistant) system.

    Uses Annotated types with reducers for proper state updates
    in multi-step graph execution.
    """
    # Conversation state
    messages: Annotated[List[BaseMessage], add_messages]

    # User query classification
    query_type: Annotated[str, update_or_keep]  # "data_load", "analysis", "recommendation", "help", "general", "knowledge", "control"
    target_agent: Annotated[str, update_or_keep]  # "analysis_agent", "knowledge_agent", "control_agent", "fallback_handler"
    user_query: Annotated[str, update_or_keep]

    # Data state
    data_loaded: Annotated[bool, lambda left, right: right if right is not None else left]
    energy_data_path: Annotated[Optional[str], update_or_keep]
    rate_data_path: Annotated[Optional[str], update_or_keep]
    load_timestamp: Annotated[Optional[str], update_or_keep]  # ISO format

    # Raw loaded data (stored as serializable dict format)
    energy_data: Annotated[Optional[Dict[str, Any]], update_or_keep]  # DataFrame.to_dict()
    rate_data: Annotated[Optional[Dict[str, Any]], update_or_keep]
    data_metadata: Annotated[Dict[str, Any], merge_dicts]

    # Processed data state
    processed_data: Annotated[Optional[Dict[str, Any]], update_or_keep]  # Feature-engineered DataFrame

    # Analysis state
    analysis_completed: Annotated[bool, lambda left, right: right if right is not None else left]
    analysis_results: Annotated[Optional[Dict[str, Any]], update_or_keep]
    analysis_timestamp: Annotated[Optional[str], update_or_keep]

    # Personalization state
    user_profile: Annotated[Dict[str, Any], merge_dicts]
    prompt_analysis: Annotated[Optional[Dict[str, Any]], update_or_keep]

    # Response state
    final_response: Annotated[Optional[str], update_or_keep]

    # Error handling
    error: Annotated[Optional[str], update_or_keep]

    # Session metadata
    session_id: Annotated[Optional[str], update_or_keep]
    workflow_step: Annotated[str, update_or_keep]  # Current step for tracking

    # Clarification state (for self-consistency classifier)
    needs_clarification: Annotated[bool, lambda left, right: right if right is not None else left]
    clarification_options: Annotated[Optional[List[Dict[str, str]]], update_or_keep]
    clarification_response: Annotated[Optional[str], update_or_keep]  # User's selection
    classification_results: Annotated[Optional[List[Any]], update_or_keep]  # Raw results for resolution

    # Classification details (for logging)
    vote_distribution: Annotated[Optional[Dict[str, int]], update_or_keep]  # Votes per agent
    personalization_intent: Annotated[Optional[str], update_or_keep]  # personal/general/ambiguous
    personalization_distribution: Annotated[Optional[Dict[str, int]], update_or_keep]  # Votes per personalization intent

    # Tool tracking (for metrics)
    tool_calls: Annotated[List[Dict[str, Any]], accumulate_list]  # List of all tool calls
    tools_used: Annotated[List[str], accumulate_list]  # Unique tools used (accumulated)
    tool_call_count: Annotated[int, accumulate_count]  # Total tool invocations
    tool_distribution: Annotated[Dict[str, int], merge_dicts]  # Tool name -> count


def get_initial_state(session_id: Optional[str] = None) -> HEMAGraphState:
    """Create initial state with default values."""
    return {
        "messages": [],
        "query_type": "",
        "target_agent": "",
        "user_query": "",
        "data_loaded": False,
        "energy_data_path": None,
        "rate_data_path": None,
        "load_timestamp": None,
        "energy_data": None,
        "rate_data": None,
        "data_metadata": {},
        "processed_data": None,
        "analysis_completed": False,
        "analysis_results": None,
        "analysis_timestamp": None,
        "user_profile": {},
        "prompt_analysis": None,
        "final_response": None,
        "error": None,
        "session_id": session_id,
        "workflow_step": "start",
        # Clarification state
        "needs_clarification": False,
        "clarification_options": None,
        "clarification_response": None,
        "classification_results": None,
        # Classification details
        "vote_distribution": None,
        "personalization_intent": None,
        "personalization_distribution": None,
        # Tool tracking
        "tool_calls": [],
        "tools_used": [],
        "tool_call_count": 0,
        "tool_distribution": {},
    }
