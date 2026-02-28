# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.

"""
Cache key constants for consistent cache access across modules.

This module defines all cache keys used throughout the agent tools,
providing a single source of truth to prevent key mismatches.
"""

# Time-related cache keys
CURRENT_TIME_KEY = "current_time"
SIMULATED_TIME_KEY = "simulated_time"
TIME_OFFSET_KEY = "time_offset"

# Energy data cache keys
ENERGY_DATAFRAME_KEY = "energy_df"
PROCESSED_DATAFRAME_KEY = "processed_df"
TIMESTAMP_COLUMN_KEY = "timestamp_column"
DATA_PERIOD_INFO_KEY = "data_period_info"
APPLIANCE_THRESHOLDS_KEY = "appliance_thresholds"
CACHED_ANALYSIS_RESULTS_KEY = "analysis_results"
HOUSEHOLD_PROFILE_KEY = "household_profile"

# Device state cache keys
DEVICE_CONFIG_KEY = "device_config"
DEVICE_STATES_KEY = "device_states"

# TOU/Rate cache keys
RATE_DATA_KEY = "rate_data"
TOU_PERIODS_KEY = "tou_periods"

# Analysis cache keys
CONSUMPTION_ANALYSIS_KEY = "consumption_analysis"
FREQUENCY_ANALYSIS_KEY = "frequency_analysis"
SOLAR_ANALYSIS_KEY = "solar_analysis"
AGGREGATION_ANALYSIS_KEY = "aggregation_analysis"
