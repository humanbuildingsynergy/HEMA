# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/tools/control_tools/device_scheduling.py
"""Scheduling and automation tools for device control.

This module provides tools for scheduling device actions and
managing automation rules.
"""
from typing import Optional

from langchain_core.tools import tool

from utils.logger import setup_logger
from agents.tools.common import get_current_time
from agents.tools.analysis_tools.tou_utils import get_tou_classification
from .device_state import load_device_config, update_device_state
from .device_utils import find_device

logger = setup_logger()


@tool
def schedule_device_action(
    device_name: str,
    action: str,
    time: str,
    value: Optional[str] = None
) -> str:
    """
    Schedule a device action for a specific time.

    Args:
        device_name: Name or type of device
        action: Action to schedule (e.g., 'start', 'set_temperature')
        time: Time to execute in 24-hour format (e.g., '22:00', '06:30')
        value: Optional value for the action

    Returns:
        Confirmation of scheduled action.
    """
    logger.info(f"Scheduling: {device_name} - {action} at {time}")

    device_key, device = find_device(device_name)
    if not device:
        config = load_device_config()
        available = list(config.get("devices", {}).keys())
        return f"Device '{device_name}' not found.\n\n**Available devices:** {', '.join(available)}"

    # Validate time format
    try:
        hour, minute = time.split(":")
        hour, minute = int(hour), int(minute)
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("Invalid time range")
    except (ValueError, AttributeError):
        return "Invalid time format. Use 24-hour format (e.g., '22:00' or '06:30')"

    device_name_display = device.get("display_name", device_key)

    # Update device state with the scheduled action
    updates = {
        "scheduled_action": action,
        "scheduled_time": time,
    }
    if value:
        updates["scheduled_value"] = value

    update_device_state(device_key, updates)

    # Check TOU status for the scheduled time using rate data
    current_time = get_current_time()
    tou_info = get_tou_classification(hour=hour, dt=current_time)

    lines = [
        "## Scheduled Action",
        "",
        f"**Device:** {device_name_display}",
        f"**Action:** {action}",
        f"**Scheduled Time:** {time}",
    ]
    if value:
        lines.append(f"**Value:** {value}")

    # Add TOU information
    if tou_info.is_off_peak:
        lines.append(f"**Rate Period:** Off-peak ({tou_info.rate_cents:.1f}¢/kWh) - optimal for savings")
    elif tou_info.is_peak:
        lines.append(f"**Rate Period:** Peak ({tou_info.rate_cents:.1f}¢/kWh) - consider off-peak hours for savings")
    else:
        lines.append(f"**Rate:** {tou_info.rate_cents:.1f}¢/kWh")

    lines.append("")
    lines.append("Action scheduled successfully.")

    return "\n".join(lines)


@tool
def get_automation_rules() -> str:
    """
    Get the list of configured automation rules for demand response and energy optimization.

    Returns:
        List of active automation rules with triggers, actions, and purposes.
    """
    logger.info("Getting automation rules")

    config = load_device_config()
    rules = config.get("automation_rules", [])
    home_name = config.get("home_name", "Home")

    lines = [
        f"## {home_name} - Automation Rules",
        ""
    ]

    if not rules:
        lines.append("No automation rules configured.")
        return "\n".join(lines)

    lines.append(f"**Total Rules:** {len(rules)}")
    lines.append("")

    for rule in rules:
        trigger = rule.get("trigger", {})
        trigger_type = trigger.get("type", "")

        if trigger_type == "time":
            trigger_desc = f"At {trigger.get('value')}"
        elif trigger_type == "condition":
            trigger_desc = (f"When {trigger.get('device')} "
                          f"{trigger.get('property')} {trigger.get('operator')} {trigger.get('value')}")
        else:
            trigger_desc = str(trigger)

        actions = rule.get("actions", [])
        action_descs = [f"{a.get('device')}: {a.get('action')}" for a in actions]

        lines.append(f"**{rule.get('name', 'Unnamed')}**")
        lines.append(f"- Trigger: {trigger_desc}")
        lines.append(f"- Actions: {', '.join(action_descs)}")
        lines.append(f"- Purpose: {rule.get('description', 'N/A')}")
        lines.append("")

    lines.append("---")
    lines.append("*For TOU rate information, use get_utility_rate()*")

    return "\n".join(lines)
