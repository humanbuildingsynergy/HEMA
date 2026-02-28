# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/tools/control_tools/device_state.py
"""Device state management for control tools.

This module handles loading, caching, and managing device configuration state.
State is loaded from JSON config files and modified in-memory by control actions.
"""
import json
from pathlib import Path
from typing import Optional, Dict, Any

from utils.logger import setup_logger
from agents.tools.common import get_current_time

logger = setup_logger()

# Default device configuration file
DEFAULT_DEVICE_CONFIG = "data/device_config/demo_home_devices.json"

# Global device state (loaded from config, modified by control actions)
_device_state: Optional[Dict[str, Any]] = None
_config_path: Optional[str] = None


def _get_default_config() -> Dict[str, Any]:
    """Return default device configuration if file not found."""
    return {
        "home_id": "default",
        "home_name": "Default Home",
        "devices": {},
        "device_groups": {},
        "automation_rules": [],
        "tou_integration": {}
    }


def load_device_config(config_path: str = DEFAULT_DEVICE_CONFIG) -> Dict[str, Any]:
    """Load device configuration from JSON file.

    Args:
        config_path: Path to the device configuration JSON file.

    Returns:
        Device configuration dictionary.
    """
    global _device_state, _config_path

    if _device_state is not None and _config_path == config_path:
        return _device_state

    try:
        full_path = Path(config_path)
        if not full_path.is_absolute():
            project_root = Path(__file__).parent.parent.parent.parent
            full_path = project_root / config_path

        if full_path.exists():
            with open(full_path, "r") as f:
                _device_state = json.load(f)
                _config_path = config_path
                logger.info(f"Loaded device config from {full_path}")
                return _device_state
        else:
            logger.warning(f"Device config not found at {full_path}, using defaults")
            _device_state = _get_default_config()
            return _device_state

    except Exception as e:
        logger.error(f"Error loading device config: {e}")
        _device_state = _get_default_config()
        return _device_state


def update_device_state(device_key: str, updates: Dict[str, Any]) -> bool:
    """Update device state in memory.

    Args:
        device_key: Key of the device to update.
        updates: Dictionary of state updates to apply.

    Returns:
        True if update was successful, False otherwise.
    """
    config = load_device_config()
    if device_key in config.get("devices", {}):
        device = config["devices"][device_key]
        if "current_state" in device:
            device["current_state"].update(updates)
            return True
    return False


def reset_device_state() -> None:
    """Reset device state by clearing the cached config.

    This forces a reload from the JSON file on next access,
    useful for ensuring clean state between evaluation tests.
    """
    global _device_state, _config_path
    _device_state = None
    _config_path = None
    logger.info("Device state cache cleared - will reload from file on next access")


def get_device_state_snapshot() -> Dict[str, Any]:
    """Get a snapshot of all device states for evaluation verification.

    Returns a serializable dictionary containing the current state of all devices,
    suitable for saving to a file or comparing before/after control actions.

    Returns:
        Dict with device states, timestamp, and metadata.
    """
    config = load_device_config()
    devices = config.get("devices", {})

    snapshot = {
        "timestamp": get_current_time().isoformat(),
        "home_id": config.get("home_id", "unknown"),
        "home_name": config.get("home_name", "Unknown Home"),
        "device_count": len(devices),
        "devices": {}
    }

    for device_key, device in devices.items():
        snapshot["devices"][device_key] = {
            "display_name": device.get("display_name", device_key),
            "device_type": device.get("device_type", "unknown"),
            "connection_status": device.get("connection_status", "unknown"),
            "smart_enabled": device.get("smart_enabled", False),
            "current_state": device.get("current_state", {}).copy(),
        }

    return snapshot


def compare_device_states(
    before: Dict[str, Any],
    after: Dict[str, Any]
) -> Dict[str, Any]:
    """Compare two device state snapshots and return the differences.

    Args:
        before: Device state snapshot before control actions
        after: Device state snapshot after control actions

    Returns:
        Dict with changed devices and their state differences.
    """
    changes = {
        "timestamp_before": before.get("timestamp"),
        "timestamp_after": after.get("timestamp"),
        "devices_changed": [],
        "changes_by_device": {}
    }

    before_devices = before.get("devices", {})
    after_devices = after.get("devices", {})

    all_device_keys = set(before_devices.keys()) | set(after_devices.keys())

    for device_key in all_device_keys:
        before_state = before_devices.get(device_key, {}).get("current_state", {})
        after_state = after_devices.get(device_key, {}).get("current_state", {})

        device_changes = {}
        all_keys = set(before_state.keys()) | set(after_state.keys())

        for key in all_keys:
            before_val = before_state.get(key)
            after_val = after_state.get(key)

            if before_val != after_val:
                device_changes[key] = {
                    "before": before_val,
                    "after": after_val
                }

        if device_changes:
            display_name = after_devices.get(device_key, {}).get(
                "display_name",
                before_devices.get(device_key, {}).get("display_name", device_key)
            )
            changes["devices_changed"].append(device_key)
            changes["changes_by_device"][device_key] = {
                "display_name": display_name,
                "state_changes": device_changes
            }

    changes["total_changes"] = len(changes["devices_changed"])

    return changes
