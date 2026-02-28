# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# core/analysis/appliance/consistency.py
"""Consistency analysis for appliance usage patterns."""
from typing import Dict, Any
import pandas as pd
import numpy as np
from utils.logger import setup_logger

logger = setup_logger()


class ConsistencyAnalyzer:
    """Analyzes consistency of appliance usage patterns."""

    def calculate_daily_consistency(self, df: pd.DataFrame, appliance: str) -> Dict[str, float]:
        """
        Calculate the consistency of daily usage patterns for an appliance using RMSE.

        Args:
            df: DataFrame containing appliance data
            appliance: Name of the appliance column

        Returns:
            Dict containing consistency metrics:
                - score: Normalized consistency score (0-1)
                - rmse: Root Mean Square Error from mean profile
        """
        try:
            # Ensure timestamp column exists
            if 'timestamp' not in df.columns:
                if 'local_15min' in df.columns:
                    df = df.copy()
                    df['timestamp'] = pd.to_datetime(df['local_15min'])
                else:
                    raise ValueError("No timestamp column available")

            # Create daily load profiles (96 points per day for 15-min data)
            df = df.copy()
            df['time_of_day'] = df['timestamp'].dt.hour * 4 + df['timestamp'].dt.minute // 15
            daily_profiles = df.pivot_table(
                index='time_of_day',
                columns=df['timestamp'].dt.date,
                values=appliance,
                aggfunc='mean'
            )

            # Calculate mean profile
            mean_profile = daily_profiles.mean(axis=1)

            # Normalize profiles by maximum value for scale-independent comparison
            max_value = daily_profiles.max().max()
            if max_value > 0:
                normalized_profiles = daily_profiles / max_value
                normalized_mean = mean_profile / max_value
            else:
                return {
                    'score': 1.0,
                    'rmse': 0.0
                }  # Perfect consistency if no usage

            # Calculate RMSE between each daily profile and the mean profile
            squared_errors = (normalized_profiles.T - normalized_mean) ** 2
            rmse = np.sqrt(squared_errors.mean().mean())

            # Convert RMSE to a 0-1 score where:
            # 0 RMSE -> 1.0 score (perfect consistency)
            # High RMSE -> score approaches 0 (inconsistent)
            # Using a threshold of 1.0 for maximum reasonable RMSE
            consistency_score = max(0, 1 - rmse)

            result = {
                'score': consistency_score,
                'rmse': rmse
            }

            logger.info(
                f"Daily consistency for {appliance}: "
                f"score={consistency_score:.2f}, RMSE={rmse:.4f}"
            )
            logger.debug(
                f"Detailed consistency metrics for {appliance}:\n"
                f"- Number of days analyzed: {daily_profiles.shape[1]}\n"
                f"- Max profile value: {max_value:.4f}\n"
                f"- Raw RMSE: {rmse:.4f}"
            )

            return result

        except Exception as e:
            logger.error(f"Error calculating daily consistency for {appliance}: {str(e)}")
            raise
