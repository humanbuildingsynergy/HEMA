# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# core/analysis/aggregation.py
"""Enhanced aggregation utilities for energy data analysis."""
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np

from .constants import SEASON_NAMES


def get_season(month: int) -> str:
    """Get season name for a given month (1-12)."""
    return SEASON_NAMES.get(month, "unknown")


# =============================================================================
# Aggregation Engine
# =============================================================================

class AggregationEngine:
    """
    Engine for advanced time-based aggregations on energy data.

    Supports:
    - Standard aggregations: hourly, daily, weekly, monthly
    - Seasonal aggregations
    - Rolling averages (7-day, 30-day, custom)
    - Year-over-year comparisons
    - Peak/off-peak period aggregations
    """

    def __init__(self, df: pd.DataFrame):
        """
        Initialize the aggregation engine.

        Args:
            df: DataFrame with energy data (must have 'local_15min' timestamp column)
        """
        self.df = df.copy()

        # Ensure timestamp column exists and is datetime
        if 'local_15min' in self.df.columns:
            self.df['local_15min'] = pd.to_datetime(self.df['local_15min'])
            self.timestamp_col = 'local_15min'
        else:
            raise ValueError("DataFrame must have 'local_15min' column")

        # Store timezone info
        self.tz = self.df['local_15min'].dt.tz

        # Ensure derived columns exist
        self._ensure_derived_columns()

        # Get appliance columns
        self.appliance_cols = self._get_appliance_columns()

    def _ensure_derived_columns(self):
        """Ensure necessary derived columns exist."""
        ts = self.df[self.timestamp_col]

        if 'hour' not in self.df.columns:
            self.df['hour'] = ts.dt.hour
        if 'date' not in self.df.columns:
            self.df['date'] = ts.dt.date
        if 'day_of_week' not in self.df.columns:
            self.df['day_of_week'] = ts.dt.dayofweek
        if 'is_weekend' not in self.df.columns:
            self.df['is_weekend'] = ts.dt.dayofweek >= 5
        if 'week' not in self.df.columns:
            self.df['week'] = ts.dt.isocalendar().week
        if 'month' not in self.df.columns:
            self.df['month'] = ts.dt.month
        if 'year' not in self.df.columns:
            self.df['year'] = ts.dt.year
        if 'season' not in self.df.columns:
            self.df['season'] = self.df['month'].map(get_season)

        # Year-week and year-month for grouping
        if 'year_week' not in self.df.columns:
            self.df['year_week'] = ts.dt.strftime('%Y-W%W')
        if 'year_month' not in self.df.columns:
            self.df['year_month'] = ts.dt.strftime('%Y-%m')

    def _get_appliance_columns(self) -> List[str]:
        """Get list of appliance columns."""
        exclude = {
            'local_15min', 'dataid', 'grid', 'solar', 'solar2',
            'leg1v', 'leg2v', 'Solar power generation 1', 'Solar power generation 2',
            'hour', 'date', 'day_of_week', 'is_weekend', 'week', 'month', 'year',
            'year_month', 'year_week', 'season', 'total_consumption', 'net_consumption',
            'interval_cost', 'solar_savings'
        }
        return [col for col in self.df.columns if col not in exclude and not col.endswith('_cost')]

    def _calculate_consumption(self, df: pd.DataFrame, appliances: Optional[List[str]] = None) -> pd.Series:
        """Calculate total consumption for selected appliances."""
        if appliances:
            valid_appliances = [a for a in appliances if a in df.columns]
            if not valid_appliances:
                raise ValueError(f"None of the specified appliances found: {appliances}")
            return df[valid_appliances].sum(axis=1)
        else:
            return df[self.appliance_cols].sum(axis=1)

    # =========================================================================
    # Weekly Aggregation
    # =========================================================================

    def aggregate_weekly(
        self,
        appliances: Optional[List[str]] = None,
        include_breakdown: bool = False
    ) -> Dict[str, Any]:
        """
        Aggregate energy data by week.

        Args:
            appliances: List of appliances to include (None = all)
            include_breakdown: Include per-appliance breakdown

        Returns:
            Dict with weekly aggregation results
        """
        df = self.df.copy()
        df['consumption'] = self._calculate_consumption(df, appliances)

        # Group by year-week
        weekly = df.groupby('year_week').agg({
            'consumption': ['sum', 'mean', 'max'],
            'date': ['min', 'max']
        })

        weekly.columns = ['total_kw', 'avg_kw', 'peak_kw', 'start_date', 'end_date']
        weekly['total_kwh'] = weekly['total_kw'] / 4  # Convert 15-min to kWh
        # Calculate per-week daily average using timestamp span for consistency
        weekly['days'] = (pd.to_datetime(weekly['end_date']) - pd.to_datetime(weekly['start_date'])).dt.days + 1
        weekly['daily_avg_kwh'] = weekly['total_kwh'] / weekly['days']
        weekly = weekly.reset_index()

        # Calculate overall daily average using timestamp span (consistent with ground truth)
        min_ts = df[self.timestamp_col].min()
        max_ts = df[self.timestamp_col].max()
        total_days = (max_ts - min_ts).days + 1
        total_kwh = weekly['total_kwh'].sum()
        overall_daily_avg = total_kwh / total_days if total_days > 0 else 0

        # Calculate statistics
        stats = {
            "num_weeks": len(weekly),
            "avg_weekly_kwh": round(weekly['total_kwh'].mean(), 2),
            "min_weekly_kwh": round(weekly['total_kwh'].min(), 2),
            "max_weekly_kwh": round(weekly['total_kwh'].max(), 2),
            "std_weekly_kwh": round(weekly['total_kwh'].std(), 2),
            "total_kwh": round(total_kwh, 2),
            "total_days": total_days,
            "avg_daily_kwh": round(overall_daily_avg, 2),
        }

        # Find best and worst weeks
        best_week_idx = weekly['total_kwh'].idxmin()
        worst_week_idx = weekly['total_kwh'].idxmax()

        stats["best_week"] = {
            "week": weekly.loc[best_week_idx, 'year_week'],
            "kwh": round(weekly.loc[best_week_idx, 'total_kwh'], 2),
        }
        stats["worst_week"] = {
            "week": weekly.loc[worst_week_idx, 'year_week'],
            "kwh": round(weekly.loc[worst_week_idx, 'total_kwh'], 2),
        }

        result = {
            "aggregation": "weekly",
            "statistics": stats,
            "data": weekly[['year_week', 'total_kwh', 'daily_avg_kwh', 'peak_kw', 'days']].to_dict('records'),
        }

        # Add per-appliance breakdown if requested
        if include_breakdown and appliances:
            breakdown = {}
            for appliance in appliances:
                if appliance in df.columns:
                    app_weekly = df.groupby('year_week')[appliance].sum() / 4
                    breakdown[appliance] = {
                        "weekly_avg_kwh": round(app_weekly.mean(), 2),
                        "weekly_total_kwh": round(app_weekly.sum(), 2),
                    }
            result["appliance_breakdown"] = breakdown

        return result

    # =========================================================================
    # Monthly Aggregation
    # =========================================================================

    def aggregate_monthly(
        self,
        appliances: Optional[List[str]] = None,
        include_breakdown: bool = False
    ) -> Dict[str, Any]:
        """
        Aggregate energy data by month.

        Args:
            appliances: List of appliances to include (None = all)
            include_breakdown: Include per-appliance breakdown

        Returns:
            Dict with monthly aggregation results
        """
        df = self.df.copy()
        df['consumption'] = self._calculate_consumption(df, appliances)

        # Group by year-month
        monthly = df.groupby('year_month').agg({
            'consumption': ['sum', 'mean', 'max'],
            'date': ['min', 'max']
        })

        monthly.columns = ['total_kw', 'avg_kw', 'peak_kw', 'start_date', 'end_date']
        monthly['total_kwh'] = monthly['total_kw'] / 4  # Convert 15-min to kWh
        # Calculate per-month daily average using timestamp span for consistency
        monthly['days'] = (pd.to_datetime(monthly['end_date']) - pd.to_datetime(monthly['start_date'])).dt.days + 1
        monthly['daily_avg_kwh'] = monthly['total_kwh'] / monthly['days']
        monthly = monthly.reset_index()

        # Calculate overall daily average using timestamp span (consistent with ground truth)
        min_ts = df[self.timestamp_col].min()
        max_ts = df[self.timestamp_col].max()
        total_days = (max_ts - min_ts).days + 1
        total_kwh = monthly['total_kwh'].sum()
        overall_daily_avg = total_kwh / total_days if total_days > 0 else 0

        # Calculate statistics
        stats = {
            "num_months": len(monthly),
            "avg_monthly_kwh": round(monthly['total_kwh'].mean(), 2),
            "min_monthly_kwh": round(monthly['total_kwh'].min(), 2),
            "max_monthly_kwh": round(monthly['total_kwh'].max(), 2),
            "avg_daily_kwh": round(overall_daily_avg, 2),
            "total_kwh": round(total_kwh, 2),
            "total_days": total_days,
        }

        # Find best and worst months
        best_month_idx = monthly['total_kwh'].idxmin()
        worst_month_idx = monthly['total_kwh'].idxmax()

        stats["best_month"] = {
            "month": monthly.loc[best_month_idx, 'year_month'],
            "kwh": round(monthly.loc[best_month_idx, 'total_kwh'], 2),
            "daily_avg": round(monthly.loc[best_month_idx, 'daily_avg_kwh'], 2),
        }
        stats["worst_month"] = {
            "month": monthly.loc[worst_month_idx, 'year_month'],
            "kwh": round(monthly.loc[worst_month_idx, 'total_kwh'], 2),
            "daily_avg": round(monthly.loc[worst_month_idx, 'daily_avg_kwh'], 2),
        }

        result = {
            "aggregation": "monthly",
            "statistics": stats,
            "data": monthly[['year_month', 'total_kwh', 'daily_avg_kwh', 'peak_kw', 'days']].to_dict('records'),
        }

        # Add per-appliance breakdown if requested
        if include_breakdown and appliances:
            breakdown = {}
            for appliance in appliances:
                if appliance in df.columns:
                    app_monthly = df.groupby('year_month')[appliance].sum() / 4
                    breakdown[appliance] = {
                        "monthly_avg_kwh": round(app_monthly.mean(), 2),
                        "monthly_total_kwh": round(app_monthly.sum(), 2),
                    }
            result["appliance_breakdown"] = breakdown

        return result

    # =========================================================================
    # Seasonal Aggregation
    # =========================================================================

    def aggregate_seasonal(
        self,
        appliances: Optional[List[str]] = None,
        include_breakdown: bool = False
    ) -> Dict[str, Any]:
        """
        Aggregate energy data by season.

        Args:
            appliances: List of appliances to include (None = all)
            include_breakdown: Include per-appliance breakdown

        Returns:
            Dict with seasonal aggregation results
        """
        df = self.df.copy()
        df['consumption'] = self._calculate_consumption(df, appliances)

        # Group by season
        seasonal = df.groupby('season').agg({
            'consumption': ['sum', 'mean', 'max'],
            'date': 'nunique'
        })

        seasonal.columns = ['total_kw', 'avg_kw', 'peak_kw', 'days']
        seasonal['total_kwh'] = seasonal['total_kw'] / 4
        seasonal['daily_avg_kwh'] = seasonal['total_kwh'] / seasonal['days']
        seasonal = seasonal.reset_index()

        # Order seasons properly
        season_order = ['winter', 'spring', 'summer', 'fall']
        seasonal['season'] = pd.Categorical(seasonal['season'], categories=season_order, ordered=True)
        seasonal = seasonal.sort_values('season').reset_index(drop=True)

        # Calculate statistics
        stats = {
            "seasons_present": seasonal['season'].tolist(),
            "total_kwh": round(seasonal['total_kwh'].sum(), 2),
        }

        # Find highest and lowest consumption seasons
        if len(seasonal) > 0:
            highest_idx = seasonal['daily_avg_kwh'].idxmax()
            lowest_idx = seasonal['daily_avg_kwh'].idxmin()

            stats["highest_season"] = {
                "season": seasonal.loc[highest_idx, 'season'],
                "daily_avg_kwh": round(seasonal.loc[highest_idx, 'daily_avg_kwh'], 2),
                "total_kwh": round(seasonal.loc[highest_idx, 'total_kwh'], 2),
            }
            stats["lowest_season"] = {
                "season": seasonal.loc[lowest_idx, 'season'],
                "daily_avg_kwh": round(seasonal.loc[lowest_idx, 'daily_avg_kwh'], 2),
                "total_kwh": round(seasonal.loc[lowest_idx, 'total_kwh'], 2),
            }

        result = {
            "aggregation": "seasonal",
            "statistics": stats,
            "data": seasonal[['season', 'total_kwh', 'daily_avg_kwh', 'peak_kw', 'days']].to_dict('records'),
        }

        # Add per-appliance breakdown if requested
        if include_breakdown and appliances:
            breakdown = {}
            for appliance in appliances:
                if appliance in df.columns:
                    app_seasonal = df.groupby('season')[appliance].agg(['sum', 'mean'])
                    app_seasonal['total_kwh'] = app_seasonal['sum'] / 4
                    breakdown[appliance] = app_seasonal['total_kwh'].to_dict()
            result["appliance_breakdown"] = breakdown

        return result

    # =========================================================================
    # Rolling Averages
    # =========================================================================

    def calculate_rolling_average(
        self,
        window_days: int = 7,
        appliances: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Calculate rolling average consumption.

        Args:
            window_days: Rolling window size in days (default: 7)
            appliances: List of appliances to include (None = all)

        Returns:
            Dict with rolling average data and statistics
        """
        df = self.df.copy()
        df['consumption'] = self._calculate_consumption(df, appliances)

        # Aggregate to daily first
        daily = df.groupby('date').agg({
            'consumption': 'sum'
        }).reset_index()
        daily['consumption_kwh'] = daily['consumption'] / 4
        daily = daily.sort_values('date')

        # Calculate rolling average
        daily[f'rolling_{window_days}d_avg'] = daily['consumption_kwh'].rolling(
            window=window_days, min_periods=1
        ).mean()

        # Calculate rolling statistics
        rolling_values = daily[f'rolling_{window_days}d_avg'].dropna()

        stats = {
            "window_days": window_days,
            "num_days": len(daily),
            "current_rolling_avg": round(rolling_values.iloc[-1], 2) if len(rolling_values) > 0 else None,
            "min_rolling_avg": round(rolling_values.min(), 2) if len(rolling_values) > 0 else None,
            "max_rolling_avg": round(rolling_values.max(), 2) if len(rolling_values) > 0 else None,
            "overall_daily_avg": round(daily['consumption_kwh'].mean(), 2),
        }

        # Detect trend
        if len(rolling_values) >= window_days * 2:
            first_half = rolling_values.iloc[:len(rolling_values)//2].mean()
            second_half = rolling_values.iloc[len(rolling_values)//2:].mean()
            pct_change = ((second_half - first_half) / first_half) * 100

            if pct_change > 5:
                stats["trend"] = "increasing"
            elif pct_change < -5:
                stats["trend"] = "decreasing"
            else:
                stats["trend"] = "stable"
            stats["trend_pct_change"] = round(pct_change, 1)
        else:
            stats["trend"] = "insufficient_data"

        # Return last 30 days of data for charting
        recent_data = daily.tail(30)[['date', 'consumption_kwh', f'rolling_{window_days}d_avg']].copy()
        recent_data['date'] = recent_data['date'].astype(str)

        return {
            "aggregation": f"rolling_{window_days}d",
            "statistics": stats,
            "recent_data": recent_data.to_dict('records'),
        }

    # =========================================================================
    # Weekday vs Weekend Comparison
    # =========================================================================

    def compare_weekday_weekend(
        self,
        appliances: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Compare weekday vs weekend consumption patterns.

        Args:
            appliances: List of appliances to include (None = all)

        Returns:
            Dict with weekday/weekend comparison
        """
        df = self.df.copy()
        df['consumption'] = self._calculate_consumption(df, appliances)

        # Aggregate by day type
        weekday_df = df[~df['is_weekend']]
        weekend_df = df[df['is_weekend']]

        def calc_stats(subset_df: pd.DataFrame) -> Dict[str, float]:
            daily = subset_df.groupby('date')['consumption'].sum() / 4
            return {
                "total_kwh": round(daily.sum(), 2),
                "avg_daily_kwh": round(daily.mean(), 2),
                "num_days": len(daily),
                "peak_kw": round(subset_df['consumption'].max(), 3),
            }

        weekday_stats = calc_stats(weekday_df)
        weekend_stats = calc_stats(weekend_df)

        # Calculate difference
        diff_kwh = weekend_stats["avg_daily_kwh"] - weekday_stats["avg_daily_kwh"]
        diff_pct = (diff_kwh / weekday_stats["avg_daily_kwh"]) * 100 if weekday_stats["avg_daily_kwh"] > 0 else 0

        comparison = {
            "difference_kwh": round(diff_kwh, 2),
            "difference_pct": round(diff_pct, 1),
            "higher_on": "weekend" if diff_kwh > 0 else "weekday" if diff_kwh < 0 else "equal",
        }

        # Hourly pattern comparison
        weekday_hourly = weekday_df.groupby('hour')['consumption'].mean()
        weekend_hourly = weekend_df.groupby('hour')['consumption'].mean()

        hourly_comparison = []
        for hour in range(24):
            wd = weekday_hourly.get(hour, 0)
            we = weekend_hourly.get(hour, 0)
            hourly_comparison.append({
                "hour": hour,
                "weekday_kw": round(wd, 3),
                "weekend_kw": round(we, 3),
                "difference_kw": round(we - wd, 3),
            })

        return {
            "weekday": weekday_stats,
            "weekend": weekend_stats,
            "comparison": comparison,
            "hourly_pattern": hourly_comparison,
        }

    # =========================================================================
    # Peak Hour Analysis
    # =========================================================================

    def analyze_peak_hours(
        self,
        peak_start: int = 14,
        peak_end: int = 20,
        appliances: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze on-peak vs off-peak consumption.

        Args:
            peak_start: Start hour of peak period (default: 14 / 2 PM)
            peak_end: End hour of peak period (default: 20 / 8 PM)
            appliances: List of appliances to include (None = all)

        Returns:
            Dict with peak/off-peak analysis
        """
        df = self.df.copy()
        df['consumption'] = self._calculate_consumption(df, appliances)

        # Classify periods
        df['is_peak'] = (df['hour'] >= peak_start) & (df['hour'] < peak_end)

        # Aggregate
        peak_df = df[df['is_peak']]
        off_peak_df = df[~df['is_peak']]

        peak_kwh = peak_df['consumption'].sum() / 4
        off_peak_kwh = off_peak_df['consumption'].sum() / 4
        total_kwh = peak_kwh + off_peak_kwh

        peak_pct = (peak_kwh / total_kwh) * 100 if total_kwh > 0 else 0
        off_peak_pct = (off_peak_kwh / total_kwh) * 100 if total_kwh > 0 else 0

        # Peak hours are typically 6 hours, off-peak 18 hours
        peak_hours = peak_end - peak_start
        off_peak_hours = 24 - peak_hours

        # Intensity comparison (kWh per hour of period type)
        peak_intensity = peak_kwh / (peak_hours * df['date'].nunique()) if peak_hours > 0 else 0
        off_peak_intensity = off_peak_kwh / (off_peak_hours * df['date'].nunique()) if off_peak_hours > 0 else 0

        return {
            "peak_period": f"{peak_start}:00 - {peak_end}:00",
            "peak_hours_per_day": peak_hours,
            "off_peak_hours_per_day": off_peak_hours,
            "consumption": {
                "peak_kwh": round(peak_kwh, 2),
                "off_peak_kwh": round(off_peak_kwh, 2),
                "peak_pct": round(peak_pct, 1),
                "off_peak_pct": round(off_peak_pct, 1),
            },
            "intensity": {
                "peak_kwh_per_hour": round(peak_intensity, 3),
                "off_peak_kwh_per_hour": round(off_peak_intensity, 3),
                "ratio": round(peak_intensity / off_peak_intensity, 2) if off_peak_intensity > 0 else None,
            },
            "insights": self._generate_peak_insights(peak_pct, peak_intensity, off_peak_intensity),
        }

    def _generate_peak_insights(
        self,
        peak_pct: float,
        peak_intensity: float,
        off_peak_intensity: float
    ) -> List[str]:
        """Generate insights from peak analysis."""
        insights = []

        if peak_pct > 40:
            insights.append(f"High peak usage ({peak_pct:.1f}%) - consider shifting loads to off-peak hours")
        elif peak_pct < 20:
            insights.append(f"Excellent peak management ({peak_pct:.1f}% during peak) - you're avoiding high-rate periods")

        if peak_intensity > off_peak_intensity * 1.5:
            insights.append("Peak hour intensity is 50%+ higher than off-peak - ideal candidates for load shifting")

        return insights
