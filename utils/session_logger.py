# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# utils/session_logger.py
"""
Session Replay Logger for HEMA system.

Logs all interactions in JSONL format for debugging and analysis.
Each session gets its own log file per day.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

# Default log directory
DEFAULT_LOG_DIR = "logs/session_replay"


class SessionLogger:
    """
    Logs session interactions to JSONL files.

    Thread-safe logging with automatic file rotation by session and date.
    """

    _instance: Optional["SessionLogger"] = None
    _lock = Lock()

    def __new__(cls, log_dir: str = DEFAULT_LOG_DIR):
        """Singleton pattern for global logger access."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, log_dir: str = DEFAULT_LOG_DIR):
        """Initialize the session logger."""
        if self._initialized:
            return

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._file_handles: Dict[str, Any] = {}
        self._turn_counts: Dict[str, int] = {}
        self._write_lock = Lock()
        self._initialized = True

    def _get_log_file(self, session_id: str) -> Path:
        """Get the log file path for a session."""
        date_str = datetime.now().strftime("%Y%m%d")
        return self.log_dir / f"session_{session_id}_{date_str}.jsonl"

    def _write_entry(self, session_id: str, entry: Dict[str, Any]) -> None:
        """Write a log entry to the session's log file."""
        with self._write_lock:
            log_file = self._get_log_file(session_id)
            with open(log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")

    def _get_turn_number(self, session_id: str) -> int:
        """Get and increment the turn number for a session."""
        if session_id not in self._turn_counts:
            self._turn_counts[session_id] = 0
        self._turn_counts[session_id] += 1
        return self._turn_counts[session_id]

    def log_request(
        self,
        session_id: str,
        message: str,
        endpoint: str = "/api/chat",
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Log an incoming request.

        Args:
            session_id: Session identifier
            message: User's message
            endpoint: API endpoint called
            metadata: Additional metadata

        Returns:
            Turn number for this interaction
        """
        turn_number = self._get_turn_number(session_id)

        entry = {
            "type": "request",
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "turn_number": turn_number,
            "request": {
                "message": message,
                "endpoint": endpoint,
                "message_length": len(message),
            },
            "metadata": metadata or {},
        }

        self._write_entry(session_id, entry)
        return turn_number

    def log_classification(
        self,
        session_id: str,
        turn_number: int,
        intent: Optional[str],
        agent: Optional[str],
        vote_distribution: Optional[Dict[str, int]] = None,
        needs_clarification: bool = False,
        clarification_options: Optional[List[Dict[str, str]]] = None,
        reasoning: Optional[str] = None,
    ) -> None:
        """
        Log a classification decision.

        Args:
            session_id: Session identifier
            turn_number: Turn number from log_request
            intent: Classified intent
            agent: Target agent
            vote_distribution: Votes per agent from self-consistency
            needs_clarification: Whether clarification was needed
            clarification_options: Options presented to user
            reasoning: Classification reasoning
        """
        entry = {
            "type": "classification",
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "turn_number": turn_number,
            "classification": {
                "intent": intent,
                "agent": agent,
                "vote_distribution": vote_distribution,
                "needs_clarification": needs_clarification,
                "clarification_options": clarification_options,
                "reasoning": reasoning,
            },
        }

        self._write_entry(session_id, entry)

    def log_response(
        self,
        session_id: str,
        turn_number: int,
        response: str,
        workflow_step: str,
        latency_ms: float,
        data_loaded: bool = False,
        analysis_completed: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log a response.

        Args:
            session_id: Session identifier
            turn_number: Turn number from log_request
            response: System response
            workflow_step: Current workflow step
            latency_ms: Processing time in milliseconds
            data_loaded: Whether data is loaded
            analysis_completed: Whether analysis is complete
            metadata: Additional metadata
        """
        entry = {
            "type": "response",
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "turn_number": turn_number,
            "response": {
                "content": response,
                "content_length": len(response),
                "workflow_step": workflow_step,
                "latency_ms": round(latency_ms, 2),
                "data_loaded": data_loaded,
                "analysis_completed": analysis_completed,
            },
            "metadata": metadata or {},
        }

        self._write_entry(session_id, entry)

    def log_error(
        self,
        session_id: str,
        turn_number: int,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log an error.

        Args:
            session_id: Session identifier
            turn_number: Turn number from log_request
            error_type: Type of error
            error_message: Error message
            stack_trace: Full stack trace
            context: Additional context
        """
        entry = {
            "type": "error",
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "turn_number": turn_number,
            "error": {
                "type": error_type,
                "message": error_message,
                "stack_trace": stack_trace,
            },
            "context": context or {},
        }

        self._write_entry(session_id, entry)

    def reset_session(self, session_id: str) -> None:
        """Reset the turn counter for a session."""
        if session_id in self._turn_counts:
            del self._turn_counts[session_id]


# Global logger instance
_logger: Optional[SessionLogger] = None


def get_session_logger(log_dir: str = DEFAULT_LOG_DIR) -> SessionLogger:
    """Get the global session logger instance."""
    global _logger
    if _logger is None:
        _logger = SessionLogger(log_dir)
    return _logger


def log_interaction(
    session_id: str,
    message: str,
    response: str,
    classification: Optional[Dict[str, Any]] = None,
    latency_ms: float = 0,
    error: Optional[str] = None,
    **kwargs
) -> None:
    """
    Convenience function to log a complete interaction.

    Args:
        session_id: Session identifier
        message: User message
        response: System response
        classification: Classification details
        latency_ms: Processing time
        error: Error message if any
        **kwargs: Additional fields
    """
    logger = get_session_logger()
    turn_number = logger.log_request(session_id, message)

    if classification:
        logger.log_classification(
            session_id=session_id,
            turn_number=turn_number,
            scope=classification.get("scope"),
            intent=classification.get("intent"),
            agent=classification.get("agent"),
            vote_distribution=classification.get("vote_distribution"),
            needs_clarification=classification.get("needs_clarification", False),
        )

    if error:
        logger.log_error(
            session_id=session_id,
            turn_number=turn_number,
            error_type="processing_error",
            error_message=error,
        )

    logger.log_response(
        session_id=session_id,
        turn_number=turn_number,
        response=response,
        workflow_step=kwargs.get("workflow_step", "unknown"),
        latency_ms=latency_ms,
        data_loaded=kwargs.get("data_loaded", False),
        analysis_completed=kwargs.get("analysis_completed", False),
    )
