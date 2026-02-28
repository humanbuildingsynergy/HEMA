# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/tools/control_tools/device_energy.py
"""Energy query tools for device control.

This module provides tools for querying energy consumption information
for individual devices and the entire home.
"""
from langchain_core.tools import tool

from utils.logger import setup_logger
from .device_state import load_device_config
from .device_utils import find_device, format_key, format_value

logger = setup_logger()


@tool
def get_device_energy(device_name: str) -> str:
    """
    Get detailed energy consumption information for a specific device.

    Args:
        device_name: Name or type of device

    Returns:
        Energy consumption data including power ratings, efficiency, and usage statistics.
    """
    logger.info(f"Getting energy info for: {device_name}")

    device_key, device = find_device(device_name)
    if not device:
        config = load_device_config()
        available = list(config.get("devices", {}).keys())
        return f"Device '{device_name}' not found.\n\n**Available devices:** {', '.join(available)}"

    name = device.get("display_name", device_key)
    energy = device.get("energy_info", {})

    if not energy:
        return f"No energy information available for {name}."

    lines = [f"## {name} - Energy Information", ""]

    for key, value in energy.items():
        lines.append(f"- **{format_key(key)}:** {format_value(key, value)}")

    return "\n".join(lines)


@tool
def get_all_devices_energy() -> str:
    """
    Get an energy consumption summary for all devices in the home.

    Returns:
        Table showing power ratings and daily consumption for all devices,
        with total usage and estimated daily cost.
    """
    logger.info("Getting energy summary for all devices")

    config = load_device_config()
    devices = config.get("devices", {})
    home_name = config.get("home_name", "Home")

    lines = [
        f"## {home_name} - Energy Summary",
        "",
        "| Device | Rated Power | Avg Daily Usage | Status |",
        "|--------|-------------|-----------------|--------|"
    ]

    total_daily_kwh = 0

    for device_key, device in devices.items():
        name = device.get("display_name", device_key)
        energy = device.get("energy_info", {})
        state = device.get("current_state", {})

        # Get power rating (try multiple keys)
        rated_power = (
            energy.get("rated_power_kw") or
            energy.get("max_power_kw") or
            energy.get("power_at_high_speed_kw") or
            "N/A"
        )
        power_str = f"{rated_power:.1f} kW" if isinstance(rated_power, (int, float)) else rated_power

        # Get daily usage
        daily_usage = energy.get("avg_daily_consumption_kwh", 0)
        if isinstance(daily_usage, (int, float)) and daily_usage > 0:
            total_daily_kwh += daily_usage
            daily_str = f"{daily_usage:.1f} kWh"
        else:
            daily_str = "N/A"

        # Get status
        power_state = state.get("power", "unknown")
        if power_state == "on":
            status = "Running"
        elif power_state in ["off", "standby"]:
            status = power_state.title()
        else:
            status = power_state.title() if isinstance(power_state, str) else "Unknown"

        lines.append(f"| {name} | {power_str} | {daily_str} | {status} |")

    lines.append("")
    lines.append(f"**Total Estimated Daily Usage:** {total_daily_kwh:.1f} kWh")

    # Calculate cost estimate using TOU rates
    tou = config.get("tou_integration", {})
    if tou:
        off_peak_rate = tou.get("off_peak_rate_per_kwh", 0.05)
        peak_periods = tou.get("peak_periods", [{}])
        peak_rate = peak_periods[0].get("rate_per_kwh", 0.20) if peak_periods else 0.20
        # Rough estimate: 60% off-peak, 40% peak
        estimated_cost = total_daily_kwh * (0.6 * off_peak_rate + 0.4 * peak_rate)
        lines.append(f"**Estimated Daily Cost:** ${estimated_cost:.2f}")

    return "\n".join(lines)
