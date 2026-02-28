# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# core/analysis/appliance/peak_power.py
"""Peak power analysis for appliances."""
from typing import Dict, Any
import pandas as pd
import numpy as np
from utils.logger import setup_logger

logger = setup_logger()


class PeakPowerAnalyzer:
    """Analyzes peak power consumption patterns for appliances."""

    def analyze_peak_power(self, df: pd.DataFrame, appliance: str) -> Dict[str, Any]:
        """
        Analyze power consumption during peak periods for an appliance.

        Args:
            df: DataFrame containing appliance data
            appliance: Name of the appliance column

        Returns:
            Dict containing peak power statistics:
                - average_peak_power: Mean power during peak periods
                - peak_power_variance: Variance in peak period power
                - max_peak_power: Maximum observed peak power
        """
        try:
            logger.info(f"Analyzing peak power consumption for {appliance}")

            # Ensure hour column exists
            if 'hour' not in df.columns:
                if 'timestamp' not in df.columns:
                    if 'local_15min' in df.columns:
                        df = df.copy()
                        df['timestamp'] = pd.to_datetime(df['local_15min'])
                    else:
                        raise ValueError("No timestamp column available")
                df = df.copy()
                df['hour'] = df['timestamp'].dt.hour

            # Define peak periods (could be customized based on your definition)
            df = df.copy()
            df['peak_period'] = df['hour'].between(17, 21)  # Example: 5PM-9PM

            # Get power values during peak periods
            peak_period_power = df[df['peak_period']][appliance]

            if peak_period_power.empty:
                return {
                    "error": "No data found for peak periods"
                }

            # Calculate statistics
            avg_peak_power = peak_period_power.mean()
            peak_power_variance = peak_period_power.var()
            max_peak_power = peak_period_power.max()

            results = {
                'average_peak_power': avg_peak_power,
                'peak_power_variance': peak_power_variance,
                'peak_power_std': np.sqrt(peak_power_variance),  # Standard deviation
                'max_peak_power': max_peak_power,
                'min_peak_power': peak_period_power.min(),
                'peak_power_percentiles': {
                    '25th': peak_period_power.quantile(0.25),
                    '50th': peak_period_power.quantile(0.50),
                    '75th': peak_period_power.quantile(0.75)
                }
            }

            logger.info(f"Peak power analysis completed for {appliance}")
            logger.debug(f"Peak power stats for {appliance}: avg={avg_peak_power:.2f}, var={peak_power_variance:.2f}")

            return results

        except Exception as e:
            logger.error(f"Error analyzing peak power for {appliance}: {str(e)}")
            raise
