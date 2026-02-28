# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/metrics/action_constants.py
"""Domain knowledge constants for device action evaluation."""


# Energy-efficient temperature ranges (Fahrenheit)
EFFICIENT_TEMP_RANGES = {
    "hvac_cooling": (76, 82),  # DOE recommends 78°F when home
    "hvac_heating": (62, 70),  # DOE recommends 68°F when home
    "water_heater": (110, 120),  # 120°F max recommended
}

# Pool pump speed recommendations (RPM)
# Lower speeds are more energy-efficient due to affinity laws (power ~ speed^3)
POOL_PUMP_SPEED_RANGES = {
    "efficient_filtration": (450, 1500),  # Low speed for daily filtration
    "normal_filtration": (1500, 2200),  # Medium speed
    "cleaning_vacuuming": (2200, 3000),  # Higher speed for cleaning
    "max_power": (3000, 3450),  # Max speed for spa jets, water features
}

# HVAC mode appropriateness based on climate/season
# For Hot-Dry climate like Arizona, cooling is typically needed most of the year
HVAC_MODE_GUIDELINES = {
    "hot_dry": {
        "summer_modes": ["cool", "auto"],  # April-October
        "winter_modes": ["heat", "auto"],  # November-March
        "always_acceptable": ["auto", "fan_only", "off"],
    },
    "default": {
        "summer_modes": ["cool", "auto"],
        "winter_modes": ["heat", "auto"],
        "always_acceptable": ["auto", "fan_only", "off"],
    },
}

# Water heater mode efficiency ranking (most to least efficient)
WATER_HEATER_MODE_EFFICIENCY = {
    "heat_pump": 1,  # Most efficient (COP ~3-4)
    "hybrid": 2,  # Good efficiency, faster recovery
    "electric": 3,  # Least efficient (COP ~1)
    "vacation": 4,  # Energy saving when away
    "off": 5,  # No energy use
}

# Device constraint definitions (min/max values, valid options)
# These should match the device_config but provide fallback defaults
DEVICE_CONSTRAINTS = {
    "hvac": {
        "temperature_range_f": {"min": 60, "max": 85},
        "valid_modes": ["off", "cool", "heat", "auto", "fan_only"],
        "valid_fan_modes": ["auto", "on", "circulate"],
    },
    "water_heater": {
        "temperature_range_f": {"min": 95, "max": 140},
        "valid_modes": ["heat_pump", "hybrid", "electric", "vacation", "off"],
    },
    "pool_pump": {
        "speed_range_rpm": {"min": 450, "max": 3450},
    },
    "ev_charger": {
        "charge_limit_range": {"min": 50, "max": 100},
    },
}
