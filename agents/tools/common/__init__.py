# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.

"""
Common utilities for agent tools.

This module provides shared utilities to reduce code duplication across analysis,
control, and knowledge tools:

- cache_keys: Constants for consistent cache access
- time_manager: Time management for device control
- formatters: Response building and formatting utilities
- data_period_utils: Data period extraction and validation
- parameters: Parameter parsing and validation
"""

# Cache key constants
from .cache_keys import (
    CURRENT_TIME_KEY,
    SIMULATED_TIME_KEY,
    TIME_OFFSET_KEY,
    ENERGY_DATAFRAME_KEY,
    PROCESSED_DATAFRAME_KEY,
    TIMESTAMP_COLUMN_KEY,
    DATA_PERIOD_INFO_KEY,
    APPLIANCE_THRESHOLDS_KEY,
    CACHED_ANALYSIS_RESULTS_KEY,
    HOUSEHOLD_PROFILE_KEY,
    DEVICE_CONFIG_KEY,
    DEVICE_STATES_KEY,
    RATE_DATA_KEY,
    TOU_PERIODS_KEY,
    CONSUMPTION_ANALYSIS_KEY,
    FREQUENCY_ANALYSIS_KEY,
    SOLAR_ANALYSIS_KEY,
    AGGREGATION_ANALYSIS_KEY,
)

# Time management
from .time_manager import (
    get_current_time,
    set_simulated_time,
    reset_time,
    get_simulated_time,
    is_simulated_time_set,
)

# Response formatting
from .formatters import (
    ResponseBuilder,
    format_value_with_unit,
    format_percentage,
    format_date_range,
)

# Data period utilities
from .data_period_utils import (
    find_timestamp_column,
    get_data_period_info,
    get_data_scope_string,
    format_data_period_header,
    validate_data_loaded,
    get_or_calculate_processed_df,
)

# Parameter parsing
from .parameters import (
    parse_appliance_list,
    parse_time_range,
    parse_date_range,
    parse_device_name,
    parse_boolean,
    parse_numeric_range,
    validate_optional_string,
)

__all__ = [
    # Cache keys
    "CURRENT_TIME_KEY",
    "SIMULATED_TIME_KEY",
    "TIME_OFFSET_KEY",
    "ENERGY_DATAFRAME_KEY",
    "PROCESSED_DATAFRAME_KEY",
    "TIMESTAMP_COLUMN_KEY",
    "DATA_PERIOD_INFO_KEY",
    "APPLIANCE_THRESHOLDS_KEY",
    "CACHED_ANALYSIS_RESULTS_KEY",
    "HOUSEHOLD_PROFILE_KEY",
    "DEVICE_CONFIG_KEY",
    "DEVICE_STATES_KEY",
    "RATE_DATA_KEY",
    "TOU_PERIODS_KEY",
    "CONSUMPTION_ANALYSIS_KEY",
    "FREQUENCY_ANALYSIS_KEY",
    "SOLAR_ANALYSIS_KEY",
    "AGGREGATION_ANALYSIS_KEY",
    # Time management
    "get_current_time",
    "set_simulated_time",
    "reset_time",
    "get_simulated_time",
    "is_simulated_time_set",
    # Response formatting
    "ResponseBuilder",
    "format_value_with_unit",
    "format_percentage",
    "format_date_range",
    # Data period utilities
    "find_timestamp_column",
    "get_data_period_info",
    "get_data_scope_string",
    "format_data_period_header",
    "validate_data_loaded",
    "get_or_calculate_processed_df",
    # Parameter parsing
    "parse_appliance_list",
    "parse_time_range",
    "parse_date_range",
    "parse_device_name",
    "parse_boolean",
    "parse_numeric_range",
    "validate_optional_string",
]
