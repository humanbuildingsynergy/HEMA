# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# core/analysis/solar/alignment.py
"""Solar power alignment analysis for appliances."""
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import pandas as pd
import numpy as np
from utils.logger import setup_logger
from core.analysis.constants import get_appliance_columns

logger = setup_logger()


class SolarAlignmentAnalyzer:
    """
    Analyzes how well appliance usage aligns with solar power generation periods.

    The alignment metric uses an indicator function approach:
    - For each 15-min interval, check if appliance is "active" (above threshold)
    - Check if solar is generating power in the same interval
    - Alignment = (intervals where both active) / (total intervals appliance active)

    This provides synchronization scores between appliance operation and solar production.
    """

    # Possible solar column names
    SOLAR_COLUMNS = ['solar', 'Solar power generation 1', 'Solar power generation 2', 'solar2']

    # Default threshold file path (relative to project root)
    DEFAULT_THRESHOLD_FILE = "data/home_power/appliance_thresholds_sample.csv"

    # Minimum solar generation to consider "active" (kW)
    SOLAR_THRESHOLD_KW = 0.01

    def __init__(self, threshold_file: Optional[str] = None):
        """
        Initialize analyzer with threshold file.

        Args:
            threshold_file: Path to CSV file with appliance thresholds.
                           If None, uses default path.
        """
        self.threshold_file = threshold_file or self.DEFAULT_THRESHOLD_FILE
        self.thresholds: Dict[str, float] = {}
        self._load_thresholds()

    def _load_thresholds(self) -> None:
        """Load appliance thresholds from CSV file."""
        try:
            path = Path(self.threshold_file)
            if not path.exists():
                # Try relative to current working directory
                path = Path.cwd() / self.threshold_file

            if not path.exists():
                logger.warning(f"Threshold file not found: {self.threshold_file}")
                return

            df = pd.read_csv(path)

            # Handle potential BOM in CSV
            if df.columns[0].startswith('\ufeff'):
                df.columns = [col.replace('\ufeff', '') for col in df.columns]

            # Build threshold dictionary
            for _, row in df.iterrows():
                appliance = row['appliance_name']
                threshold = row['threshold_kw']
                self.thresholds[appliance] = threshold

            logger.info(f"Loaded {len(self.thresholds)} appliance thresholds from {path}")

        except Exception as e:
            logger.error(f"Error loading thresholds: {str(e)}")

    def get_threshold(self, appliance_name: str) -> float:
        """
        Get threshold for an appliance.

        Uses fuzzy matching to handle column name variations.

        Args:
            appliance_name: Name of the appliance column

        Returns:
            Threshold in kW, or default of 0.01 if not found
        """
        # Direct match
        if appliance_name in self.thresholds:
            return self.thresholds[appliance_name]

        # Fuzzy match - check if threshold name is contained in appliance column name
        appliance_lower = appliance_name.lower()
        for thresh_name, thresh_value in self.thresholds.items():
            thresh_lower = thresh_name.lower()
            # Check both directions for substring match
            if thresh_lower in appliance_lower or appliance_lower in thresh_lower:
                return thresh_value

        # Default threshold
        logger.debug(f"No threshold found for '{appliance_name}', using default 0.01 kW")
        return 0.01

    def _detect_solar_column(self, df: pd.DataFrame) -> Optional[str]:
        """Detect solar column in DataFrame."""
        for col in self.SOLAR_COLUMNS:
            if col in df.columns and not df[col].isna().all():
                if df[col].abs().sum() > 0:
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

    def calculate_alignment(
        self,
        df: pd.DataFrame,
        appliance: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate solar alignment score for appliance(s).

        The alignment score represents the fraction of appliance active time
        that coincides with solar generation periods.

        Args:
            df: DataFrame with energy data
            appliance: Specific appliance to analyze (None = all appliances)
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)

        Returns:
            Dict with alignment scores and details
        """
        try:
            df = self._ensure_timestamp(df)
            solar_col = self._detect_solar_column(df)

            if solar_col is None:
                return {'error': 'No solar data available in the dataset', 'has_solar': False}

            df = df.copy()

            # Apply date filters
            if start_date:
                df = df[df['timestamp'] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df['timestamp'] <= pd.to_datetime(end_date)]

            if df.empty:
                return {'error': 'No data available for the specified date range'}

            # Get solar generation indicator (1 if generating, 0 otherwise)
            df['solar_active'] = (df[solar_col].abs() > self.SOLAR_THRESHOLD_KW).astype(int)

            # Determine which appliances to analyze
            if appliance:
                if appliance not in df.columns:
                    return {'error': f"Appliance '{appliance}' not found in data"}
                appliances_to_analyze = [appliance]
            else:
                appliances_to_analyze = get_appliance_columns(df)

            # Calculate alignment for each appliance
            results = {}
            for app in appliances_to_analyze:
                threshold = self.get_threshold(app)

                # Appliance active indicator
                app_active = (df[app].abs() > threshold).astype(int)

                # Count intervals
                total_active = app_active.sum()

                if total_active == 0:
                    results[app] = {
                        'alignment_score': None,
                        'message': 'Appliance never active during analysis period',
                        'threshold_kw': threshold,
                        'active_intervals': 0,
                        'aligned_intervals': 0
                    }
                    continue

                # Count intervals where both appliance and solar are active
                aligned = ((app_active == 1) & (df['solar_active'] == 1)).sum()

                # Alignment score: fraction of appliance runtime during solar hours
                alignment_score = aligned / total_active

                # Additional metrics
                solar_hours = df['solar_active'].sum()
                app_during_no_solar = total_active - aligned

                results[app] = {
                    'alignment_score': round(alignment_score, 4),
                    'alignment_percentage': round(alignment_score * 100, 1),
                    'threshold_kw': threshold,
                    'active_intervals': int(total_active),
                    'aligned_intervals': int(aligned),
                    'non_aligned_intervals': int(app_during_no_solar),
                    'solar_generation_intervals': int(solar_hours),
                    'active_hours': round(total_active * 0.25, 2),  # Convert to hours
                    'aligned_hours': round(aligned * 0.25, 2)
                }

            # Calculate overall statistics
            num_days = df['timestamp'].dt.date.nunique()

            return {
                'success': True,
                'solar_column': solar_col,
                'date_range': {
                    'start': str(df['timestamp'].dt.date.min()),
                    'end': str(df['timestamp'].dt.date.max())
                },
                'days_analyzed': num_days,
                'total_intervals': len(df),
                'solar_generation_intervals': int(df['solar_active'].sum()),
                'appliance_alignments': results
            }

        except Exception as e:
            logger.error(f"Error calculating solar alignment: {str(e)}")
            return {'error': str(e)}

    def get_daily_alignment_profile(
        self,
        df: pd.DataFrame,
        appliance: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get daily alignment profile for an appliance.

        Shows how alignment varies day-to-day, useful for identifying patterns.

        Args:
            df: DataFrame with energy data
            appliance: Appliance to analyze
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dict with daily alignment scores
        """
        try:
            df = self._ensure_timestamp(df)
            solar_col = self._detect_solar_column(df)

            if solar_col is None:
                return {'error': 'No solar data available', 'has_solar': False}

            if appliance not in df.columns:
                return {'error': f"Appliance '{appliance}' not found"}

            df = df.copy()

            # Apply date filters
            if start_date:
                df = df[df['timestamp'] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df['timestamp'] <= pd.to_datetime(end_date)]

            if df.empty:
                return {'error': 'No data available for specified date range'}

            threshold = self.get_threshold(appliance)
            df['date'] = df['timestamp'].dt.date
            df['solar_active'] = (df[solar_col].abs() > self.SOLAR_THRESHOLD_KW).astype(int)
            df['app_active'] = (df[appliance].abs() > threshold).astype(int)
            df['aligned'] = ((df['app_active'] == 1) & (df['solar_active'] == 1)).astype(int)

            # Group by date
            daily = df.groupby('date').agg({
                'app_active': 'sum',
                'aligned': 'sum',
                'solar_active': 'sum'
            }).reset_index()

            # Calculate daily alignment scores
            daily_scores = []
            for _, row in daily.iterrows():
                if row['app_active'] > 0:
                    score = row['aligned'] / row['app_active']
                else:
                    score = None

                daily_scores.append({
                    'date': str(row['date']),
                    'alignment_score': round(score, 4) if score is not None else None,
                    'active_intervals': int(row['app_active']),
                    'aligned_intervals': int(row['aligned']),
                    'solar_intervals': int(row['solar_active'])
                })

            # Calculate average alignment
            valid_scores = [d['alignment_score'] for d in daily_scores if d['alignment_score'] is not None]
            avg_alignment = np.mean(valid_scores) if valid_scores else None

            return {
                'success': True,
                'appliance': appliance,
                'threshold_kw': threshold,
                'date_range': {
                    'start': str(df['date'].min()),
                    'end': str(df['date'].max())
                },
                'days_analyzed': len(daily_scores),
                'days_with_activity': len(valid_scores),
                'average_alignment': round(avg_alignment, 4) if avg_alignment else None,
                'daily_profile': daily_scores
            }

        except Exception as e:
            logger.error(f"Error getting daily alignment profile: {str(e)}")
            return {'error': str(e)}

    def get_hourly_alignment_pattern(
        self,
        df: pd.DataFrame,
        appliance: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get hourly alignment pattern showing when appliance runs vs solar generation.

        Args:
            df: DataFrame with energy data
            appliance: Appliance to analyze
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dict with hourly patterns for appliance and solar
        """
        try:
            df = self._ensure_timestamp(df)
            solar_col = self._detect_solar_column(df)

            if solar_col is None:
                return {'error': 'No solar data available', 'has_solar': False}

            if appliance not in df.columns:
                return {'error': f"Appliance '{appliance}' not found"}

            df = df.copy()

            if start_date:
                df = df[df['timestamp'] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df['timestamp'] <= pd.to_datetime(end_date)]

            if df.empty:
                return {'error': 'No data available for specified date range'}

            threshold = self.get_threshold(appliance)
            df['hour'] = df['timestamp'].dt.hour
            df['solar_kw'] = df[solar_col].abs()
            df['app_active'] = (df[appliance].abs() > threshold).astype(int)

            # Group by hour
            hourly = df.groupby('hour').agg({
                'solar_kw': 'mean',
                'app_active': 'mean',  # Fraction of intervals active
                appliance: 'mean'
            }).reset_index()

            hourly_pattern = []
            for _, row in hourly.iterrows():
                hourly_pattern.append({
                    'hour': int(row['hour']),
                    'avg_solar_kw': round(row['solar_kw'], 3),
                    'appliance_activity_rate': round(row['app_active'], 3),
                    'avg_appliance_kw': round(row[appliance], 3)
                })

            # Identify optimal and suboptimal hours
            solar_hours = [h for h in hourly_pattern if h['avg_solar_kw'] > self.SOLAR_THRESHOLD_KW]
            if solar_hours:
                solar_start = min(h['hour'] for h in solar_hours)
                solar_end = max(h['hour'] for h in solar_hours)
            else:
                solar_start = None
                solar_end = None

            return {
                'success': True,
                'appliance': appliance,
                'threshold_kw': threshold,
                'date_range': {
                    'start': str(df['timestamp'].dt.date.min()),
                    'end': str(df['timestamp'].dt.date.max())
                },
                'solar_generation_window': {
                    'start_hour': solar_start,
                    'end_hour': solar_end
                },
                'hourly_pattern': hourly_pattern
            }

        except Exception as e:
            logger.error(f"Error getting hourly alignment pattern: {str(e)}")
            return {'error': str(e)}
