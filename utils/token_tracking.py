# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# utils/token_tracking.py
"""Token usage tracking for LLM calls using LangChain callbacks."""

from typing import Any, Dict, List, Optional
from threading import Lock
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult


class TokenUsageCallbackHandler(BaseCallbackHandler):
    """
    Callback handler that tracks token usage across LLM calls.

    Thread-safe implementation for tracking input/output tokens
    from OpenAI, Anthropic, and other LLM providers.
    """

    def __init__(self):
        super().__init__()
        self._lock = Lock()
        self.reset()

    def reset(self) -> None:
        """Reset all token counters."""
        with self._lock:
            self.total_input_tokens = 0
            self.total_output_tokens = 0
            self.total_tokens = 0
            self.call_count = 0
            self.per_call_usage: List[Dict[str, int]] = []

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Called when LLM call ends - extract token usage."""
        with self._lock:
            self.call_count += 1

            # Try to extract token usage from llm_output
            if response.llm_output:
                usage = response.llm_output.get("token_usage", {})
                if not usage:
                    # Try alternative key names
                    usage = response.llm_output.get("usage", {})

                input_tokens = usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0) or usage.get("output_tokens", 0)

                self.total_input_tokens += input_tokens
                self.total_output_tokens += output_tokens
                self.total_tokens = self.total_input_tokens + self.total_output_tokens

                self.per_call_usage.append({
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                })

            # Also try to extract from generations metadata
            for generation in response.generations:
                for gen in generation:
                    if hasattr(gen, 'generation_info') and gen.generation_info:
                        usage = gen.generation_info.get("usage", {})
                        if usage and not self.per_call_usage:
                            input_tokens = usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0)
                            output_tokens = usage.get("completion_tokens", 0) or usage.get("output_tokens", 0)

                            self.total_input_tokens += input_tokens
                            self.total_output_tokens += output_tokens
                            self.total_tokens = self.total_input_tokens + self.total_output_tokens

    def get_usage(self) -> Dict[str, int]:
        """Get current token usage statistics."""
        with self._lock:
            return {
                "input_tokens": self.total_input_tokens,
                "output_tokens": self.total_output_tokens,
                "total_tokens": self.total_tokens,
                "call_count": self.call_count,
            }

    def get_and_reset(self) -> Dict[str, int]:
        """Get current usage and reset counters."""
        usage = self.get_usage()
        self.reset()
        return usage


# Global token tracker for easy access
_global_token_tracker: Optional[TokenUsageCallbackHandler] = None
_tracker_lock = Lock()


def get_token_tracker() -> TokenUsageCallbackHandler:
    """Get or create the global token tracker."""
    global _global_token_tracker
    with _tracker_lock:
        if _global_token_tracker is None:
            _global_token_tracker = TokenUsageCallbackHandler()
        return _global_token_tracker


def reset_token_tracker() -> None:
    """Reset the global token tracker."""
    tracker = get_token_tracker()
    tracker.reset()


def get_token_usage() -> Dict[str, int]:
    """Get current token usage from global tracker."""
    tracker = get_token_tracker()
    return tracker.get_usage()


def get_and_reset_token_usage() -> Dict[str, int]:
    """Get current token usage and reset the tracker."""
    tracker = get_token_tracker()
    return tracker.get_and_reset()
