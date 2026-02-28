# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/tools/control_tools/device_control.py
"""Control tools for the Control Agent - handles IoT device interactions.

This module provides ADAPTIVE device control using configurations loaded from JSON.
All device features, states, and actions are read dynamically from the config file,
eliminating the need for device-specific hardcoded functions.

For production use, these would integrate with actual device APIs:
- MCP (Model Context Protocol) server integration
- Device-specific APIs (Ecobee, Nest, Home Assistant, etc.)
- Proper authentication and security

This module has been refactored into focused submodules:
- device_actions.py: Action handlers for control operations
- device_status.py: Status query tools (get_device_status, get_device_list, etc.)
- device_energy.py: Energy query tools (get_device_energy, get_all_devices_energy)
- device_scheduling.py: Scheduling tools (schedule_device_action, get_automation_rules)
- device_state.py: State management (load_device_config, update_device_state, etc.)
- device_utils.py: Utility functions (find_device, format_key, format_value)
"""
from typing import Optional

from langchain_core.tools import tool

from utils.logger import setup_logger
from .device_state import load_device_config, update_device_state
from .device_utils import find_device, format_key, format_value
from .device_actions import dispatch_action

logger = setup_logger()


# Re-export tools from submodules for backward compatibility
from .device_status import get_device_status, get_device_list, get_available_actions
from .device_energy import get_device_energy, get_all_devices_energy
from .device_scheduling import schedule_device_action, get_automation_rules

# Re-export state management functions
from .device_state import (
    reset_device_state,
    get_device_state_snapshot,
    compare_device_states,
)


@tool
def control_device(
    device_name: str,
    action: str,
    value: Optional[str] = None
) -> str:
    """
    Control any smart device by executing an action.

    This tool reads available actions from the device configuration and executes
    them. It validates parameters and provides feedback.

    Args:
        device_name: Name or type of device (e.g., 'thermostat', 'ev charger', 'pool pump')
        action: Action to perform. Common actions include:
                - 'on', 'off', 'start', 'stop' (basic power control)
                - 'set_temperature', 'set_mode', 'set_speed' (device-specific)
                - Use get_device_status to see available actions for a device
        value: Value or parameter for the action (e.g., '72' for temperature,
               'heat' for mode, 'low' for speed preset)

    Returns:
        Confirmation of action taken with updated device state.
    """
    logger.info(f"Control device: {device_name} - {action} = {value}")

    device_key, device = find_device(device_name)
    if not device:
        config = load_device_config()
        available = list(config.get("devices", {}).keys())
        return f"Device '{device_name}' not found.\n\n**Available devices:** {', '.join(available)}"

    device_name_display = device.get("display_name", device_key)
    state = device.get("current_state", {})
    settings = device.get("settings", {})
    control_actions = device.get("control_actions", [])

    # Dispatch to action handler
    result = dispatch_action(
        action=action,
        state=state,
        settings=settings,
        value=value,
        control_actions=control_actions,
        device_name_display=device_name_display,
    )

    # If result is a string, it's an error message
    if isinstance(result, str):
        return result

    # Unpack successful result
    updates, result_lines, tips = result

    # Build response
    response_lines = [f"## {device_name_display} - Control Result", ""]
    response_lines.extend(result_lines)

    # Apply updates
    if updates:
        update_device_state(device_key, updates)

    # Show updated state
    response_lines.append("")
    response_lines.append("**Updated State:**")
    updated_state = device.get("current_state", {})
    for key in updates:
        response_lines.append(f"- {format_key(key)}: {format_value(key, updated_state.get(key, updates[key]))}")

    # Add tips
    if tips:
        response_lines.append("")
        response_lines.append("**Tips:**")
        for tip in tips:
            response_lines.append(f"- {tip}")

    return "\n".join(response_lines)
