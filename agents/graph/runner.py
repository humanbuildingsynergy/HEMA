# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/graph/runner.py
"""Graph runner for executing the multi-agent workflow."""
from typing import Optional

from langgraph.checkpoint.memory import MemorySaver

from utils.logger import setup_logger
from utils.token_tracking import get_token_tracker
from .state import get_initial_state

logger = setup_logger()


def get_default_checkpointer() -> MemorySaver:
    """
    Get the default in-memory checkpointer.

    Returns:
        MemorySaver instance for state persistence within the session
    """
    return MemorySaver()


class HEMAGraphRunner:
    """
    Runner class for the multi-agent HEMA graph.

    Provides a simplified interface for invoking the graph
    with session management.
    """

    def __init__(self, use_persistence: bool = True):
        """
        Initialize the graph runner.

        Args:
            use_persistence: Whether to use in-memory persistence for conversation continuity
        """
        if use_persistence:
            self.checkpointer = get_default_checkpointer()
        else:
            self.checkpointer = None

        # Import here to avoid circular imports
        from .builder import build_multi_agent_graph
        self.graph = build_multi_agent_graph(self.checkpointer)
        logger.info(f"HEMAGraphRunner initialized (persistence={use_persistence})")

    def invoke(
        self,
        user_query: str,
        session_id: str = "default",
        existing_state: Optional[dict] = None,
        clarification_response: Optional[str] = None
    ) -> dict:
        """
        Invoke the graph with a user query.

        Args:
            user_query: The user's query/message
            session_id: Session ID for conversation continuity
            existing_state: Optional existing state to build upon
            clarification_response: Optional user's clarification selection

        Returns:
            Final state after graph execution, including token usage metrics:
            - input_tokens: Total input tokens used
            - output_tokens: Total output tokens used
            - total_tokens: Combined token count
            - llm_call_count: Number of LLM calls made
        """
        # Reset token tracker before invocation to get fresh counts for this query
        token_tracker = get_token_tracker()
        token_tracker.reset()

        # Build input state
        if existing_state:
            input_state = {**existing_state, "user_query": user_query}
        else:
            input_state = get_initial_state(session_id)
            input_state["user_query"] = user_query

        # Handle clarification response
        if clarification_response:
            input_state["clarification_response"] = clarification_response

        # Configure with thread ID for persistence
        config = {"configurable": {"thread_id": session_id}}

        # Invoke the graph
        logger.info(f"Invoking graph for session {session_id}")
        result = self.graph.invoke(input_state, config=config)

        # Capture token usage from the tracker
        token_usage = token_tracker.get_usage()
        result["input_tokens"] = token_usage["input_tokens"]
        result["output_tokens"] = token_usage["output_tokens"]
        result["total_tokens"] = token_usage["total_tokens"]
        result["llm_call_count"] = token_usage["call_count"]

        logger.info(
            f"Graph invocation complete. Tokens: {token_usage['input_tokens']} in, "
            f"{token_usage['output_tokens']} out, {token_usage['call_count']} calls"
        )

        return result

    def get_response(self, user_query: str, session_id: str = "default") -> str:
        """
        Get just the response string from a query.

        Args:
            user_query: The user's query/message
            session_id: Session ID for conversation continuity

        Returns:
            The final response string
        """
        result = self.invoke(user_query, session_id)
        return result.get("final_response", "I couldn't generate a response.")

    def get_state(self, session_id: str = "default") -> Optional[dict]:
        """
        Get the current state for a session.

        Args:
            session_id: Session ID to retrieve state for

        Returns:
            Current state dict or None
        """
        if not self.checkpointer:
            return None

        config = {"configurable": {"thread_id": session_id}}
        try:
            state = self.graph.get_state(config)
            return state.values if state else None
        except Exception as e:
            logger.error(f"Error getting state: {str(e)}")
            return None

    def reset_session(self, session_id: str = "default") -> bool:
        """
        Reset a session's state.

        Args:
            session_id: Session ID to reset

        Returns:
            True if successful
        """
        # For now, just return True - proper reset would need checkpointer support
        logger.info(f"Session {session_id} reset requested")
        return True
