# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/tools/control_tools/device_actions.py
"""Action handlers for device control operations.

This module contains individual action handlers extracted from the control_device tool.
Each handler processes a specific type of action (power, temperature, mode, etc.)
and returns a tuple of (updates, result_lines, tips) or an error string.
"""
from typing import Dict, List, Tuple, Union, Any, Optional

from agents.tools.common import get_current_time
from agents.tools.analysis_tools.tou_utils import get_tou_classification


# Type alias for action handler return value
ActionResult = Union[Tuple[Dict[str, Any], List[str], List[str]], str]


def handle_power_on(
    state: Dict[str, Any],
    settings: Dict[str, Any],
    value: Optional[str],
) -> ActionResult:
    """Handle power on actions."""
    updates = {"power": "on"}
    result_lines = ["**Action:** Turned ON"]
    return updates, result_lines, []


def handle_power_off(
    state: Dict[str, Any],
    settings: Dict[str, Any],
    value: Optional[str],
) -> ActionResult:
    """Handle power off actions."""
    updates = {"power": "off"}
    result_lines = ["**Action:** Turned OFF"]
    return updates, result_lines, []


def handle_set_temperature(
    state: Dict[str, Any],
    settings: Dict[str, Any],
    value: Optional[str],
) -> ActionResult:
    """Handle temperature setting actions."""
    if not value:
        return "Please provide a temperature value"

    try:
        temp = float(value.replace("°", "").replace("F", "").replace("f", "").strip())
        temp_range = settings.get("temperature_range_f", {})
        min_temp = temp_range.get("min", 50)
        max_temp = temp_range.get("max", 90)

        if not (min_temp <= temp <= max_temp):
            return f"Temperature {temp}°F is outside valid range ({min_temp}°F - {max_temp}°F)"

        # Find the right temperature key in state
        temp_key = None
        for key in state:
            if "target" in key.lower() and "temp" in key.lower():
                temp_key = key
                break
        if not temp_key:
            temp_key = "target_temperature_f"

        old_temp = state.get(temp_key, "N/A")
        updates = {temp_key: temp}
        result_lines = [
            "**Action:** Set temperature",
            f"**Change:** {old_temp}°F → {temp}°F",
        ]
        return updates, result_lines, []

    except ValueError:
        return f"Invalid temperature value: {value}"


def handle_set_mode(
    state: Dict[str, Any],
    settings: Dict[str, Any],
    value: Optional[str],
) -> ActionResult:
    """Handle mode setting actions."""
    if not value:
        valid_modes = settings.get("modes", [])
        return f"Please provide a mode. Valid modes: {', '.join(valid_modes)}"

    mode_value = value.lower().replace(" ", "_")
    valid_modes = settings.get("modes", [])
    if valid_modes and mode_value not in valid_modes:
        return f"Invalid mode '{value}'. Valid modes: {', '.join(valid_modes)}"

    old_mode = state.get("mode", "N/A")
    updates = {"mode": mode_value}
    result_lines = [
        "**Action:** Set mode",
        f"**Change:** {old_mode} → {mode_value}",
    ]

    # Mode-specific tips
    tips = []
    if mode_value == "heat_pump":
        tips.append("Heat pump mode is most efficient (70% less energy than electric)")
    elif mode_value == "vacation":
        tips.append("Vacation mode reduces energy usage while away")

    return updates, result_lines, tips


def handle_set_speed(
    state: Dict[str, Any],
    settings: Dict[str, Any],
    value: Optional[str],
) -> ActionResult:
    """Handle speed/preset setting actions (pool pump, fans, etc.)."""
    if not value:
        return "Please provide a speed value or preset name"

    value_lower = value.lower()
    presets = settings.get("preset_speeds", [])

    # Check if it's a named preset
    preset_match = None
    for p in presets:
        if isinstance(p, dict) and p.get("name", "").lower() == value_lower:
            preset_match = p
            break

    if preset_match:
        rpm = preset_match.get("rpm", 0)
        updates = {"current_speed_rpm": rpm, "power": "on"}
        result_lines = [f"**Action:** Set to {value} preset ({rpm} RPM)"]
        return updates, result_lines, []

    # Try numeric RPM
    try:
        rpm = int(value)
        speed_range = settings.get("speed_range_rpm", {})
        if speed_range:
            min_rpm = speed_range.get("min", 0)
            max_rpm = speed_range.get("max", 5000)
            if not min_rpm <= rpm <= max_rpm:
                return f"Speed {rpm} RPM outside valid range ({min_rpm} - {max_rpm})"
        updates = {"current_speed_rpm": rpm, "power": "on"}
        result_lines = [f"**Action:** Set speed to {rpm} RPM"]
        return updates, result_lines, []
    except ValueError:
        preset_names = [p.get("name") for p in presets if isinstance(p, dict)]
        return f"Invalid speed/preset '{value}'. Valid presets: {', '.join(preset_names)}"


