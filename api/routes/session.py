# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# api/routes/session.py
"""Session management endpoints for the energy analysis API."""
from fastapi import APIRouter, Depends, HTTPException

from api.schemas.session import SessionInfo, SessionHistory, SessionResetResponse, MessageEntry
from api.dependencies import get_graph_runner
from agents.graph.builder import HEMAGraphRunner
from utils.logger import setup_logger

logger = setup_logger()
router = APIRouter(prefix="/session", tags=["session"])


@router.get("/{session_id}", response_model=SessionInfo)
async def get_session_info(
    session_id: str,
    runner: HEMAGraphRunner = Depends(get_graph_runner)
) -> SessionInfo:
    """
    Get information about a session.

    Args:
        session_id: Session identifier
        runner: Graph runner instance (injected)

    Returns:
        SessionInfo with current session state
    """
    logger.info(f"Getting session info for {session_id}")

    state = runner.get_state(session_id)

    if state is None:
        # Return empty session info for non-existent sessions
        return SessionInfo(session_id=session_id)

    return SessionInfo(
        session_id=session_id,
        data_loaded=state.get("data_loaded", False),
        analysis_completed=state.get("analysis_completed", False),
        workflow_step=state.get("workflow_step", "start"),
        energy_data_path=state.get("energy_data_path"),
        rate_data_path=state.get("rate_data_path"),
        user_profile=state.get("user_profile", {}),
    )


@router.get("/{session_id}/history", response_model=SessionHistory)
async def get_session_history(
    session_id: str,
    runner: HEMAGraphRunner = Depends(get_graph_runner)
) -> SessionHistory:
    """
    Get conversation history for a session.

    Args:
        session_id: Session identifier
        runner: Graph runner instance (injected)

    Returns:
        SessionHistory with list of messages
    """
    logger.info(f"Getting session history for {session_id}")

    state = runner.get_state(session_id)

    if state is None:
        return SessionHistory(session_id=session_id, messages=[], total_messages=0)

    # Convert messages to MessageEntry format
    messages = []
    raw_messages = state.get("messages", [])

    for msg in raw_messages:
        if hasattr(msg, "type") and hasattr(msg, "content"):
            role = "user" if msg.type == "human" else "assistant"
            messages.append(MessageEntry(role=role, content=msg.content))

    return SessionHistory(
        session_id=session_id,
        messages=messages,
        total_messages=len(messages)
    )


@router.get("/{session_id}/profile")
async def get_user_profile(
    session_id: str,
    runner: HEMAGraphRunner = Depends(get_graph_runner)
) -> dict:
    """
    Get the user profile for a session.

    Args:
        session_id: Session identifier
        runner: Graph runner instance (injected)

    Returns:
        User profile dictionary
    """
    logger.info(f"Getting user profile for session {session_id}")

    state = runner.get_state(session_id)

    if state is None:
        return {"session_id": session_id, "profile": {}}

    return {
        "session_id": session_id,
        "profile": state.get("user_profile", {})
    }


@router.delete("/{session_id}", response_model=SessionResetResponse)
async def reset_session(
    session_id: str,
    runner: HEMAGraphRunner = Depends(get_graph_runner)
) -> SessionResetResponse:
    """
    Reset a session's state.

    Args:
        session_id: Session identifier
        runner: Graph runner instance (injected)

    Returns:
        SessionResetResponse indicating success
    """
    logger.info(f"Resetting session {session_id}")

    try:
        success = runner.reset_session(session_id)
        return SessionResetResponse(
            session_id=session_id,
            success=success,
            message="Session reset successfully" if success else "Session reset may not have completed"
        )
    except Exception as e:
        logger.error(f"Error resetting session: {str(e)}")
        return SessionResetResponse(
            session_id=session_id,
            success=False,
            message=f"Error resetting session: {str(e)}"
        )
