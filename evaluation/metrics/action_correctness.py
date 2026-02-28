# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/metrics/action_correctness.py
"""Action correctness evaluation for device control operations.

Evaluates whether device control actions were appropriate for energy optimization,
including schedule timing (peak vs off-peak), temperature settings, power actions,
mode changes, and speed settings.
"""

from typing import Dict, List, Optional, Any

from .action_result import ActionCorrectnessResult
from .action_constants import DEVICE_CONSTRAINTS
from .action_helpers import (
    evaluate_constraint_compliance,
    _evaluate_schedule_action,
    _evaluate_temperature_action,
    _evaluate_power_action,
    _evaluate_mode_action,
    _evaluate_speed_action,
)

# Re-export constants for backward compatibility
from .action_constants import (
    EFFICIENT_TEMP_RANGES,
    POOL_PUMP_SPEED_RANGES,
    HVAC_MODE_GUIDELINES,
    WATER_HEATER_MODE_EFFICIENCY,
)

__all__ = [
    "ActionCorrectnessResult",
    "evaluate_action_correctness",
    "EFFICIENT_TEMP_RANGES",
    "POOL_PUMP_SPEED_RANGES",
    "HVAC_MODE_GUIDELINES",
    "WATER_HEATER_MODE_EFFICIENCY",
    "DEVICE_CONSTRAINTS",
]