def handle_set_charge_limit(
    state: Dict[str, Any],
    settings: Dict[str, Any],
    value: Optional[str],
) -> ActionResult:
    """Handle EV charge limit setting actions."""
    if not value:
        return "Please provide a charge limit percentage (50-100)"

    try:
        limit = int(value.replace("%", "").strip())
        if not (50 <= limit <= 100):
            return "Charge limit must be between 50% and 100%"

        updates = {"charge_limit_percent": limit}
        result_lines = [f"**Action:** Set charge limit to {limit}%"]
        tips = []
        if limit <= 80:
            tips.append("Charging to 80% or below helps preserve battery longevity")
        return updates, result_lines, tips

    except ValueError:
        return f"Invalid charge limit: {value}"


def handle_start_charging(
    state: Dict[str, Any],
    settings: Dict[str, Any],
    value: Optional[str],
) -> ActionResult:
    """Handle EV start charging actions."""
    if not state.get("vehicle_connected", True):
        return "Cannot start charging: No vehicle connected"

    updates = {
        "charging_status": "charging",
        "current_power_kw": state.get("max_charge_rate_kw", 7.2),
    }
    result_lines = ["**Action:** Started charging"]

    # Check TOU timing using rate data (accounts for seasonal variations)
    tips = []
    current_time = get_current_time()
    tou_info = get_tou_classification(hour=current_time.hour, dt=current_time)

    if tou_info.is_peak:
        tips.append(f"Currently in peak rate period ({tou_info.rate_cents:.1f}¢/kWh). Consider scheduling for off-peak hours")

    return updates, result_lines, tips


def handle_stop_charging(
    state: Dict[str, Any],
    settings: Dict[str, Any],
    value: Optional[str],
) -> ActionResult:
    """Handle EV stop charging actions."""
    updates = {"charging_status": "stopped", "current_power_kw": 0}
    result_lines = ["**Action:** Stopped charging"]
    return updates, result_lines, []


def handle_set_schedule(
    state: Dict[str, Any],
    settings: Dict[str, Any],
    value: Optional[str],
) -> ActionResult:
    """Handle schedule setting actions."""
    if not value:
        return "Please provide a time (e.g., '22:00')"

    updates = {"scheduled_start_time": value}
    result_lines = [f"**Action:** Scheduled for {value}"]

    # Check if off-peak using rate data (accounts for seasonal variations)
    tips = []
    try:
        hour = int(value.split(":")[0])
        # Get current simulated time for month context
        current_time = get_current_time()
        tou_info = get_tou_classification(hour=hour, dt=current_time)

        if tou_info.is_off_peak:
            tips.append(f"Good choice! This is during off-peak hours ({tou_info.rate_cents:.1f}¢/kWh)")
        elif tou_info.is_peak:
            tips.append(f"Note: {hour}:00 is during peak hours ({tou_info.rate_cents:.1f}¢/kWh). Consider off-peak hours for savings")
    except (ValueError, IndexError):
        pass

    return updates, result_lines, tips


def handle_vacation_on(
    state: Dict[str, Any],
    settings: Dict[str, Any],
    value: Optional[str],
) -> ActionResult:
    """Handle vacation mode enable actions."""
    updates = {"mode": "vacation"}
    vacation_temp = settings.get("vacation_mode_temp_f", 60)
    if "target_water_temp_f" in state:
        updates["target_water_temp_f"] = vacation_temp

    result_lines = ["**Action:** Vacation mode enabled"]
    tips = ["Energy consumption reduced while away"]
    return updates, result_lines, tips


def handle_vacation_off(
    state: Dict[str, Any],
    settings: Dict[str, Any],
    value: Optional[str],
) -> ActionResult:
    """Handle vacation mode disable actions."""
    updates = {"mode": settings.get("default_mode", "auto")}
    result_lines = ["**Action:** Vacation mode disabled, returning to normal operation"]
    return updates, result_lines, []


