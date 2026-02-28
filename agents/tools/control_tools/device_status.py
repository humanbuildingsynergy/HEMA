# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/tools/control_tools/device_status.py
"""Status query tools for device control.

This module provides read-only tools for querying device status,
listing devices, and getting available actions.
"""
from langchain_core.tools import tool

from utils.logger import setup_logger
from .device_state import load_device_config
from .device_utils import find_device, format_key, format_value

logger = setup_logger()


@tool
def get_device_status(device_name: str) -> str:
    """
    Get the current status of any smart device.

    This tool dynamically reads the device's current state from the configuration
    and formats it for display. Works with any device type.

    Args:
        device_name: Name or type of the device (e.g., 'thermostat', 'hvac',
                    'ev charger', 'dishwasher', 'pool pump', 'water heater')

    Returns:
        Formatted device status including all current state information,
        capabilities, and available actions.
    """
    logger.info(f"Getting status for device: {device_name}")

    device_key, device = find_device(device_name)
    if not device:
        config = load_device_config()
        available = list(config.get("devices", {}).keys())
        return f"Device '{device_name}' not found.\n\n**Available devices:** {', '.join(available)}"

    # Build status display
    lines = [
        f"## {device.get('display_name', device_key)}",
        "",
        "**Device Info:**",
        f"- Manufacturer: {device.get('manufacturer', 'Unknown')}",
        f"- Model: {device.get('model', 'Unknown')}",
        f"- Connection: {device.get('connection_status', 'unknown').title()}",
        f"- Smart Enabled: {'Yes' if device.get('smart_enabled') else 'No'}",
    ]

    # Capabilities
    capabilities = device.get("capabilities", [])
    if capabilities:
        lines.append(f"- Capabilities: {', '.join(c.replace('_', ' ').title() for c in capabilities[:6])}")

    # Current State (dynamically formatted)
    state = device.get("current_state", {})
    if state:
        lines.append("")
        lines.append("**Current State:**")
        for key, value in state.items():
            lines.append(f"- {format_key(key)}: {format_value(key, value)}")

    # Settings summary (show key constraints)
    settings = device.get("settings", {})
    if settings:
        lines.append("")
        lines.append("**Settings/Limits:**")
        for key, value in list(settings.items())[:5]:  # Show top 5 settings
            if isinstance(value, dict) and "min" in value and "max" in value:
                lines.append(f"- {format_key(key)}: {value['min']} - {value['max']}")
            elif isinstance(value, list) and len(value) <= 6:
                lines.append(f"- {format_key(key)}: {', '.join(str(v) for v in value)}")

    # Energy info
    energy = device.get("energy_info", {})
    if energy:
        lines.append("")
        lines.append("**Energy Info:**")
        for key, value in list(energy.items())[:4]:  # Show top 4 energy stats
            lines.append(f"- {format_key(key)}: {format_value(key, value)}")

    # Available actions
    actions = device.get("control_actions", [])
    if actions:
        lines.append("")
        lines.append("**Available Actions:**")
        for action in actions[:6]:  # Show top 6 actions
            action_name = action.get("action", "").replace("_", " ").title()
            description = action.get("description", "")
            lines.append(f"- {action_name}: {description}")

    return "\n".join(lines)


@tool
def get_device_list() -> str:
    """
    Get a list of all smart devices in the home with their current status summary.

    Returns:
        Overview of all devices grouped by status (online/offline) with key metrics.
    """
    logger.info("Getting device list")

    config = load_device_config()
    devices = config.get("devices", {})
    home_name = config.get("home_name", "Home")

    lines = [
        f"## {home_name} - Smart Devices",
        f"**Total Devices:** {len(devices)}",
        ""
    ]

    online_devices = []
    offline_devices = []

    for device_key, device in devices.items():
        name = device.get("display_name", device_key)
        connection = device.get("connection_status", "unknown")
        state = device.get("current_state", {})

        # Build status summary
        status_parts = []
        power = state.get("power", "")
        if power:
            status_parts.append(power.title())

        # Add key metric based on device type
        if "current_temperature_f" in state and "target_temperature_f" in state:
            status_parts.append(f"{state['current_temperature_f']}°F → {state['target_temperature_f']}°F")
        elif "vehicle_battery_percent" in state:
            status_parts.append(f"Battery: {state['vehicle_battery_percent']}%")
        elif "current_speed_rpm" in state:
            status_parts.append(f"{state['current_speed_rpm']} RPM")
        elif "current_production_kw" in state:
            status_parts.append(f"Producing: {state['current_production_kw']} kW")

        status_str = " | ".join(status_parts) if status_parts else "Ready"

        entry = f"| {name} | {status_str} |"

        if connection == "online":
            online_devices.append(entry)
        else:
            offline_devices.append(entry)

    if online_devices:
        lines.append("### Online Devices")
        lines.append("| Device | Status |")
        lines.append("|--------|--------|")
        lines.extend(online_devices)
        lines.append("")

    if offline_devices:
        lines.append("### Offline Devices")
        lines.append("| Device | Status |")
        lines.append("|--------|--------|")
        lines.extend(offline_devices)

    return "\n".join(lines)


@tool
def get_available_actions(device_name: str) -> str:
    """
    Get the list of available control actions for a specific device.

    Args:
        device_name: Name or type of device

    Returns:
        List of actions with parameters and descriptions.
    """
    logger.info(f"Getting available actions for: {device_name}")

    device_key, device = find_device(device_name)
    if not device:
        config = load_device_config()
        available = list(config.get("devices", {}).keys())
        return f"Device '{device_name}' not found.\n\n**Available devices:** {', '.join(available)}"

    name = device.get("display_name", device_key)
    actions = device.get("control_actions", [])
    settings = device.get("settings", {})

    lines = [f"## {name} - Available Actions", ""]

    if not actions:
        lines.append("No specific actions defined. Common actions: on, off, status")
        return "\n".join(lines)

    for action in actions:
        action_name = action.get("action", "").replace("_", " ").title()
        params = action.get("params", [])
        description = action.get("description", "")

        param_str = f" ({', '.join(params)})" if params else ""
        lines.append(f"- **{action_name}{param_str}**: {description}")

    # Show relevant settings for context
    if settings:
        lines.append("")
        lines.append("**Valid Values:**")
        for key, value in settings.items():
            if isinstance(value, list) and len(value) <= 8:
                lines.append(f"- {format_key(key)}: {', '.join(str(v) for v in value)}")
            elif isinstance(value, dict) and "min" in value and "max" in value:
                lines.append(f"- {format_key(key)}: {value['min']} - {value['max']}")

    return "\n".join(lines)
