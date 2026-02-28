# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/metrics/action_helpers.py
"""Helper functions for device action evaluation."""

from typing import Dict, List, Optional, Any

from agents.tools.analysis_tools.tou_utils import get_tou_classification
from agents.tools.analysis_tools.cache import get_current_time

from .action_constants import (
    EFFICIENT_TEMP_RANGES,
    POOL_PUMP_SPEED_RANGES,
    HVAC_MODE_GUIDELINES,
    WATER_HEATER_MODE_EFFICIENCY,
    DEVICE_CONSTRAINTS,
)


def evaluate_constraint_compliance(
    device_state_changes: Dict[str, Any],
    device_state_after: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Evaluate whether device actions respected device constraints/limits.

    Checks:
    - Temperature settings within device min/max range
    - Mode settings are valid for the device type
    - Speed settings within device speed range
    - Charge limits within valid range

    Args:
        device_state_changes: Changes captured during experiment
        device_state_after: Final device state snapshot (for device config info)

    Returns:
        Dict with:
        - compliance_rate: float (0-1)
        - total_constrained_actions: int
        - compliant_actions: int
        - violations: List of violation details
    """
    changes_by_device = device_state_changes.get("changes_by_device", {})
    if not changes_by_device:
        return {
            "compliance_rate": 1.0,
            "total_constrained_actions": 0,
            "compliant_actions": 0,
            "violations": [],
        }

    violations = []
    total_checks = 0
    compliant_checks = 0

    for device_key, device_changes in changes_by_device.items():
        state_changes = device_changes.get("state_changes", {})

        # Determine device type
        device_type = device_key  # Default to key name
        if device_state_after:
            device_info = device_state_after.get("devices", {}).get(device_key, {})
            device_type = device_info.get("device_type", device_key)

        # Get constraints for this device type
        constraints = DEVICE_CONSTRAINTS.get(device_type, {})

        # Check temperature constraints
        for temp_key in ["target_temperature_f", "target_water_temp_f"]:
            if temp_key in state_changes:
                temp_val = state_changes[temp_key].get("after")
                if temp_val is not None:
                    total_checks += 1
                    temp_range = constraints.get("temperature_range_f")
                    if temp_range:
                        try:
                            temp_float = float(temp_val)
                            if temp_range["min"] <= temp_float <= temp_range["max"]:
                                compliant_checks += 1
                            else:
                                violations.append({
                                    "device": device_key,
                                    "property": temp_key,
                                    "value": temp_float,
                                    "constraint": f"must be {temp_range['min']}-{temp_range['max']}°F",
                                    "violation_type": "out_of_range",
                                })
                        except (ValueError, TypeError):
                            pass
                    else:
                        compliant_checks += 1  # No constraint defined, assume compliant

        # Check mode constraints
        if "mode" in state_changes:
            mode_val = state_changes["mode"].get("after")
            if mode_val:
                total_checks += 1
                valid_modes = constraints.get("valid_modes", [])
                if valid_modes:
                    if mode_val.lower() in [m.lower() for m in valid_modes]:
                        compliant_checks += 1
                    else:
                        violations.append({
                            "device": device_key,
                            "property": "mode",
                            "value": mode_val,
                            "constraint": f"must be one of {valid_modes}",
                            "violation_type": "invalid_option",
                        })
                else:
                    compliant_checks += 1  # No constraint defined

        # Check speed constraints (pool pump)
        for speed_key in ["current_speed_rpm", "speed_rpm"]:
            if speed_key in state_changes:
                speed_val = state_changes[speed_key].get("after")
                if speed_val is not None:
                    total_checks += 1
                    speed_range = constraints.get("speed_range_rpm")
                    if speed_range:
                        try:
                            speed_float = float(speed_val)
                            if speed_range["min"] <= speed_float <= speed_range["max"]:
                                compliant_checks += 1
                            else:
                                violations.append({
                                    "device": device_key,
                                    "property": speed_key,
                                    "value": speed_float,
                                    "constraint": f"must be {speed_range['min']}-{speed_range['max']} RPM",
                                    "violation_type": "out_of_range",
                                })
                        except (ValueError, TypeError):
                            pass
                    else:
                        compliant_checks += 1

    compliance_rate = compliant_checks / total_checks if total_checks > 0 else 1.0

    return {
        "compliance_rate": compliance_rate,
        "total_constrained_actions": total_checks,
        "compliant_actions": compliant_checks,
        "violations": violations,
    }


def _parse_time_to_hour(time_str: str) -> Optional[int]:
    """Parse a time string (e.g., '22:00') to hour (0-23)."""
    if not time_str:
        return None
    try:
        parts = str(time_str).split(":")
        return int(parts[0])
    except (ValueError, IndexError, AttributeError):
        return None


def _evaluate_schedule_action(
    device_key: str,
    scheduled_time: str,
    action: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluate if a scheduled action is during optimal hours.

    Uses the TOU utility to check actual rate data for the current month,
    accounting for seasonal variations in peak/off-peak periods.
    For flat rate households, schedule timing is not evaluated.
    """
    hour = _parse_time_to_hour(scheduled_time)

    if hour is None:
        return {
            "device": device_key,
            "action": action or "schedule",
            "value": scheduled_time,
            "evaluation": "invalid_time",
            "is_correct": False,
            "is_optimal": False,
            "reason": f"Could not parse time: {scheduled_time}",
        }

    # Use TOU utility to check rate data
    current_time = get_current_time()
    tou_info = get_tou_classification(hour=hour, dt=current_time)

    if tou_info.is_off_peak:
        return {
            "device": device_key,
            "action": action or "schedule",
            "value": scheduled_time,
            "evaluation": "off_peak",
            "is_correct": True,
            "is_optimal": True,
            "reason": f"Scheduled during off-peak hours ({hour}:00, {tou_info.rate_cents:.1f}¢/kWh)",
        }
    elif tou_info.is_peak:
        return {
            "device": device_key,
            "action": action or "schedule",
            "value": scheduled_time,
            "evaluation": "peak",
            "is_correct": False,
            "is_optimal": False,
            "reason": f"Scheduled during peak hours ({hour}:00, {tou_info.rate_cents:.1f}¢/kWh) - should be off-peak",
        }
    else:
        # Partial peak or flat rate (all hours same rate)
        return {
            "device": device_key,
            "action": action or "schedule",
            "value": scheduled_time,
            "evaluation": "partial_peak",
            "is_correct": True,
            "is_optimal": False,
            "reason": f"Scheduled at {hour}:00 ({tou_info.rate_cents:.1f}¢/kWh)",
        }


def _evaluate_temperature_action(
    device_key: str,
    temperature: float,
    device_type: str = "hvac",
    mode: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluate if a temperature setting is energy-efficient."""
    # Determine which range to use
    if device_type in ["water_heater", "electric_water_heater"]:
        range_key = "water_heater"
        min_temp, max_temp = EFFICIENT_TEMP_RANGES["water_heater"]
    elif mode and "heat" in mode.lower():
        range_key = "hvac_heating"
        min_temp, max_temp = EFFICIENT_TEMP_RANGES["hvac_heating"]
    else:
        # Default to cooling for HVAC
        range_key = "hvac_cooling"
        min_temp, max_temp = EFFICIENT_TEMP_RANGES["hvac_cooling"]

    is_in_range = min_temp <= temperature <= max_temp

    if is_in_range:
        return {
            "device": device_key,
            "action": "set_temperature",
            "value": temperature,
            "evaluation": "efficient",
            "is_correct": True,
            "is_optimal": True,
            "reason": f"Temperature {temperature}°F is in efficient range ({min_temp}-{max_temp}°F)",
        }
    elif temperature < min_temp:
        # Too cold for heating / too aggressive for cooling
        if range_key == "hvac_heating":
            return {
                "device": device_key,
                "action": "set_temperature",
                "value": temperature,
                "evaluation": "too_cold",
                "is_correct": True,  # It's energy-efficient, just uncomfortable
                "is_optimal": False,
                "reason": f"Temperature {temperature}°F is below recommended heating range ({min_temp}°F min)",
            }
        else:  # Cooling
            return {
                "device": device_key,
                "action": "set_temperature",
                "value": temperature,
                "evaluation": "too_aggressive",
                "is_correct": False,
                "is_optimal": False,
                "reason": f"Temperature {temperature}°F is too low for energy efficiency ({min_temp}°F min recommended)",
            }
    else:  # temperature > max_temp
        if range_key == "hvac_cooling":
            return {
                "device": device_key,
                "action": "set_temperature",
                "value": temperature,
                "evaluation": "too_warm",
                "is_correct": True,  # It's energy-efficient, just warm
                "is_optimal": False,
                "reason": f"Temperature {temperature}°F is above typical comfort range ({max_temp}°F max)",
            }
        else:  # Heating or water heater
            return {
                "device": device_key,
                "action": "set_temperature",
                "value": temperature,
                "evaluation": "too_high",
                "is_correct": False,
                "is_optimal": False,
                "reason": f"Temperature {temperature}°F is above efficient range ({max_temp}°F max recommended)",
            }


def _evaluate_power_action(
    device_key: str,
    power_before: Optional[str],
    power_after: str,
    device_type: str = "unknown",
) -> Dict[str, Any]:
    """Evaluate if a power on/off action was appropriate.

    For energy optimization, turning off unused devices is generally good.
    Turning on high-power devices during peak hours may be suboptimal.
    """
    current_time = get_current_time()
    hour = current_time.hour
    tou_info = get_tou_classification(hour=hour, dt=current_time)

    # High-power devices that should ideally not run during peak
    high_power_devices = ["hvac", "ev_charger", "water_heater", "clothes_dryer", "pool_pump"]
    is_high_power = device_type in high_power_devices or device_key in high_power_devices

    if power_after in ["off", "standby"]:
        # Turning off is generally energy-efficient
        return {
            "device": device_key,
            "action": "power_off",
            "value": power_after,
            "evaluation": "energy_saving",
            "is_correct": True,
            "is_optimal": True,
            "reason": f"Turning off {device_key} saves energy",
        }
    elif power_after == "on":
        if is_high_power and tou_info.is_peak:
            # Turning on high-power device during peak is suboptimal
            return {
                "device": device_key,
                "action": "power_on",
                "value": power_after,
                "evaluation": "peak_usage",
                "is_correct": True,  # Valid action, just not optimal timing
                "is_optimal": False,
                "reason": f"Turning on {device_key} during peak hours ({hour}:00, {tou_info.rate_cents:.1f}¢/kWh) - consider off-peak",
            }
        else:
            return {
                "device": device_key,
                "action": "power_on",
                "value": power_after,
                "evaluation": "acceptable",
                "is_correct": True,
                "is_optimal": not is_high_power or tou_info.is_off_peak,
                "reason": f"Power on {device_key}" + (f" during off-peak ({tou_info.rate_cents:.1f}¢/kWh)" if tou_info.is_off_peak else ""),
            }
    else:
        # Unknown power state
        return {
            "device": device_key,
            "action": "power_change",
            "value": power_after,
            "evaluation": "unknown",
            "is_correct": True,
            "is_optimal": False,
            "reason": f"Power state changed to '{power_after}'",
        }


def _evaluate_mode_action(
    device_key: str,
    mode_before: Optional[str],
    mode_after: str,
    device_type: str = "unknown",
) -> Dict[str, Any]:
    """Evaluate if a mode change was appropriate.

    For HVAC: Check if mode matches season/climate.
    For water heater: Check if mode is energy-efficient.
    """
    current_time = get_current_time()
    month = current_time.month

    # Determine if it's summer (cooling season) or winter (heating season)
    # For Northern Hemisphere: April-October is cooling, November-March is heating
    is_cooling_season = 4 <= month <= 10

    if device_type == "hvac" or device_key == "hvac":
        guidelines = HVAC_MODE_GUIDELINES.get("hot_dry", HVAC_MODE_GUIDELINES["default"])

        if mode_after in guidelines["always_acceptable"]:
            return {
                "device": device_key,
                "action": "set_mode",
                "value": mode_after,
                "evaluation": "acceptable",
                "is_correct": True,
                "is_optimal": True,
                "reason": f"HVAC mode '{mode_after}' is always appropriate",
            }
        elif is_cooling_season and mode_after in guidelines["summer_modes"]:
            return {
                "device": device_key,
                "action": "set_mode",
                "value": mode_after,
                "evaluation": "season_appropriate",
                "is_correct": True,
                "is_optimal": True,
                "reason": f"HVAC mode '{mode_after}' is appropriate for cooling season",
            }
        elif not is_cooling_season and mode_after in guidelines["winter_modes"]:
            return {
                "device": device_key,
                "action": "set_mode",
                "value": mode_after,
                "evaluation": "season_appropriate",
                "is_correct": True,
                "is_optimal": True,
                "reason": f"HVAC mode '{mode_after}' is appropriate for heating season",
            }
        elif is_cooling_season and mode_after == "heat":
            return {
                "device": device_key,
                "action": "set_mode",
                "value": mode_after,
                "evaluation": "season_mismatch",
                "is_correct": False,
                "is_optimal": False,
                "reason": f"HVAC mode 'heat' during cooling season (month {month}) - unusual",
            }
        elif not is_cooling_season and mode_after == "cool":
            return {
                "device": device_key,
                "action": "set_mode",
                "value": mode_after,
                "evaluation": "season_mismatch",
                "is_correct": False,
                "is_optimal": False,
                "reason": f"HVAC mode 'cool' during heating season (month {month}) - unusual",
            }
        else:
            return {
                "device": device_key,
                "action": "set_mode",
                "value": mode_after,
                "evaluation": "unknown_mode",
                "is_correct": True,
                "is_optimal": False,
                "reason": f"HVAC mode changed to '{mode_after}'",
            }

    elif device_type == "water_heater" or "water_heater" in device_key:
        # Water heater mode evaluation based on efficiency
        efficiency_rank = WATER_HEATER_MODE_EFFICIENCY.get(mode_after, 99)

        if mode_after == "heat_pump":
            return {
                "device": device_key,
                "action": "set_mode",
                "value": mode_after,
                "evaluation": "most_efficient",
                "is_correct": True,
                "is_optimal": True,
                "reason": "Heat pump mode is most energy-efficient (COP ~3-4)",
            }
        elif mode_after == "hybrid":
            return {
                "device": device_key,
                "action": "set_mode",
                "value": mode_after,
                "evaluation": "efficient",
                "is_correct": True,
                "is_optimal": True,
                "reason": "Hybrid mode balances efficiency with faster recovery",
            }
        elif mode_after == "electric":
            return {
                "device": device_key,
                "action": "set_mode",
                "value": mode_after,
                "evaluation": "inefficient",
                "is_correct": True,
                "is_optimal": False,
                "reason": "Electric-only mode is less efficient than heat pump modes",
            }
        elif mode_after == "vacation":
            return {
                "device": device_key,
                "action": "set_mode",
                "value": mode_after,
                "evaluation": "energy_saving",
                "is_correct": True,
                "is_optimal": True,
                "reason": "Vacation mode saves energy when away",
            }
        else:
            return {
                "device": device_key,
                "action": "set_mode",
                "value": mode_after,
                "evaluation": "unknown_mode",
                "is_correct": True,
                "is_optimal": False,
                "reason": f"Water heater mode changed to '{mode_after}'",
            }

    else:
        # Generic mode change for other devices
        return {
            "device": device_key,
            "action": "set_mode",
            "value": mode_after,
            "evaluation": "mode_change",
            "is_correct": True,
            "is_optimal": False,
            "reason": f"Mode changed to '{mode_after}'",
        }


def _evaluate_speed_action(
    device_key: str,
    speed_before: Optional[float],
    speed_after: float,
    device_type: str = "unknown",
) -> Dict[str, Any]:
    """Evaluate if a speed setting was appropriate.

    For pool pumps: Lower speeds are more efficient due to affinity laws (power ~ speed^3).
    Running at 1/2 speed uses only 1/8 the power.
    """
    current_time = get_current_time()
    hour = current_time.hour
    tou_info = get_tou_classification(hour=hour, dt=current_time)

    if device_type == "pool_pump" or "pool" in device_key:
        min_efficient, max_efficient = POOL_PUMP_SPEED_RANGES["efficient_filtration"]
        min_normal, max_normal = POOL_PUMP_SPEED_RANGES["normal_filtration"]

        if speed_after <= max_efficient:
            # Low speed is most efficient
            if tou_info.is_off_peak:
                return {
                    "device": device_key,
                    "action": "set_speed",
                    "value": speed_after,
                    "evaluation": "optimal",
                    "is_correct": True,
                    "is_optimal": True,
                    "reason": f"Low speed ({speed_after} RPM) during off-peak is optimal for efficiency",
                }
            else:
                return {
                    "device": device_key,
                    "action": "set_speed",
                    "value": speed_after,
                    "evaluation": "efficient_speed",
                    "is_correct": True,
                    "is_optimal": False,  # Good speed, but could be better timing
                    "reason": f"Low speed ({speed_after} RPM) is efficient; consider running during off-peak",
                }
        elif speed_after <= max_normal:
            # Medium speed
            return {
                "device": device_key,
                "action": "set_speed",
                "value": speed_after,
                "evaluation": "moderate",
                "is_correct": True,
                "is_optimal": False,
                "reason": f"Medium speed ({speed_after} RPM) - consider lower speed for better efficiency",
            }
        else:
            # High speed
            return {
                "device": device_key,
                "action": "set_speed",
                "value": speed_after,
                "evaluation": "high_power",
                "is_correct": True,
                "is_optimal": False,
                "reason": f"High speed ({speed_after} RPM) uses significantly more power - use only when needed",
            }

    else:
        # Generic speed change for other devices
        return {
            "device": device_key,
            "action": "set_speed",
            "value": speed_after,
            "evaluation": "speed_change",
            "is_correct": True,
            "is_optimal": False,
            "reason": f"Speed changed to {speed_after}",
        }
