# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
"""Threshold handler for filtering appliance standby power."""
import os
from typing import Dict, Optional
import pandas as pd
from utils.logger import setup_logger

logger = setup_logger()


class ThresholdHandler:
    """Handles loading and applying appliance power thresholds."""

    def __init__(self):
        self._thresholds: Dict[str, float] = {}
        self._column_mapping: Dict[str, str] = {}

    def load_thresholds(self, file_path: str) -> Dict[str, float]:
        """
        Load appliance thresholds from a CSV file.

        Args:
            file_path: Path to the thresholds CSV file

        Returns:
            Dict mapping appliance names to threshold values (in kW)
        """
        if not os.path.exists(file_path):
            logger.warning(f"Thresholds file not found: {file_path}")
            return {}

        try:
            df = pd.read_csv(file_path, encoding='utf-8-sig')  # Handle BOM
            logger.info(f"Loaded thresholds from {file_path}")

            # Expected columns: appliance_name, threshold_kw
            if 'appliance_name' not in df.columns or 'threshold_kw' not in df.columns:
                logger.error(f"Invalid threshold file format. Expected columns: appliance_name, threshold_kw")
                return {}

            self._thresholds = dict(zip(df['appliance_name'], df['threshold_kw']))

            # Build column mapping (threshold file names -> actual column names)
            self._build_column_mapping()

            logger.info(f"Loaded {len(self._thresholds)} appliance thresholds")
            return self._thresholds

        except Exception as e:
            logger.error(f"Error loading thresholds: {e}")
            return {}

    def _build_column_mapping(self):
        """Build mapping between threshold file appliance names and data column names."""
        # Map threshold file names to data column names
        # Threshold file uses "HVAC unit" but data uses "HVAC"
        self._column_mapping = {
            'HVAC unit': 'HVAC',
            'Electric vehicle charger': 'Electric vehicle charger',
            'Washing machine': 'Washing machine',
            'Dishwasher': 'Dishwasher',
            'Clothes dryer': 'Clothes dryer',
            'Microwave': 'Microwave',
            'Oven 1': 'Oven 1',
            'Oven 2': 'Oven 2',
            'Pool pump': 'Pool pump',
            'Cooktop': 'Cooktop',
            'Refrigerator': 'Refrigerator',
            'Electric water heater': 'Electric water heater',
            'Kitchen sink garbage disposal': 'Kitchen sink garbage disposal',
        }

    def get_threshold(self, appliance_name: str) -> Optional[float]:
        """
        Get the threshold for a specific appliance.

        Args:
            appliance_name: Name of the appliance (data column name)

        Returns:
            Threshold value in kW, or None if not found
        """
        # First try direct lookup
        if appliance_name in self._thresholds:
            return self._thresholds[appliance_name]

        # Try reverse mapping (data column name -> threshold file name)
        for threshold_name, column_name in self._column_mapping.items():
            if column_name == appliance_name:
                return self._thresholds.get(threshold_name)

        return None

    def get_column_thresholds(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Get thresholds mapped to actual DataFrame column names.

        Args:
            df: DataFrame with appliance columns

        Returns:
            Dict mapping column names to threshold values
        """
        result = {}
        for threshold_name, threshold_value in self._thresholds.items():
            # Get the corresponding column name
            column_name = self._column_mapping.get(threshold_name, threshold_name)
            if column_name in df.columns:
                result[column_name] = threshold_value
        return result

    def apply_thresholds(
        self,
        df: pd.DataFrame,
        mode: str = 'zero_below'
    ) -> pd.DataFrame:
        """
        Apply thresholds to filter out standby power readings.

        Args:
            df: DataFrame with appliance columns
            mode: How to handle values below threshold:
                - 'zero_below': Set values below threshold to 0 (default)
                - 'flag_only': Add boolean columns indicating active usage
                - 'both': Both zero out and add flag columns

        Returns:
            DataFrame with thresholds applied
        """
        df = df.copy()
        column_thresholds = self.get_column_thresholds(df)

        if not column_thresholds:
            logger.warning("No matching thresholds found for data columns")
            return df

        logger.info(f"Applying thresholds to {len(column_thresholds)} appliance columns (mode: {mode})")

        for col, threshold in column_thresholds.items():
            if col not in df.columns:
                continue

            if mode in ('zero_below', 'both'):
                # Zero out values below threshold (standby power)
                original_sum = df[col].sum()
                df[col] = df[col].where(df[col] >= threshold, 0)
                filtered_sum = df[col].sum()

                reduction_pct = ((original_sum - filtered_sum) / original_sum * 100) if original_sum > 0 else 0
                logger.debug(f"{col}: threshold={threshold}kW, filtered {reduction_pct:.1f}% as standby")

            if mode in ('flag_only', 'both'):
                # Add boolean column indicating when appliance is actively in use
                df[f'{col}_active'] = df[col] >= threshold

        return df

    def get_active_usage_stats(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """
        Get statistics about active vs standby usage for each appliance.

        Args:
            df: DataFrame with appliance columns (before threshold filtering)

        Returns:
            Dict with stats for each appliance
        """
        column_thresholds = self.get_column_thresholds(df)
        stats = {}

        for col, threshold in column_thresholds.items():
            if col not in df.columns:
                continue

            total_readings = len(df)
            active_readings = (df[col] >= threshold).sum()
            standby_readings = total_readings - active_readings

            total_kwh = df[col].sum() / 4  # 15-min intervals
            active_kwh = df[df[col] >= threshold][col].sum() / 4
            standby_kwh = total_kwh - active_kwh

            stats[col] = {
                'threshold_kw': threshold,
                'total_readings': total_readings,
                'active_readings': active_readings,
                'active_pct': (active_readings / total_readings * 100) if total_readings > 0 else 0,
                'standby_readings': standby_readings,
                'standby_pct': (standby_readings / total_readings * 100) if total_readings > 0 else 0,
                'total_kwh': total_kwh,
                'active_kwh': active_kwh,
                'standby_kwh': standby_kwh,
                'standby_kwh_pct': (standby_kwh / total_kwh * 100) if total_kwh > 0 else 0,
            }

        return stats
