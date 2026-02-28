# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/graph/message_utils.py
"""Message utilities for graph operations."""
from typing import Optional, List
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage

from utils.logger import setup_logger

logger = setup_logger()


def extract_tool_calls_from_messages(messages: list, skip_first_n: int = 0) -> dict:
    """
    Extract tool call information from agent response messages.

    Args:
        messages: List of messages from agent execution
        skip_first_n: Number of messages to skip from the beginning (conversation history).
                      This ensures we only extract tool calls from the current turn,
                      not from previous conversation history.

    Returns:
        Dict with tool_calls list and tool usage statistics
    """
    tool_calls = []
    tool_counts = {}

    # Only process messages after the input history
    for msg in messages[skip_first_n:]:
        # Check AIMessage for tool_calls attribute
        if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_name = tc.get('name', 'unknown') if isinstance(tc, dict) else getattr(tc, 'name', 'unknown')
                tool_calls.append({
                    'name': tool_name,
                    'args': tc.get('args', {}) if isinstance(tc, dict) else getattr(tc, 'args', {}),
                })
                tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

        # Also check ToolMessage for tool name
        if isinstance(msg, ToolMessage):
            tool_name = getattr(msg, 'name', None)
            if tool_name:
                # Tool was executed (ToolMessage is the response)
                # We already counted in AIMessage, so just log
                logger.debug(f"Tool executed: {tool_name}")

    return {
        'tool_calls': tool_calls,
        'tool_counts': tool_counts,
        'total_tool_calls': len(tool_calls),
        'unique_tools': list(tool_counts.keys()),
    }


def _generate_conversation_summary(messages: List[BaseMessage], max_turns: int = 3) -> Optional[str]:
    """
    Generate a brief summary of recent conversation for classification context.

    Args:
        messages: List of conversation messages
        max_turns: Maximum number of recent turns to include (default 3)

    Returns:
        A string summary of recent conversation, or None if no messages
    """
    if not messages:
        return None

    # Get last N exchanges (user + assistant pairs)
    recent = messages[-(max_turns * 2):]
    if not recent:
        return None

    summary_parts = []
    for msg in recent:
        role = "User" if isinstance(msg, HumanMessage) else "Assistant"
        # Truncate long messages
        content = msg.content[:150] + "..." if len(msg.content) > 150 else msg.content
        summary_parts.append(f"{role}: {content}")

    return "Recent conversation:\n" + "\n".join(summary_parts)
