# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# core/analysis/solar/availability.py
"""Solar power availability analysis."""
from typing import Dict, Any, List, Optional, Literal
import pandas as pd
import numpy as np
from utils.logger import setup_logger

logger = setup_logger()

# Type alias for analysis types
AnalysisType = Literal["daily_profile", "average_profile", "aggregated"]
TimeframeType = Literal["daily", "weekly", "monthly"]


class SolarAvailabilityAnalyzer:
    """
    Analyzes solar power generation patterns and availability.

    Supports multiple analysis types:
    - daily_profile: Solar generation for a specific date
    - average_profile: Average hourly solar profile across days
    - aggregated: Total generation by timeframe (daily/weekly/monthly)
    """

    # Possible solar column names in the data
    SOLAR_COLUMNS = ['solar', 'Solar power generation 1', 'Solar power generation 2', 'solar2']

    def detect_solar_column(self, df: pd.DataFrame) -> Optional[str]:
        """
        Auto-detect available solar column in DataFrame.

        Args:
            df: DataFrame containing energy data

        Returns:
            Name of solar column if found, None otherwise
        """
        for col in self.SOLAR_COLUMNS:
            if col in df.columns and not df[col].isna().all():
                # Check if column has any non-zero values
                if df[col].abs().sum() > 0:
                    logger.info(f"Detected solar column: {col}")
                    return col
        return None

    def _ensure_timestamp(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure DataFrame has a timestamp column."""
        if 'timestamp' not in df.columns:
            if 'local_15min' in df.columns:
                df = df.copy()
                df['timestamp'] = pd.to_datetime(df['local_15min'])
            else:
                raise ValueError("No timestamp column available")
        return df

    def get_daily_profile(
        self,
        df: pd.DataFrame,
        date: str,
        resolution: str = "hourly"
    ) -> Dict[str, Any]:
        """
        Get solar generation profile for a specific day.

        Args:
            df: DataFrame with solar data
            date: Date string in YYYY-MM-DD format
            resolution: "15min" or "hourly" (default: hourly)

        Returns:
            Dict containing:
                - date: The requested date
                - profile: List of {time, kw} values
                - total_kwh: Total generation for the day
                - peak_hour: Hour with highest generation
                - peak_kw: Peak power value
                - generation_start: First hour with generation
                - generation_end: Last hour with generation
        """
        try:
            logger.info(f"Getting daily solar profile for {date}")

            df = self._ensure_timestamp(df)
            solar_col = self.detect_solar_column(df)

            if solar_col is None:
                return {'error': 'No solar data available in the dataset'}

            # Filter to the specific date
            target_date = pd.to_datetime(date).date()
            df_day = df[df['timestamp'].dt.date == target_date].copy()

            if df_day.empty:
                return {'error': f'No data available for date {date}'}

            # Get solar values (convert negative to positive if needed - generation is positive)
            df_day['solar_kw'] = df_day[solar_col].abs()

            if resolution == "hourly":
                # Aggregate to hourly
                df_day['hour'] = df_day['timestamp'].dt.hour
                hourly = df_day.groupby('hour')['solar_kw'].mean().reset_index()
                profile = [
                    {'hour': int(row['hour']), 'kw': round(row['solar_kw'], 3)}
                    for _, row in hourly.iterrows()
                ]
            else:
                # Keep 15-min resolution
                profile = [
                    {'time': row['timestamp'].strftime('%H:%M'), 'kw': round(row['solar_kw'], 3)}
                    for _, row in df_day.iterrows()
                ]

            # Calculate statistics
            # Total kWh: sum of kW values * 0.25 hours (15-min intervals)
            total_kwh = df_day['solar_kw'].sum() * 0.25

            # Find peak
            if resolution == "hourly":
                peak_idx = hourly['solar_kw'].idxmax()
                peak_hour = int(hourly.loc[peak_idx, 'hour'])
                peak_kw = hourly.loc[peak_idx, 'solar_kw']
            else:
                peak_idx = df_day['solar_kw'].idxmax()
                peak_hour = df_day.loc[peak_idx, 'timestamp'].hour
                peak_kw = df_day.loc[peak_idx, 'solar_kw']

            # Find generation window (hours with > 0.01 kW)
            if resolution == "hourly":
                active_hours = hourly[hourly['solar_kw'] > 0.01]['hour'].tolist()
            else:
                df_day['hour'] = df_day['timestamp'].dt.hour
                active_hours = df_day[df_day['solar_kw'] > 0.01]['hour'].unique().tolist()

            generation_start = min(active_hours) if active_hours else None
            generation_end = max(active_hours) if active_hours else None

            return {
                'date': date,
                'solar_column': solar_col,
                'resolution': resolution,
                'profile': profile,
                'total_kwh': round(total_kwh, 2),
                'peak_hour': peak_hour,
                'peak_kw': round(peak_kw, 3),
                'generation_start': generation_start,
                'generation_end': generation_end,
                'generation_hours': len(active_hours) if active_hours else 0
            }

        except Exception as e:
            logger.error(f"Error getting daily solar profile: {str(e)}")
            return {'error': str(e)}

    def get_average_hourly_profile(
        self,
        df: pd.DataFrame,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get average solar generation by hour across date range.

        Args:
            df: DataFrame with solar data
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)

        Returns:
            Dict containing:
                - profile: List of {hour, mean_kw, std_kw} for each hour 0-23
                - days_analyzed: Number of days in the analysis
                - avg_daily_kwh: Average daily generation
                - peak_hour: Hour with highest average generation
                - peak_mean_kw: Peak average power value
        """
        try:
            logger.info("Calculating average hourly solar profile")

            df = self._ensure_timestamp(df)
            solar_col = self.detect_solar_column(df)

            if solar_col is None:
                return {'error': 'No solar data available in the dataset'}

            df = df.copy()

            # Apply date filters
            if start_date:
                df = df[df['timestamp'] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df['timestamp'] <= pd.to_datetime(end_date)]

            if df.empty:
                return {'error': 'No data available for the specified date range'}

            # Get solar values
            df['solar_kw'] = df[solar_col].abs()
            df['hour'] = df['timestamp'].dt.hour
            df['date'] = df['timestamp'].dt.date

            # Calculate hourly statistics
            hourly_stats = df.groupby('hour')['solar_kw'].agg(['mean', 'std']).reset_index()
            hourly_stats.columns = ['hour', 'mean_kw', 'std_kw']
            hourly_stats['std_kw'] = hourly_stats['std_kw'].fillna(0)

            profile = [
                {
                    'hour': int(row['hour']),
                    'mean_kw': round(row['mean_kw'], 3),
                    'std_kw': round(row['std_kw'], 3)
                }
                for _, row in hourly_stats.iterrows()
            ]

            # Calculate daily totals for average
            daily_totals = df.groupby('date')['solar_kw'].sum() * 0.25  # Convert to kWh
            days_analyzed = len(daily_totals)
            avg_daily_kwh = daily_totals.mean()

            # Find peak hour
            peak_idx = hourly_stats['mean_kw'].idxmax()
            peak_hour = int(hourly_stats.loc[peak_idx, 'hour'])
            peak_mean_kw = hourly_stats.loc[peak_idx, 'mean_kw']

            # Find generation window
            active_hours = hourly_stats[hourly_stats['mean_kw'] > 0.01]['hour'].tolist()
            generation_start = min(active_hours) if active_hours else None
            generation_end = max(active_hours) if active_hours else None

            return {
                'solar_column': solar_col,
                'date_range': {
                    'start': start_date or str(df['date'].min()),
                    'end': end_date or str(df['date'].max())
                },
                'profile': profile,
                'days_analyzed': days_analyzed,
                'avg_daily_kwh': round(avg_daily_kwh, 2),
                'peak_hour': peak_hour,
                'peak_mean_kw': round(peak_mean_kw, 3),
                'generation_start': generation_start,
                'generation_end': generation_end,
                'avg_generation_hours': len(active_hours) if active_hours else 0
            }

        except Exception as e:
            logger.error(f"Error calculating average hourly profile: {str(e)}")
            return {'error': str(e)}

    def get_aggregated_generation(
        self,
        df: pd.DataFrame,
        timeframe: TimeframeType = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get aggregated solar generation totals.

        Args:
            df: DataFrame with solar data
            timeframe: "daily", "weekly", or "monthly"
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)

        Returns:
            Dict containing:
                - timeframe: The aggregation level
                - periods: List of {period, total_kwh} values
                - total_kwh: Total generation across all periods
                - avg_kwh: Average generation per period
                - best_period: Period with highest generation
                - worst_period: Period with lowest generation
        """
        try:
            logger.info(f"Getting {timeframe} aggregated solar generation")

            df = self._ensure_timestamp(df)
            solar_col = self.detect_solar_column(df)

            if solar_col is None:
                return {'error': 'No solar data available in the dataset'}

            df = df.copy()

            # Apply date filters
            if start_date:
                df = df[df['timestamp'] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df['timestamp'] <= pd.to_datetime(end_date)]

            if df.empty:
                return {'error': 'No data available for the specified date range'}

            # Get solar values
            df['solar_kw'] = df[solar_col].abs()

            # Aggregate based on timeframe
            if timeframe == "daily":
                df['period'] = df['timestamp'].dt.date
                aggregated = df.groupby('period')['solar_kw'].sum() * 0.25
                period_format = lambda p: str(p)

            elif timeframe == "weekly":
                df['period'] = df['timestamp'].dt.to_period('W')
                aggregated = df.groupby('period')['solar_kw'].sum() * 0.25
                period_format = lambda p: f"{p.start_time.strftime('%Y-%m-%d')} to {p.end_time.strftime('%Y-%m-%d')}"

            elif timeframe == "monthly":
                df['period'] = df['timestamp'].dt.to_period('M')
                aggregated = df.groupby('period')['solar_kw'].sum() * 0.25
                period_format = lambda p: p.strftime('%Y-%m')

            else:
                return {'error': f'Invalid timeframe: {timeframe}'}

            periods = [
                {'period': period_format(period), 'total_kwh': round(kwh, 2)}
                for period, kwh in aggregated.items()
            ]

            # Statistics
            total_kwh = aggregated.sum()
            avg_kwh = aggregated.mean()
            best_idx = aggregated.idxmax()
            worst_idx = aggregated.idxmin()

            return {
                'solar_column': solar_col,
                'timeframe': timeframe,
                'date_range': {
                    'start': start_date or str(df['timestamp'].dt.date.min()),
                    'end': end_date or str(df['timestamp'].dt.date.max())
                },
                'periods': periods,
                'num_periods': len(periods),
                'total_kwh': round(total_kwh, 2),
                'avg_kwh_per_period': round(avg_kwh, 2),
                'best_period': {
                    'period': period_format(best_idx),
                    'total_kwh': round(aggregated[best_idx], 2)
                },
                'worst_period': {
                    'period': period_format(worst_idx),
                    'total_kwh': round(aggregated[worst_idx], 2)
                }
            }

        except Exception as e:
            logger.error(f"Error getting aggregated generation: {str(e)}")
            return {'error': str(e)}

    def analyze_solar_availability(
        self,
        df: pd.DataFrame,
        analysis_type: AnalysisType = "average_profile",
        date: Optional[str] = None,
        timeframe: TimeframeType = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive solar availability analysis.

        Args:
            df: DataFrame containing energy data
            analysis_type: Type of analysis:
                - "daily_profile": Profile for a specific date (requires date param)
                - "average_profile": Average hourly profile across days
                - "aggregated": Totals by timeframe
            date: Specific date for daily_profile (YYYY-MM-DD)
            timeframe: Aggregation level for "aggregated" type
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)

        Returns:
            Dict containing analysis results based on type
        """
        try:
            logger.info(f"Running solar availability analysis: type={analysis_type}")

            if analysis_type == "daily_profile":
                if not date:
                    return {'error': 'date parameter required for daily_profile analysis'}
                return self.get_daily_profile(df, date)

            elif analysis_type == "average_profile":
                return self.get_average_hourly_profile(df, start_date, end_date)

            elif analysis_type == "aggregated":
                return self.get_aggregated_generation(df, timeframe, start_date, end_date)

            else:
                return {'error': f'Invalid analysis_type: {analysis_type}'}

        except Exception as e:
            logger.error(f"Error in solar availability analysis: {str(e)}")
            return {'error': str(e)}
