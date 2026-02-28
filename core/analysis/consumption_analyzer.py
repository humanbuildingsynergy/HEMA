# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
from typing import Dict, Any, List
import pandas as pd
from utils.logger import setup_logger

logger = setup_logger()


class ConsumptionAnalyzer:
    """Handles analysis of overall consumption patterns."""

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze overall consumption patterns.

        Args:
            df: DataFrame containing energy consumption data

        Returns:
            Dict containing consumption metrics and insights
        """
        try:
            logger.info("Analyzing overall consumption patterns")

            # Determine the consumption column to use
            if 'net_consumption' in df.columns:
                consumption_col = 'net_consumption'
            elif 'total_consumption' in df.columns:
                consumption_col = 'total_consumption'
            else:
                # Fall back to summing numeric appliance columns
                logger.warning("No consumption column found, calculating from appliances")
                non_appliance = {
                    'local_15min', 'timestamp', 'hour', 'day', 'day_of_week',
                    'is_weekend', 'dataid', 'grid', 'solar', 'solar2',
                    'Solar power generation 1', 'Solar power generation 2'
                }
                appliance_cols = [c for c in df.columns
                                  if c not in non_appliance and pd.api.types.is_numeric_dtype(df[c])]
                if appliance_cols:
                    df['_temp_consumption'] = df[appliance_cols].sum(axis=1)
                    consumption_col = '_temp_consumption'
                else:
                    raise ValueError("No consumption data available for analysis")

            # Ensure timestamp column exists
            if 'timestamp' not in df.columns:
                if 'local_15min' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['local_15min'])
                else:
                    raise ValueError("No timestamp column available for analysis")

            # Calculate summary statistics
            total_kwh = df[consumption_col].sum()
            # 15-min intervals, so divide by 4 to get kWh
            total_kwh_actual = total_kwh / 4

            # Calculate average daily using timestamp span (matches ground truth)
            # Using timestamps (not dates) handles partial days correctly
            daily_totals = df.groupby(df['timestamp'].dt.date)[consumption_col].sum() / 4
            min_ts = df['timestamp'].min()
            max_ts = df['timestamp'].max()
            timestamp_span_days = (max_ts - min_ts).days + 1
            avg_daily = total_kwh_actual / max(timestamp_span_days, 1)

            peak_demand = df[consumption_col].max()
            base_load = df[consumption_col].quantile(0.1)

            # Avoid division by zero
            if peak_demand > 0:
                load_factor = df[consumption_col].mean() / peak_demand
            else:
                load_factor = 0

            # Hourly profile analysis
            hourly_avg = df.groupby('hour')[consumption_col].mean() if 'hour' in df.columns else None
            daily_profile = {}
            if hourly_avg is not None and len(hourly_avg) > 0:
                peak_hour = hourly_avg.idxmax()
                off_peak_hour = hourly_avg.idxmin()

                # Morning peak (6-10 AM)
                morning_hours = hourly_avg.loc[hourly_avg.index.isin(range(6, 11))]
                morning_peak = morning_hours.idxmax() if len(morning_hours) > 0 else None

                # Evening peak (5-9 PM)
                evening_hours = hourly_avg.loc[hourly_avg.index.isin(range(17, 22))]
                evening_peak = evening_hours.idxmax() if len(evening_hours) > 0 else None

                daily_profile = {
                    'peak_hour': f"{peak_hour}:00",
                    'off_peak_hour': f"{off_peak_hour}:00",
                    'morning_peak': f"{morning_peak}:00" if morning_peak else "N/A",
                    'evening_peak': f"{evening_peak}:00" if evening_peak else "N/A",
                }

            # Generate patterns description
            patterns = self._identify_patterns(df, consumption_col)

            return {
                'summary': {
                    'total_kwh': total_kwh_actual,
                    'avg_daily_kwh': avg_daily,
                    'peak_demand_kw': peak_demand,
                    'base_load_kw': base_load,
                    'load_factor': load_factor,
                },
                'daily_profile': daily_profile,
                'patterns': patterns,
            }

        except Exception as e:
            logger.error(f"Error in consumption analysis: {str(e)}")
            raise

    def _identify_patterns(self, df: pd.DataFrame, consumption_col: str) -> str:
        """Identify notable consumption patterns."""
        patterns = []

        if 'is_weekend' in df.columns:
            weekday_avg = df[df['is_weekend'] == 0][consumption_col].mean()
            weekend_avg = df[df['is_weekend'] == 1][consumption_col].mean()

            if weekend_avg > weekday_avg * 1.1:
                patterns.append("Higher weekend consumption detected")
            elif weekday_avg > weekend_avg * 1.1:
                patterns.append("Higher weekday consumption detected")

        if 'hour' in df.columns:
            night_avg = df[df['hour'].isin(range(0, 6))][consumption_col].mean()
            day_avg = df[df['hour'].isin(range(9, 17))][consumption_col].mean()

            if night_avg > day_avg * 0.5:
                patterns.append("Significant overnight baseload detected")

        if not patterns:
            patterns.append("Standard consumption pattern with no unusual variations")

        return "\n".join(f"- {p}" for p in patterns)