def evaluate_action_correctness(
    device_state_changes: Optional[Dict[str, Any]],
    device_state_after: Optional[Dict[str, Any]] = None,
) -> Optional[ActionCorrectnessResult]:
    """
    Evaluate whether device control actions were appropriate for energy optimization.

    Evaluates:
    - Schedule timing (off-peak vs peak)
    - Temperature settings (efficient ranges)
    - Power actions (on/off appropriateness)
    - Mode changes (HVAC season, water heater efficiency)
    - Speed settings (pool pump efficiency)

    Args:
        device_state_changes: Changes captured during experiment
        device_state_after: Final device state snapshot

    Returns:
        ActionCorrectnessResult or None if no actions to evaluate
    """
    if not device_state_changes:
        return None

    changes_by_device = device_state_changes.get("changes_by_device", {})
    if not changes_by_device:
        return None

    action_details = []
    schedule_evaluations = []
    temp_evaluations = []
    mode_evaluations = []
    power_evaluations = []
    speed_evaluations = []

    for device_key, device_changes in changes_by_device.items():
        state_changes = device_changes.get("state_changes", {})

        # Try to determine device type from the after snapshot
        device_type = "unknown"
        if device_state_after:
            device_info = device_state_after.get("devices", {}).get(device_key, {})
            device_type = device_info.get("device_type", "unknown")

        # Evaluate scheduled_time changes
        if "scheduled_time" in state_changes:
            scheduled_time = state_changes["scheduled_time"].get("after")
            scheduled_action = state_changes.get("scheduled_action", {}).get("after")
            if scheduled_time:
                eval_result = _evaluate_schedule_action(
                    device_key, scheduled_time, scheduled_action
                )
                action_details.append(eval_result)
                schedule_evaluations.append(eval_result["is_optimal"])

        # Evaluate scheduled_start_time changes (alternate key)
        if "scheduled_start_time" in state_changes:
            scheduled_time = state_changes["scheduled_start_time"].get("after")
            if scheduled_time:
                eval_result = _evaluate_schedule_action(
                    device_key, scheduled_time, "scheduled_start"
                )
                action_details.append(eval_result)
                schedule_evaluations.append(eval_result["is_optimal"])

        # Evaluate temperature changes
        for temp_key in ["target_temperature_f", "target_water_temp_f"]:
            if temp_key in state_changes:
                temp_val = state_changes[temp_key].get("after")
                if temp_val is not None:
                    try:
                        temp_float = float(temp_val)
                        # Determine device type from key
                        if "water" in temp_key.lower() or "water" in device_key.lower():
                            temp_device_type = "water_heater"
                        else:
                            temp_device_type = "hvac"

                        # Try to get mode from state
                        mode = state_changes.get("mode", {}).get("after")

                        eval_result = _evaluate_temperature_action(
                            device_key, temp_float, temp_device_type, mode
                        )
                        action_details.append(eval_result)
                        temp_evaluations.append(eval_result["is_optimal"])
                    except (ValueError, TypeError):
                        pass

        # Evaluate power changes
        if "power" in state_changes:
            power_before = state_changes["power"].get("before")
            power_after = state_changes["power"].get("after")
            if power_after:
                eval_result = _evaluate_power_action(
                    device_key, power_before, power_after, device_type
                )
                action_details.append(eval_result)
                power_evaluations.append(eval_result["is_optimal"])

        # Evaluate mode changes
        if "mode" in state_changes:
            mode_before = state_changes["mode"].get("before")
            mode_after = state_changes["mode"].get("after")
            if mode_after:
                eval_result = _evaluate_mode_action(
                    device_key, mode_before, mode_after, device_type
                )
                action_details.append(eval_result)
                mode_evaluations.append(eval_result["is_optimal"])

        # Evaluate speed changes (pool pump, fans, etc.)
        for speed_key in ["current_speed_rpm", "speed_rpm", "fan_speed"]:
            if speed_key in state_changes:
                speed_before = state_changes[speed_key].get("before")
                speed_after = state_changes[speed_key].get("after")
                if speed_after is not None:
                    try:
                        speed_float = float(speed_after)
                        speed_before_float = float(speed_before) if speed_before else None
                        eval_result = _evaluate_speed_action(
                            device_key, speed_before_float, speed_float, device_type
                        )
                        action_details.append(eval_result)
                        speed_evaluations.append(eval_result["is_optimal"])
                    except (ValueError, TypeError):
                        pass

    if not action_details:
        return None

    # Calculate summary metrics
    actions_evaluated = len(action_details)
    actions_correct = sum(1 for a in action_details if a["is_correct"])
    actions_optimal = sum(1 for a in action_details if a["is_optimal"])
    actions_suboptimal = actions_correct - actions_optimal

    correctness_score = (actions_correct / actions_evaluated * 100) if actions_evaluated > 0 else 0

    # Calculate per-category correctness rates
    schedule_correctness = (
        (sum(schedule_evaluations) / len(schedule_evaluations) * 100)
        if schedule_evaluations else None
    )
    temperature_correctness = (
        (sum(temp_evaluations) / len(temp_evaluations) * 100)
        if temp_evaluations else None
    )
    mode_correctness = (
        (sum(mode_evaluations) / len(mode_evaluations) * 100)
        if mode_evaluations else None
    )
    power_correctness = (
        (sum(power_evaluations) / len(power_evaluations) * 100)
        if power_evaluations else None
    )
    speed_correctness = (
        (sum(speed_evaluations) / len(speed_evaluations) * 100)
        if speed_evaluations else None
    )

    # Evaluate constraint compliance
    constraint_result = evaluate_constraint_compliance(
        device_state_changes, device_state_after
    )
    constraint_compliance_rate = (
        round(constraint_result["compliance_rate"] * 100, 1)
        if constraint_result["total_constrained_actions"] > 0
        else None
    )
    constraint_violations = constraint_result["violations"]

    return ActionCorrectnessResult(
        correctness_score=round(correctness_score, 1),
        actions_evaluated=actions_evaluated,
        actions_correct=actions_correct,
        actions_suboptimal=actions_suboptimal,
        action_details=action_details,
        schedule_correctness=round(schedule_correctness, 1) if schedule_correctness is not None else None,
        temperature_correctness=round(temperature_correctness, 1) if temperature_correctness is not None else None,
        mode_correctness=round(mode_correctness, 1) if mode_correctness is not None else None,
        power_correctness=round(power_correctness, 1) if power_correctness is not None else None,
        speed_correctness=round(speed_correctness, 1) if speed_correctness is not None else None,
        constraint_compliance_rate=constraint_compliance_rate,
        constraint_violations=constraint_violations,
    )
