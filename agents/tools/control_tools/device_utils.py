# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/tools/control_tools/device_utils.py
"""Utility functions for device control tools.

This module provides device lookup, formatting, and alias resolution.
"""
import json
from typing import Optional, Dict, Any, Tuple

from .device_state import load_device_config

# Common device aliases for better fuzzy matching
DEVICE_ALIASES = {
    "thermostat": "hvac",
    "ac": "hvac",
    "air_conditioner": "hvac",
    "heat": "hvac",
    "heater": "hvac",
    "heating": "hvac",
    "cooling": "hvac",
    "car_charger": "ev_charger",
    "electric_vehicle": "ev_charger",
    "tesla_charger": "ev_charger",
    "washer": "washing_machine",
    "laundry": "washing_machine",
    "dryer": "clothes_dryer",
    "pump": "pool_pump",
    "hot_water": "water_heater",
    "boiler": "water_heater",
    "stove": "cooktop",
    "range": "cooktop",
    "disposal": "garbage_disposal",
    "solar": "solar_system",
    "solar_panels": "solar_system",
    "pv": "solar_system",
    "fridge": "refrigerator",
}


def find_device(device_name: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Find a device by name, type, or partial match.

    Supports:
    - Exact key match (e.g., 'hvac', 'ev_charger')
    - Common aliases (e.g., 'thermostat' → 'hvac')
    - Display name match (e.g., 'Smart Thermostat')
    - Partial key match (e.g., 'charger' → 'ev_charger')

    Args:
        device_name: Name, type, or alias of the device to find.

    Returns:
        Tuple of (device_key, device_data) or (None, None) if not found.
    """
    config = load_device_config()
    devices = config.get("devices", {})

    # Normalize input
    search_key = device_name.lower().replace(" ", "_").replace("-", "_")

    # Try exact match first
    if search_key in devices:
        return search_key, devices[search_key]

    # Try alias match
    alias_target = DEVICE_ALIASES.get(search_key)
    if alias_target and alias_target in devices:
        return alias_target, devices[alias_target]

    # Try matching display_name
    for key, device in devices.items():
        display_name = device.get("display_name", "").lower().replace(" ", "_")
        if search_key in display_name or display_name in search_key:
            return key, device

    # Try partial key match
    for key in devices:
        if search_key in key or key in search_key:
            return key, devices[key]

    # Try partial alias match
    for alias, target in DEVICE_ALIASES.items():
        if search_key in alias or alias in search_key:
            if target in devices:
                return target, devices[target]

    return None, None


def format_value(key: str, value: Any) -> str:
    """Format a value for display based on its key and type.

    Args:
        key: The key name (used to infer units).
        value: The value to format.

    Returns:
        Formatted string representation of the value.
    """
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float):
        # Infer unit from key name
        key_lower = key.lower()
        if "percent" in key_lower:
            return f"{value:.0f}%"
        elif "temp" in key_lower and "f" in key_lower:
            return f"{value:.0f}°F"
        elif "temp" in key_lower:
            return f"{value:.1f}°"
        elif "kwh" in key_lower:
            return f"{value:.2f} kWh"
        elif "kw" in key_lower:
            return f"{value:.2f} kW"
        elif "rpm" in key_lower:
            return f"{value:.0f} RPM"
        elif "gpm" in key_lower:
            return f"{value:.1f} GPM"
        elif "psi" in key_lower:
            return f"{value:.1f} PSI"
        elif "hours" in key_lower:
            return f"{value:.1f} hours"
        elif "minutes" in key_lower:
            return f"{value:.0f} min"
        elif "gallons" in key_lower:
            return f"{value:.1f} gal"
        else:
            return f"{value:.2f}"
    if isinstance(value, int):
        key_lower = key.lower()
        if "percent" in key_lower:
            return f"{value}%"
        elif "temp" in key_lower:
            return f"{value}°F"
        elif "rpm" in key_lower:
            return f"{value} RPM"
        elif "minutes" in key_lower:
            return f"{value} min"
        return str(value)
    if isinstance(value, str):
        return value.replace("_", " ").title()
    if isinstance(value, list):
        return ", ".join(str(v) for v in value[:5])  # Limit list display
    if isinstance(value, dict):
        return json.dumps(value)
    return str(value)


def format_key(key: str) -> str:
    """Format a key for display.

    Args:
        key: The key name to format.

    Returns:
        Human-readable key name.
    """
    return key.replace("_", " ").title()
