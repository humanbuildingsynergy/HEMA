# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# api/routes/chat.py
"""Chat endpoints for the energy analysis API."""
import json
import time
import traceback
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from api.schemas.chat import ChatRequest, ChatResponse, WorkflowStatus, StreamChunk
from api.dependencies import get_graph_runner
from agents.graph.builder import HEMAGraphRunner
from utils.logger import setup_logger
from utils.session_logger import get_session_logger

logger = setup_logger()
session_logger = get_session_logger()
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    runner: HEMAGraphRunner = Depends(get_graph_runner)
) -> ChatResponse:
    """
    Process a chat message and return the response.

    Args:
        request: Chat request with message and session_id
        runner: Graph runner instance (injected)

    Returns:
        ChatResponse with assistant response and workflow status
    """
    logger.info(f"Chat request for session {request.session_id}: {request.message[:50]}...")

    # Log the incoming request
    start_time = time.time()
    turn_number = session_logger.log_request(
        session_id=request.session_id,
        message=request.message,
        endpoint="/api/chat",
    )

    try:
        # Invoke the graph
        result = runner.invoke(request.message, session_id=request.session_id)

        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000

        # Log classification if available
        if result.get("target_agent") or result.get("query_type"):
            session_logger.log_classification(
                session_id=request.session_id,
                turn_number=turn_number,
                intent=result.get("query_type"),
                agent=result.get("target_agent"),
                vote_distribution=result.get("vote_distribution"),
                needs_clarification=result.get("needs_clarification", False),
                clarification_options=result.get("clarification_options"),
            )

        # Extract workflow status
        workflow_status = WorkflowStatus(
            data_loaded=result.get("data_loaded", False),
            analysis_completed=result.get("analysis_completed", False),
            workflow_step=result.get("workflow_step", "unknown"),
            energy_data_path=result.get("energy_data_path"),
            rate_data_path=result.get("rate_data_path"),
        )

        response_text = result.get("final_response", "No response generated")

        # Log the response
        session_logger.log_response(
            session_id=request.session_id,
            turn_number=turn_number,
            response=response_text,
            workflow_step=result.get("workflow_step", "unknown"),
            latency_ms=latency_ms,
            data_loaded=result.get("data_loaded", False),
            analysis_completed=result.get("analysis_completed", False),
            metadata={
                "query_type": result.get("query_type"),
                "target_agent": result.get("target_agent"),
            },
        )

        return ChatResponse(
            response=response_text,
            query_type=result.get("query_type", "unknown"),
            workflow_status=workflow_status,
            session_id=request.session_id,
            error=result.get("error"),
        )

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logger.error(f"Error processing chat: {str(e)}")

        # Log the error
        session_logger.log_error(
            session_id=request.session_id,
            turn_number=turn_number,
            error_type=type(e).__name__,
            error_message=str(e),
            stack_trace=traceback.format_exc(),
            context={"message": request.message},
        )

        return ChatResponse(
            response="I encountered an error processing your request.",
            query_type="error",
            workflow_status=WorkflowStatus(),
            session_id=request.session_id,
            error=str(e),
        )


@router.websocket("/ws/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: str,
    runner: HEMAGraphRunner = Depends(get_graph_runner)
):
    """
    WebSocket endpoint for real-time chat.

    Args:
        websocket: WebSocket connection
        session_id: Session identifier
        runner: Graph runner instance (injected)
    """
    await websocket.accept()
    logger.info(f"WebSocket connection opened for session {session_id}")

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")

            if not user_message:
                await websocket.send_json({
                    "error": "Empty message",
                    "done": True
                })
                continue

            logger.info(f"WebSocket message for session {session_id}: {user_message[:50]}...")

            # Log the incoming request
            start_time = time.time()
            turn_number = session_logger.log_request(
                session_id=session_id,
                message=user_message,
                endpoint="/api/chat/ws",
            )

            try:
                # Process the message
                result = runner.invoke(user_message, session_id=session_id)

                # Calculate latency
                latency_ms = (time.time() - start_time) * 1000

                # Log classification if available
                if result.get("target_agent") or result.get("query_type"):
                    session_logger.log_classification(
                        session_id=session_id,
                        turn_number=turn_number,
                        intent=result.get("query_type"),
                        agent=result.get("target_agent"),
                        vote_distribution=result.get("vote_distribution"),
                        needs_clarification=result.get("needs_clarification", False),
                    )

                response_text = result.get("final_response", "No response generated")

                # Log the response
                session_logger.log_response(
                    session_id=session_id,
                    turn_number=turn_number,
                    response=response_text,
                    workflow_step=result.get("workflow_step", "unknown"),
                    latency_ms=latency_ms,
                    data_loaded=result.get("data_loaded", False),
                    analysis_completed=result.get("analysis_completed", False),
                )

                # Send response
                await websocket.send_json({
                    "response": response_text,
                    "query_type": result.get("query_type", "unknown"),
                    "workflow_status": {
                        "data_loaded": result.get("data_loaded", False),
                        "analysis_completed": result.get("analysis_completed", False),
                        "workflow_step": result.get("workflow_step", "unknown"),
                    },
                    "done": True
                })

            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                logger.error(f"WebSocket processing error: {str(e)}")

                # Log the error
                session_logger.log_error(
                    session_id=session_id,
                    turn_number=turn_number,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    stack_trace=traceback.format_exc(),
                )

                await websocket.send_json({
                    "error": str(e),
                    "done": True
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket connection closed for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        try:
            await websocket.close()
        except Exception:
            pass
