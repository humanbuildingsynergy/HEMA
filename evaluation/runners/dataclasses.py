# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/runners/dataclasses.py
"""Shared dataclasses for conversation recording (HEMA and vanilla)."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class ConversationTurn:
    """A single turn in a conversation (HEMA or vanilla)."""

    turn_number: int
    speaker: str  # "user" or "system"
    message: str
    timestamp: float
    latency_ms: float = 0.0
    had_error: bool = False
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    metadata: dict = field(default_factory=dict)

    # HEMA-specific fields (None/empty for vanilla)
    agent_used: Optional[str] = None
    tools_called: List[str] = field(default_factory=list)
    classification_result: Optional[Dict] = None


@dataclass
class ConversationRecord:
    """Complete record of a conversation."""

    persona_id: str
    scenario_id: str
    system_type: str  # "hema", "vanilla", "vanilla_structured", etc.
    start_time: datetime
    end_time: Optional[datetime]
    turns: List[ConversationTurn]
    goal_signaled: bool
    terminated_reason: str  # "goal_met", "max_turns", "error", "loop_detected"
    total_duration_seconds: float
