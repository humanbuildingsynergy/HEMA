# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# api/schemas/chat.py
"""Pydantic models for chat endpoints."""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str = Field(..., description="User message to process")
    session_id: str = Field(default="default", description="Session identifier for conversation continuity")


class WorkflowStatus(BaseModel):
    """Current workflow status."""
    data_loaded: bool = False
    analysis_completed: bool = False
    workflow_step: str = "start"
    energy_data_path: Optional[str] = None
    rate_data_path: Optional[str] = None


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str = Field(..., description="Assistant response")
    query_type: str = Field(..., description="Classified query type")
    workflow_status: WorkflowStatus = Field(..., description="Current workflow status")
    session_id: str = Field(..., description="Session identifier")
    error: Optional[str] = Field(None, description="Error message if any")


class StreamChunk(BaseModel):
    """Model for streaming response chunks."""
    content: str
    done: bool = False
    error: Optional[str] = None
