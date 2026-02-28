# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# core/analysis/constants.py
"""Shared constants for energy analysis modules."""
from typing import Set, List, Dict
import pandas as pd

# Season definitions for energy data analysis
# Maps month (1-12) to season name
SEASON_NAMES: Dict[int, str] = {
    12: "winter", 1: "winter", 2: "winter",
    3: "spring", 4: "spring", 5: "spring",
    6: "summer", 7: "summer", 8: "summer",
    9: "fall", 10: "fall", 11: "fall",
}

# Columns that are not appliance data columns
# These are excluded when identifying appliance columns in DataFrames
NON_APPLIANCE_COLUMNS: Set[str] = {
    # Original data columns
    'local_15min', 'dataid', 'grid', 'solar', 'solar2',
    'leg1v', 'leg2v', 'Solar power generation 1', 'Solar power generation 2',
    # Time-based feature columns
    'timestamp', 'hour', 'day', 'day_of_week', 'is_weekend',
    # Consumption metric columns
    'total_consumption', 'net_consumption', 'solar_contribution',
    'grid_dependency', 'is_exporting', 'export_amount',
    # Rate and cost columns
    'rate', 'interval_cost', 'rate_period',
    # Time-of-use columns
    'time_of_day', 'peak_period',
    # Solar columns
    'solar_generation',
    # Temporary/internal columns
    '_temp_consumption'
}


def get_appliance_columns(df: pd.DataFrame) -> List[str]:
    """
    Get the list of appliance columns from a DataFrame.

    Args:
        df: DataFrame containing energy data

    Returns:
        List of column names that represent appliance data
    """
    appliance_cols = []
    for col in df.columns:
        if col not in NON_APPLIANCE_COLUMNS and not col.endswith('_cost'):
            if pd.api.types.is_numeric_dtype(df[col]):
                appliance_cols.append(col)
    return appliance_cols
