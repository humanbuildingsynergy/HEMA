# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/prompts/__init__.py
"""Agent system prompts - centralized location for all agent instructions."""

from ._common import ADAPTIVE_COMMUNICATION
from .analysis_prompt import ANALYSIS_AGENT_SYSTEM_PROMPT
from .control_prompt import CONTROL_AGENT_SYSTEM_PROMPT
from .knowledge_prompt import KNOWLEDGE_AGENT_SYSTEM_PROMPT
from .fallback_prompt import FALLBACK_HANDLER_PROMPT

__all__ = [
    "ADAPTIVE_COMMUNICATION",
    "ANALYSIS_AGENT_SYSTEM_PROMPT",
    "CONTROL_AGENT_SYSTEM_PROMPT",
    "KNOWLEDGE_AGENT_SYSTEM_PROMPT",
    "FALLBACK_HANDLER_PROMPT",
]
