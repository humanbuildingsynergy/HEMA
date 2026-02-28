# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/runners/conversation_monitor.py
"""
Conversation monitoring utilities for detecting loops, drift, and other issues.

Provides tools to detect problematic conversation patterns:
- Loop detection: Repetitive or near-duplicate messages
- Drift detection: Conversation straying from the scenario goal
- Early termination signals
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
from difflib import SequenceMatcher


@dataclass
class MonitoringResult:
    """Result from conversation monitoring checks."""
    should_terminate: bool
    reason: Optional[str]
    warning: Optional[str]
    loop_detected: bool
    drift_score: float  # 0.0 = on topic, 1.0 = completely off topic
    consecutive_similar: int  # Number of consecutive similar messages


class ConversationMonitor:
    """
    Monitors conversation health and detects problematic patterns.

    Checks for:
    1. Message loops (user repeating similar messages)
    2. Topic drift (conversation straying from goal)
    3. Stalled conversations (no progress being made)
    """

    def __init__(
        self,
        similarity_threshold: float = 0.75,
        max_consecutive_similar: int = 3,
        drift_threshold: float = 0.7,
        drift_window: int = 5,
    ):
        """
        Initialize the conversation monitor.

        Args:
            similarity_threshold: Jaccard similarity above which messages are considered duplicates (0-1)
            max_consecutive_similar: Number of consecutive similar messages before termination
            drift_threshold: Drift score above which to warn about topic drift (0-1)
            drift_window: Number of recent turns to consider for drift detection
        """
        self.similarity_threshold = similarity_threshold
        self.max_consecutive_similar = max_consecutive_similar
        self.drift_threshold = drift_threshold
        self.drift_window = drift_window

        # State tracking
        self.user_messages: List[str] = []
        self.consecutive_similar_count = 0
        self.last_similarity = 0.0

    def check_message(
        self,
        message: str,
        speaker: str,
        scenario_goal: Optional[str] = None,
        scenario_keywords: Optional[List[str]] = None,
    ) -> MonitoringResult:
        """
        Check a new message for problematic patterns.

        Args:
            message: The message to check
            speaker: "user" or "system"
            scenario_goal: The scenario's primary goal (for drift detection)
            scenario_keywords: Keywords related to the scenario topic

        Returns:
            MonitoringResult with analysis
        """
        should_terminate = False
        reason = None
        warning = None
        loop_detected = False
        drift_score = 0.0

        if speaker == "user":
            # Check for loops (user repeating themselves)
            if self.user_messages:
                similarity = self._calculate_similarity(message, self.user_messages[-1])
                self.last_similarity = similarity

                if similarity >= self.similarity_threshold:
                    self.consecutive_similar_count += 1
                    loop_detected = True

                    if self.consecutive_similar_count >= self.max_consecutive_similar:
                        should_terminate = True
                        reason = f"loop_detected: {self.consecutive_similar_count} consecutive similar messages"
                    else:
                        warning = f"Possible loop: {self.consecutive_similar_count} similar messages in a row"
                else:
                    self.consecutive_similar_count = 0

            # Check for topic drift
            if scenario_keywords:
                drift_score = self._calculate_drift(message, scenario_keywords)

                # Check drift across recent messages
                if len(self.user_messages) >= self.drift_window:
                    recent_messages = self.user_messages[-self.drift_window:] + [message]
                    avg_drift = sum(
                        self._calculate_drift(m, scenario_keywords)
                        for m in recent_messages
                    ) / len(recent_messages)

                    if avg_drift >= self.drift_threshold and not warning:
                        warning = f"Topic drift detected: conversation may be off-topic (drift={avg_drift:.2f})"

            # Record this message
            self.user_messages.append(message)

        return MonitoringResult(
            should_terminate=should_terminate,
            reason=reason,
            warning=warning,
            loop_detected=loop_detected,
            drift_score=drift_score,
            consecutive_similar=self.consecutive_similar_count,
        )

    def _calculate_similarity(self, msg1: str, msg2: str) -> float:
        """
        Calculate similarity between two messages using Jaccard similarity.

        Returns a value between 0 (completely different) and 1 (identical).
        """
        # Normalize messages
        words1 = set(self._normalize(msg1).split())
        words2 = set(self._normalize(msg2).split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0

    def _calculate_drift(self, message: str, keywords: List[str]) -> float:
        """
        Calculate how far a message has drifted from the topic keywords.

        Returns 0.0 if on-topic, 1.0 if completely off-topic.
        """
        msg_lower = self._normalize(message)
        msg_words = set(msg_lower.split())

        # Check how many keywords appear in the message
        keyword_matches = sum(
            1 for kw in keywords
            if kw.lower() in msg_lower or any(kw.lower() in w for w in msg_words)
        )

        if not keywords:
            return 0.0

        # Higher score = more drift (fewer keyword matches)
        relevance = keyword_matches / len(keywords)
        drift = 1.0 - min(relevance * 2, 1.0)  # Scale so 50% keywords = 0 drift

        return drift

    def _normalize(self, text: str) -> str:
        """Normalize text for comparison."""
        # Lowercase and remove punctuation
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def reset(self) -> None:
        """Reset the monitor state for a new conversation."""
        self.user_messages = []
        self.consecutive_similar_count = 0
        self.last_similarity = 0.0

    def get_stats(self) -> dict:
        """Get monitoring statistics."""
        return {
            "total_user_messages": len(self.user_messages),
            "consecutive_similar": self.consecutive_similar_count,
            "last_similarity": self.last_similarity,
        }


def extract_scenario_keywords(scenario) -> List[str]:
    """
    Extract relevant keywords from a scenario for drift detection.

    Args:
        scenario: A Scenario object

    Returns:
        List of keywords related to the scenario topic
    """
    keywords = set()

    # Extract from scenario name and description
    text = f"{scenario.name} {scenario.description} {scenario.primary_goal}"

    # Common energy-related terms to look for
    energy_terms = {
        "energy", "electricity", "power", "consumption", "usage", "kwh", "watt",
        "bill", "cost", "rate", "tou", "peak", "off-peak", "tier",
        "appliance", "hvac", "ac", "heating", "cooling", "thermostat",
        "solar", "panel", "generation", "battery", "ev", "charger",
        "efficiency", "save", "saving", "reduce", "optimize",
        "utility", "grid", "meter", "smart",
        "rebate", "incentive", "upgrade",
    }

    # Find energy terms in the scenario text
    text_lower = text.lower()
    for term in energy_terms:
        if term in text_lower:
            keywords.add(term)

    # Extract specific appliances mentioned
    appliance_pattern = r'\b(hvac|ac|air conditioner|heater|water heater|refrigerator|washer|dryer|dishwasher|pool pump|ev charger)\b'
    for match in re.finditer(appliance_pattern, text_lower):
        keywords.add(match.group(1))

    # Add scenario-specific terms
    if "rate" in scenario.id or "utility" in scenario.id:
        keywords.update(["rate", "tier", "peak", "pricing", "cost"])
    if "solar" in scenario.id:
        keywords.update(["solar", "panel", "generation", "sun"])
    if "hvac" in scenario.id or "heating" in scenario.id or "cooling" in scenario.id:
        keywords.update(["hvac", "temperature", "thermostat", "heating", "cooling"])
    if "appliance" in scenario.id:
        keywords.update(["appliance", "device", "equipment"])
    if "bill" in scenario.id or "spike" in scenario.id:
        keywords.update(["bill", "increase", "spike", "cost", "charge"])
    if "comparison" in scenario.id or "compare" in scenario.id:
        keywords.update(["compare", "comparison", "difference", "change", "month", "week"])

    return list(keywords)
