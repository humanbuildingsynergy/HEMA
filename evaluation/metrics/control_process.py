# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/metrics/control_process.py
"""Control process metrics for evaluating Control Agent behavior.

Evaluates HOW the agent approaches control tasks:
- Information gathering before action
- Action confirmation to user
- Action explanation quality
- Constraint compliance
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


# Tools that gather information (should be called before control actions)
INFO_GATHERING_TOOLS = {
    "get_device_status",
    "get_device_list",
    "get_utility_rate",
    "get_device_energy",
    "get_all_devices_energy",
    "get_available_actions",
    "get_automation_rules",
}

# Tools that perform control actions
CONTROL_ACTION_TOOLS = {
    "control_device",
    "schedule_device_action",
}


@dataclass
class ControlProcessMetrics:
    """Metrics evaluating the Control Agent's process (Table 1 only).

    Only includes metrics from manuscript Table 1:
    - Information-before-action rate
    - Action confirmation rate
    - Action explanation rate
    """

    # Information gathering before action (Table 1)
    info_before_action_rate: float = 0.0  # Fraction of control actions preceded by info gathering
    info_before_action_details: List[Dict[str, Any]] = field(default_factory=list)  # For debugging
    info_tools_called: int = 0  # Count of info-gathering tool calls
    control_tools_called: int = 0  # Count of control-action tool calls

    # Action confirmation (Table 1)
    action_confirmation_rate: float = 0.0  # Fraction of actions followed by confirmation
    confirmation_details: List[str] = field(default_factory=list)  # For debugging

    # Action explanation (Table 1)
    action_explanation_rate: float = 0.0  # Fraction of actions with explanation of why
    explanation_details: List[str] = field(default_factory=list)  # For debugging

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization (Table 1 metrics only)."""
        return {
            "information_before_action_rate": round(self.info_before_action_rate, 2),
            "action_confirmation_rate": round(self.action_confirmation_rate, 2),
            "action_explanation_rate": round(self.action_explanation_rate, 2),
            # Debugging details
            "info_before_action_details": self.info_before_action_details,
            "confirmation_details": self.confirmation_details,
            "explanation_details": self.explanation_details,
        }


def compute_info_before_action_rate(
    turn_details: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Compute the rate at which information-gathering tools were called before control actions.

    A good Control Agent should gather information (device status, rates, etc.)
    before executing control actions.

    Args:
        turn_details: List of turn metrics from the experiment, each containing
                     'tools_called' list.

    Returns:
        Dict with:
        - info_before_action_rate: float (0-1)
        - info_tools_called: int
        - control_tools_called: int
        - details: List of analysis per control action
    """
    # Flatten all tool calls in order
    all_tool_calls = []
    for turn in turn_details:
        tools = turn.get("tools_called", [])
        if tools:
            all_tool_calls.extend(tools)

    # Track which info tools have been called so far
    info_tools_seen = set()
    control_actions_with_info = 0
    control_actions_without_info = 0
    details = []

    info_count = 0
    control_count = 0

    for tool in all_tool_calls:
        # Normalize tool name (sometimes includes parameters)
        tool_name = tool.split("(")[0].strip() if "(" in tool else tool

        if tool_name in INFO_GATHERING_TOOLS:
            info_tools_seen.add(tool_name)
            info_count += 1

        elif tool_name in CONTROL_ACTION_TOOLS:
            control_count += 1

            if info_tools_seen:
                # Control action was preceded by at least one info tool
                control_actions_with_info += 1
                details.append({
                    "action": tool_name,
                    "had_info_first": True,
                    "info_tools_used": list(info_tools_seen),
                })
            else:
                # Control action without prior info gathering
                control_actions_without_info += 1
                details.append({
                    "action": tool_name,
                    "had_info_first": False,
                    "info_tools_used": [],
                })

    total_control_actions = control_actions_with_info + control_actions_without_info
    rate = control_actions_with_info / total_control_actions if total_control_actions > 0 else 0.0

    return {
        "info_before_action_rate": rate,
        "info_tools_called": info_count,
        "control_tools_called": control_count,
        "control_actions_with_info": control_actions_with_info,
        "control_actions_without_info": control_actions_without_info,
        "details": details,
    }


def compute_tool_call_efficiency(
    turn_details: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Compute tool call efficiency metrics.

    Measures:
    - Total tool calls
    - Unique tools used
    - Redundant calls (same tool called multiple times)

    Args:
        turn_details: List of turn metrics from the experiment.

    Returns:
        Dict with efficiency metrics.
    """
    all_tool_calls = []
    for turn in turn_details:
        tools = turn.get("tools_called", [])
        if tools:
            all_tool_calls.extend(tools)

    # Count occurrences of each tool
    tool_counts: Dict[str, int] = {}
    for tool in all_tool_calls:
        tool_name = tool.split("(")[0].strip() if "(" in tool else tool
        tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

    total_calls = len(all_tool_calls)
    unique_tools = len(tool_counts)

    # Redundant calls: calls beyond the first for each tool
    # (This is a simple heuristic - some redundant calls may be intentional)
    redundant = sum(max(0, count - 1) for count in tool_counts.values())

    return {
        "total_tool_calls": total_calls,
        "unique_tools_used": unique_tools,
        "redundant_tool_calls": redundant,
        "tool_call_distribution": tool_counts,
    }


def compute_control_process_metrics(
    turn_details: List[Dict[str, Any]],
    semantic_metrics: Optional[Dict[str, Any]] = None,
) -> ControlProcessMetrics:
    """
    Compute Table 1 control process metrics.

    Args:
        turn_details: List of turn metrics from the experiment.
        semantic_metrics: Optional dict with semantic extraction results
                         (action_confirmations, action_explanations).

    Returns:
        ControlProcessMetrics object with Table 1 metrics only.
    """
    # Compute info-before-action rate
    info_metrics = compute_info_before_action_rate(turn_details)

    # Extract semantic metrics if provided
    confirmations = semantic_metrics.get("action_confirmations", []) if semantic_metrics else []
    explanations = semantic_metrics.get("action_explanations", []) if semantic_metrics else []

    # Calculate confirmation/explanation rates based on control actions
    control_actions = info_metrics["control_tools_called"]

    confirmation_rate = len(confirmations) / control_actions if control_actions > 0 else 0.0
    explanation_rate = len(explanations) / control_actions if control_actions > 0 else 0.0

    return ControlProcessMetrics(
        info_before_action_rate=info_metrics["info_before_action_rate"],
        info_before_action_details=info_metrics["details"],
        info_tools_called=info_metrics["info_tools_called"],
        control_tools_called=info_metrics["control_tools_called"],
        action_confirmation_rate=min(confirmation_rate, 1.0),  # Cap at 1.0
        confirmation_details=confirmations,
        action_explanation_rate=min(explanation_rate, 1.0),  # Cap at 1.0
        explanation_details=explanations,
    )