def handle_away_mode(
    state: Dict[str, Any],
    settings: Dict[str, Any],
    value: Optional[str],
) -> ActionResult:
    """Handle away mode for HVAC systems.

    Away mode sets temperature to energy-saving levels based on current mode:
    - Cooling mode: Higher setpoint (85°F default) to reduce AC runtime
    - Heating mode: Lower setpoint (62°F default) to reduce heating
    """
    current_mode = state.get("mode", "cool")

    # Set temperature to energy-saving level based on mode
    if current_mode == "heat":
        away_temp = settings.get("away_mode_temp_f", 62)  # Lower for heating
    else:
        away_temp = settings.get("away_mode_temp_f", 85)  # Higher for cooling

    updates = {}
    if "target_temperature_f" in state:
        updates["target_temperature_f"] = away_temp

    result_lines = [
        "**Action:** Away mode enabled",
        f"**Temperature setback:** {away_temp}°F",
    ]
    tips = ["HVAC will maintain minimal conditioning while you're away"]
    return updates, result_lines, tips


def handle_disable_away(
    state: Dict[str, Any],
    settings: Dict[str, Any],
    value: Optional[str],
) -> ActionResult:
    """Handle disabling away mode for HVAC systems."""
    # Return to auto mode with default temperature
    default_temp = settings.get("default_temperature_f", 74)
    updates = {"mode": "auto"}
    if "target_temperature_f" in state:
        updates["target_temperature_f"] = default_temp

    result_lines = ["**Action:** Away mode disabled, returning to normal operation"]
    tips = ["HVAC will resume normal schedule"]
    return updates, result_lines, tips


# Action mapping: maps normalized action names to handler functions
ACTION_HANDLERS = {
    # Power control
    "on": handle_power_on,
    "start": handle_power_on,
    "turn_on": handle_power_on,
    "power_on": handle_power_on,
    "off": handle_power_off,
    "stop": handle_power_off,
    "turn_off": handle_power_off,
    "power_off": handle_power_off,
    # Temperature control
    "set_temperature": handle_set_temperature,
    "set_temp": handle_set_temperature,
    "temperature": handle_set_temperature,
    # Mode control
    "set_mode": handle_set_mode,
    "mode": handle_set_mode,
    "change_mode": handle_set_mode,
    # Speed/preset control
    "set_speed": handle_set_speed,
    "set_preset": handle_set_speed,
    "speed": handle_set_speed,
    "preset": handle_set_speed,
    # EV charging
    "set_charge_limit": handle_set_charge_limit,
    "charge_limit": handle_set_charge_limit,
    "set_limit": handle_set_charge_limit,
    "start_charging": handle_start_charging,
    "begin_charging": handle_start_charging,
    "stop_charging": handle_stop_charging,
    "end_charging": handle_stop_charging,
    # Scheduling
    "set_schedule": handle_set_schedule,
    "schedule": handle_set_schedule,
    # Vacation mode
    "vacation_on": handle_vacation_on,
    "enable_vacation": handle_vacation_on,
    "enable_vacation_mode": handle_vacation_on,  # Device config uses this name
    "vacation_mode": handle_vacation_on,
    "vacation_off": handle_vacation_off,
    "disable_vacation": handle_vacation_off,
    "disable_vacation_mode": handle_vacation_off,  # Device config uses this name
    # Away mode (HVAC)
    "away": handle_away_mode,
    "away_mode": handle_away_mode,
    "enable_away": handle_away_mode,
    "enable_away_mode": handle_away_mode,
    "disable_away": handle_disable_away,
    "disable_away_mode": handle_disable_away,
}


def dispatch_action(
    action: str,
    state: Dict[str, Any],
    settings: Dict[str, Any],
    value: Optional[str],
    control_actions: List[Dict[str, Any]],
    device_name_display: str,
) -> ActionResult:
    """Dispatch an action to the appropriate handler.

    Args:
        action: The action name (will be normalized)
        state: Current device state
        settings: Device settings/constraints
        value: Optional value for the action
        control_actions: List of available control actions for error messages
        device_name_display: Display name of the device for error messages

    Returns:
        Either (updates, result_lines, tips) tuple on success,
        or an error string on failure.
    """
    action_lower = action.lower().replace(" ", "_")

    handler = ACTION_HANDLERS.get(action_lower)
    if handler:
        return handler(state, settings, value)

    # Unknown action - return helpful error
    action_list = [a.get("action", "") for a in control_actions]
    return (
        f"Unknown action '{action}' for {device_name_display}.\n\n"
        f"**Available actions:** {', '.join(action_list)}\n\n"
        f"**Common actions:** on, off, set_temperature, set_mode, set_speed, set_schedule"
    )
