# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# core/analysis/appliance/base.py
"""Base ApplianceAnalyzer class with core functionality."""
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from datetime import datetime
from utils.logger import setup_logger
from core.analysis.constants import NON_APPLIANCE_COLUMNS, get_appliance_columns

logger = setup_logger()


class ApplianceAnalyzerBase:
    """Base class for appliance analysis with shared utilities."""

    # Reference to shared constants for backward compatibility
    NON_APPLIANCE_COLUMNS = NON_APPLIANCE_COLUMNS

    def get_appliance_columns(self, df: pd.DataFrame) -> List[str]:
        """Get the list of appliance columns from a DataFrame."""
        return get_appliance_columns(df)

    def ensure_timestamp_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure DataFrame has a timestamp column."""
        if 'timestamp' not in df.columns:
            if 'local_15min' in df.columns:
                df = df.copy()
                df['timestamp'] = pd.to_datetime(df['local_15min'])
            else:
                raise ValueError("No timestamp column available for analysis")
        return df

    def ensure_hour_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure DataFrame has an hour column."""
        if 'hour' not in df.columns:
            df = df.copy()
            df['hour'] = df['timestamp'].dt.hour
        return df

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze appliance-specific patterns including usage frequency, consistency, and peak power.

        Returns a dict with:
        - consumption_rankings: List of appliances sorted by total consumption
        - insights: List of key insights
        - appliance_details: Detailed analysis per appliance
        """
        try:
            logger.info("Starting appliance pattern analysis")
            start_time = datetime.now()

            # Ensure timestamp column exists
            df = self.ensure_timestamp_column(df)

            # Ensure hour column exists
            df = self.ensure_hour_column(df)

            # Get appliance columns
            appliance_cols = self.get_appliance_columns(df)
            logger.info(f"Found {len(appliance_cols)} appliance columns to analyze")

            if not appliance_cols:
                return {
                    'consumption_rankings': [],
                    'insights': ["No appliance columns found in the data"],
                    'appliance_details': {}
                }

            # Calculate total consumption for each appliance
            # Data is in 15-min intervals, so divide by 4 to get kWh
            appliance_totals = {}
            for col in appliance_cols:
                total = df[col].sum() / 4  # Convert to kWh
                appliance_totals[col] = total

            # Calculate total consumption across all appliances
            grand_total = sum(appliance_totals.values())

            # Create rankings
            rankings = []
            for appliance, total_kwh in sorted(appliance_totals.items(), key=lambda x: x[1], reverse=True):
                pct = (total_kwh / grand_total * 100) if grand_total > 0 else 0
                rankings.append({
                    'appliance': appliance,
                    'total_kwh': total_kwh,
                    'percentage': pct
                })

            # Generate insights
            insights = self._generate_insights(df, appliance_cols, rankings)

            # Detailed analysis per appliance (top 5)
            details = {}
            for appliance in appliance_cols[:5]:
                try:
                    details[appliance] = {
                        'total_kwh': appliance_totals.get(appliance, 0),
                        'daily_frequency': self._calculate_daily_frequency(df, appliance),
                        'peak_power_kw': df[appliance].max(),
                        'avg_power_kw': df[appliance].mean(),
                    }
                except Exception as e:
                    logger.warning(f"Error analyzing {appliance}: {str(e)}")
                    details[appliance] = {"error": str(e)}

            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"Appliance analysis completed. Duration: {duration:.2f}s")

            return {
                'consumption_rankings': rankings,
                'insights': insights,
                'appliance_details': details
            }

        except Exception as e:
            logger.error(f"Error in appliance analysis: {str(e)}")
            raise

    def _generate_insights(self, df: pd.DataFrame, appliance_cols: List[str], rankings: List[Dict]) -> List[str]:
        """Generate key insights from appliance analysis."""
        insights = []

        if not rankings:
            return ["No appliance data available for analysis"]

        # Top consumer insight
        top = rankings[0]
        insights.append(f"{top['appliance']} is the top energy consumer at {top['total_kwh']:.1f} kWh ({top['percentage']:.1f}% of total)")

        # Check if top 3 make up most of the consumption
        if len(rankings) >= 3:
            top3_pct = sum(r['percentage'] for r in rankings[:3])
            if top3_pct > 70:
                insights.append(f"Top 3 appliances account for {top3_pct:.0f}% of total consumption")

        # Check for standby/phantom loads (non-zero minimums)
        for appliance in appliance_cols[:5]:
            min_usage = df[appliance].min()
            if min_usage > 0.01:  # More than 10W standby
                insights.append(f"{appliance} has a {min_usage*1000:.0f}W standby load that could be reduced")
                break

        return insights

    def _calculate_daily_frequency(self, df: pd.DataFrame, appliance: str) -> float:
        """
        Calculate the frequency of daily usage for an appliance.

        Args:
            df: DataFrame containing appliance data
            appliance: Name of the appliance column

        Returns:
            float: Usage frequency (0-1) representing proportion of days the appliance was used
        """
        try:
            # Group by date and check if appliance was used (consumption > 0)
            daily_usage = df.groupby(df['timestamp'].dt.date)[appliance].apply(lambda x: (x > 0).any())

            # Calculate frequency
            total_days = len(daily_usage)
            days_used = daily_usage.sum()
            frequency = days_used / total_days if total_days > 0 else 0

            logger.info(f"Daily frequency for {appliance}: {frequency:.2f}")
            return frequency

        except Exception as e:
            logger.error(f"Error calculating daily frequency for {appliance}: {str(e)}")
            raise
