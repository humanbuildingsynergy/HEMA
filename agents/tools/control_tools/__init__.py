# agents/tools/control_tools/__init__.py
"""Control tools package for the Control Agent.

This package provides IoT device control and automation tools organized into submodules:
- device_control: Main control tool and re-exports for backward compatibility
- device_status: Status query tools (get_device_status, get_device_list, etc.)
- device_energy: Energy query tools (get_device_energy, get_all_devices_energy)
- device_scheduling: Scheduling tools (schedule_device_action, get_automation_rules)
- device_actions: Action handlers (internal, used by control_device)
- device_state: State management (load_device_config, update_device_state, etc.)
- device_utils: Utility functions (find_device, format_key, format_value)
"""

from .device_control import (
    # Device information
    get_device_status,
    get_device_list,
    get_available_actions,
    get_device_energy,
    get_all_devices_energy,
    # Device control
    control_device,
    schedule_device_action,
    # Automation
    get_automation_rules,
    # State management (for evaluation)
    reset_device_state,
    get_device_state_snapshot,
    compare_device_states,
)

__all__ = [
    # Device information
    "get_device_status",
    "get_device_list",
    "get_available_actions",
    "get_device_energy",
    "get_all_devices_energy",
    # Device control
    "control_device",
    "schedule_device_action",
    # Automation
    "get_automation_rules",
    # State management (for evaluation)
    "reset_device_state",
    "get_device_state_snapshot",
    "compare_device_states",
]
