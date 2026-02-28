# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# api/schemas/session.py
"""Pydantic models for session endpoints."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class SessionInfo(BaseModel):
    """Session information model."""
    session_id: str
    data_loaded: bool = False
    analysis_completed: bool = False
    workflow_step: str = "start"
    energy_data_path: Optional[str] = None
    rate_data_path: Optional[str] = None
    user_profile: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
    last_updated: Optional[str] = None


class MessageEntry(BaseModel):
    """Single message in conversation history."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None


class SessionHistory(BaseModel):
    """Conversation history for a session."""
    session_id: str
    messages: List[MessageEntry] = Field(default_factory=list)
    total_messages: int = 0


class SessionResetResponse(BaseModel):
    """Response for session reset."""
    session_id: str
    success: bool
    message: str
