# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# core/analysis/appliance/frequency.py
"""Usage frequency analysis for appliances."""
from typing import Dict, Any, List
import pandas as pd
from utils.logger import setup_logger
from core.analysis.constants import NON_APPLIANCE_COLUMNS, get_appliance_columns

logger = setup_logger()


class UsageFrequencyAnalyzer:
    """Analyzes usage frequency patterns for appliances."""

    # Reference to shared constants for backward compatibility
    NON_APPLIANCE_COLUMNS = NON_APPLIANCE_COLUMNS

    def get_appliance_columns(self, df: pd.DataFrame) -> List[str]:
        """Get the list of appliance columns from a DataFrame."""
        return get_appliance_columns(df)

    def calculate_hourly_usage_frequency(
        self,
        df: pd.DataFrame,
        appliance: str,
        threshold: float
    ) -> pd.DataFrame:
        """
        Calculate hourly usage frequency for an appliance.

        The hourly usage frequency is the sum of binary indicator values
        (True: when above threshold, False: when below threshold) for all
        15-minute intervals within each hour.

        For 15-minute interval data, each hour has 4 intervals, so the
        maximum hourly frequency is 4.

        Args:
            df: DataFrame containing appliance data with timestamp column
            appliance: Name of the appliance column
            threshold: Power threshold in kW to distinguish active vs standby

        Returns:
            DataFrame with columns:
                - date: Date of the measurement
                - hour: Hour of the day (0-23)
                - hourly_frequency: Sum of binary indicators (0-4 for 15-min data)
        """
        try:
            logger.info(f"Calculating hourly usage frequency for {appliance} with threshold {threshold} kW")

            # Ensure timestamp column exists
            if 'timestamp' not in df.columns:
                if 'local_15min' in df.columns:
                    df = df.copy()
                    df['timestamp'] = pd.to_datetime(df['local_15min'])
                else:
                    raise ValueError("No timestamp column available")

            # Create binary indicator: 1 if above threshold, 0 otherwise
            df = df.copy()
            df['is_active'] = (df[appliance] >= threshold).astype(int)

            # Extract date and hour
            df['date'] = df['timestamp'].dt.date
            df['hour'] = df['timestamp'].dt.hour

            # Group by date and hour, sum the binary indicators
            hourly_freq = df.groupby(['date', 'hour'])['is_active'].sum().reset_index()
            hourly_freq.columns = ['date', 'hour', 'hourly_frequency']

            logger.info(f"Calculated hourly frequency for {len(hourly_freq)} date-hour combinations")

            return hourly_freq

        except Exception as e:
            logger.error(f"Error calculating hourly usage frequency for {appliance}: {str(e)}")
            raise

    def calculate_normalized_avg_hourly_frequency(
        self,
        df: pd.DataFrame,
        appliance: str,
        threshold: float,
        num_days: int = None
    ) -> pd.DataFrame:
        """
        Calculate normalized averaged hourly usage frequency.

        The normalized averaged hourly usage frequency is the average of
        hourly usage frequency values over a specified number of days,
        normalized by the maximum possible frequency (4 for 15-min intervals).

        Args:
            df: DataFrame containing appliance data with timestamp column
            appliance: Name of the appliance column
            threshold: Power threshold in kW to distinguish active vs standby
            num_days: Number of days to average over. If None, uses all available days.

        Returns:
            DataFrame with columns:
                - hour: Hour of the day (0-23)
                - avg_hourly_frequency: Average hourly frequency across days
                - normalized_frequency: Normalized to 0-1 range (divided by 4)
                - days_counted: Number of days used in the average
        """
        try:
            logger.info(f"Calculating normalized avg hourly frequency for {appliance}")

            # First calculate hourly usage frequency
            hourly_freq = self.calculate_hourly_usage_frequency(df, appliance, threshold)

            # Filter to most recent num_days if specified
            if num_days is not None:
                unique_dates = sorted(hourly_freq['date'].unique(), reverse=True)
                selected_dates = unique_dates[:num_days]
                hourly_freq = hourly_freq[hourly_freq['date'].isin(selected_dates)]
                logger.info(f"Filtering to {len(selected_dates)} most recent days")

            # Group by hour and calculate average
            avg_freq = hourly_freq.groupby('hour').agg({
                'hourly_frequency': ['mean', 'count']
            }).reset_index()
            avg_freq.columns = ['hour', 'avg_hourly_frequency', 'days_counted']

            # Normalize by maximum possible frequency (4 intervals per hour for 15-min data)
            max_intervals_per_hour = 4
            avg_freq['normalized_frequency'] = avg_freq['avg_hourly_frequency'] / max_intervals_per_hour

            logger.info(f"Calculated normalized avg frequency for {len(avg_freq)} hours")

            return avg_freq

        except Exception as e:
            logger.error(f"Error calculating normalized avg hourly frequency for {appliance}: {str(e)}")
            raise

    def analyze_usage_frequency(
        self,
        df: pd.DataFrame,
        appliances: List[str] = None,
        thresholds: Dict[str, float] = None,
        num_days: int = None
    ) -> Dict[str, Any]:
        """
        Comprehensive usage frequency analysis for multiple appliances.

        Args:
            df: DataFrame containing appliance data
            appliances: List of appliance names to analyze. If None, analyzes top 5 by consumption.
            thresholds: Dict mapping appliance names to threshold values in kW.
                       If None or missing entries, uses default threshold of 0.01 kW.
            num_days: Number of days to include in normalized average. If None, uses all days.

        Returns:
            Dict containing:
                - summary: Overall frequency statistics
                - appliance_profiles: Per-appliance hourly frequency profiles
                - high_usage_hours: Hours with highest appliance activity
                - insights: Key observations about usage patterns
        """
        try:
            logger.info("Starting comprehensive usage frequency analysis")

            # Ensure timestamp column exists
            if 'timestamp' not in df.columns:
                if 'local_15min' in df.columns:
                    df = df.copy()
                    df['timestamp'] = pd.to_datetime(df['local_15min'])
                else:
                    raise ValueError("No timestamp column available")

            # Get appliance columns if not specified
            if appliances is None:
                all_appliances = self.get_appliance_columns(df)
                # Get top 5 by total consumption
                consumption = {col: df[col].sum() for col in all_appliances}
                appliances = sorted(consumption.keys(), key=lambda x: consumption[x], reverse=True)[:5]

            # Default thresholds
            default_threshold = 0.01  # 10W default
            thresholds = thresholds or {}

            appliance_profiles = {}
            all_normalized = []

            for appliance in appliances:
                threshold = thresholds.get(appliance, default_threshold)

                try:
                    # Calculate normalized average hourly frequency
                    norm_freq = self.calculate_normalized_avg_hourly_frequency(
                        df, appliance, threshold, num_days
                    )

                    # Calculate daily frequency for context
                    hourly_freq = self.calculate_hourly_usage_frequency(df, appliance, threshold)

                    # Find peak usage hours (frequency > 0.5 normalized)
                    peak_hours = norm_freq[norm_freq['normalized_frequency'] > 0.5]['hour'].tolist()

                    appliance_profiles[appliance] = {
                        'threshold_kw': threshold,
                        'hourly_profile': norm_freq.to_dict('records'),
                        'peak_usage_hours': peak_hours,
                        'avg_daily_active_hours': norm_freq['avg_hourly_frequency'].sum() / 4,  # Normalize to hours
                        'max_normalized_frequency': norm_freq['normalized_frequency'].max(),
                        'days_analyzed': norm_freq['days_counted'].max() if len(norm_freq) > 0 else 0
                    }

                    # Store for aggregate analysis
                    norm_freq['appliance'] = appliance
                    all_normalized.append(norm_freq)

                except Exception as e:
                    logger.warning(f"Error analyzing {appliance}: {str(e)}")
                    appliance_profiles[appliance] = {'error': str(e)}

            # Aggregate analysis across appliances
            high_usage_hours = {}
            if all_normalized:
                combined = pd.concat(all_normalized, ignore_index=True)
                for hour in range(24):
                    hour_data = combined[combined['hour'] == hour]
                    active_appliances = hour_data[hour_data['normalized_frequency'] > 0.25]['appliance'].tolist()
                    if active_appliances:
                        high_usage_hours[hour] = active_appliances

            # Generate insights
            insights = self._generate_frequency_insights(appliance_profiles, high_usage_hours)

            # Summary statistics
            summary = {
                'appliances_analyzed': len(appliances),
                'days_analyzed': num_days or 'all available',
                'most_active_appliance': max(
                    [(a, p.get('avg_daily_active_hours', 0)) for a, p in appliance_profiles.items() if 'error' not in p],
                    key=lambda x: x[1],
                    default=(None, 0)
                )[0],
                'busiest_hour': max(high_usage_hours.items(), key=lambda x: len(x[1]), default=(None, []))[0] if high_usage_hours else None,
            }

            return {
                'summary': summary,
                'appliance_profiles': appliance_profiles,
                'high_usage_hours': high_usage_hours,
                'insights': insights
            }

        except Exception as e:
            logger.error(f"Error in usage frequency analysis: {str(e)}")
            raise

    def _generate_frequency_insights(
        self,
        appliance_profiles: Dict[str, Any],
        high_usage_hours: Dict[int, List[str]]
    ) -> List[str]:
        """Generate insights from usage frequency analysis."""
        insights = []

        # Most active appliance
        active_appliances = [
            (name, profile.get('avg_daily_active_hours', 0))
            for name, profile in appliance_profiles.items()
            if 'error' not in profile
        ]
        if active_appliances:
            most_active = max(active_appliances, key=lambda x: x[1])
            if most_active[1] > 0:
                insights.append(
                    f"{most_active[0]} is the most frequently used appliance, "
                    f"active approximately {most_active[1]:.1f} hours per day"
                )

        # Peak concurrent usage
        if high_usage_hours:
            max_concurrent = max(high_usage_hours.items(), key=lambda x: len(x[1]))
            if len(max_concurrent[1]) >= 2:
                hour_str = f"{max_concurrent[0]}:00"
                insights.append(
                    f"Peak appliance activity occurs around {hour_str} with "
                    f"{len(max_concurrent[1])} appliances frequently active"
                )

        # Always-on appliances
        for name, profile in appliance_profiles.items():
            if 'error' not in profile:
                max_freq = profile.get('max_normalized_frequency', 0)
                if max_freq > 0.9:
                    insights.append(f"{name} appears to be running almost continuously")

        # Low usage appliances
        for name, profile in appliance_profiles.items():
            if 'error' not in profile:
                avg_hours = profile.get('avg_daily_active_hours', 0)
                if 0 < avg_hours < 1:
                    insights.append(f"{name} is used infrequently (less than 1 hour/day on average)")

        return insights
