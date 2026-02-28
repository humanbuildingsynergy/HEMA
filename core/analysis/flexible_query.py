# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# core/analysis/flexible_query.py
"""Flexible query engine for arbitrary time-based energy data queries."""
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from utils.logger import setup_logger
from .date_parser import parse_date_range
from .constants import SEASON_NAMES

logger = setup_logger()

SEASON_ORDER = ["winter", "spring", "summer", "fall"]


class FlexibleQueryEngine:
    """
    Engine for flexible time-based queries on energy data.

    Supports:
    - Arbitrary date range filtering
    - Multiple aggregation levels (raw/15min, hourly, daily, weekly, monthly, seasonal)
    - Appliance filtering with optional breakdown
    - Day-of-week filtering (weekday/weekend, specific days)
    - Hour-of-day filtering
    - Best/worst period identification
    - Rolling averages
    - Peak hours analysis
    - Weekday vs weekend comparison
    """

    AGGREGATION_LEVELS = ["raw", "15min", "hourly", "daily", "weekly", "monthly", "seasonal"]

    DAY_FILTERS = {
        "weekday": [0, 1, 2, 3, 4],  # Monday-Friday
        "weekend": [5, 6],  # Saturday-Sunday
        "monday": [0], "tuesday": [1], "wednesday": [2],
        "thursday": [3], "friday": [4], "saturday": [5], "sunday": [6],
    }

    def __init__(self, df: pd.DataFrame, rate_df: Optional[pd.DataFrame] = None):
        """
        Initialize the query engine.

        Args:
            df: DataFrame with energy data (must have 'local_15min' timestamp column)
            rate_df: Optional rate data for cost calculations
        """
        self.df = df.copy()
        self.rate_df = rate_df

        # Ensure timestamp column exists and is datetime
        if 'local_15min' in self.df.columns:
            self.df['local_15min'] = pd.to_datetime(self.df['local_15min'])
            self.timestamp_col = 'local_15min'
        else:
            raise ValueError("DataFrame must have 'local_15min' column")

        # Store timezone info for date comparisons
        self.tz = self.df['local_15min'].dt.tz

        # Store data range for relative date calculations
        # Use the last timestamp as reference for "last week", "yesterday", etc.
        self.data_start = self.df['local_15min'].min()
        self.data_end = self.df['local_15min'].max()
        # Convert to naive datetime for reference_date (parse functions expect naive datetime)
        self.reference_date = self.data_end.to_pydatetime().replace(tzinfo=None)

        # Add derived columns if not present
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
        if 'year_month' not in self.df.columns:
            self.df['year_month'] = ts.dt.to_period('M')
        if 'year_week' not in self.df.columns:
            self.df['year_week'] = ts.dt.strftime('%Y-W%W')
        if 'season' not in self.df.columns:
            self.df['season'] = self.df['month'].map(SEASON_NAMES)

    def _get_appliance_columns(self) -> List[str]:
        """Get list of appliance columns."""
        exclude = {
            'local_15min', 'dataid', 'grid', 'solar', 'solar2',
            'leg1v', 'leg2v', 'Solar power generation 1', 'Solar power generation 2',
            'hour', 'date', 'day_of_week', 'is_weekend', 'week', 'month', 'year',
            'year_month', 'year_week', 'total_consumption', 'net_consumption',
            'interval_cost', 'solar_savings', 'season',  # Derived columns
        }
        # Only include numeric columns that aren't in the exclude list
        return [
            col for col in self.df.columns
            if col not in exclude
            and not col.endswith('_cost')
            and pd.api.types.is_numeric_dtype(self.df[col])
        ]

    def _calculate_total_consumption(self, df: pd.DataFrame, appliances: Optional[List[str]] = None) -> pd.Series:
        """Calculate total consumption for selected appliances."""
        if appliances:
            valid_appliances = [a for a in appliances if a in df.columns]
            if not valid_appliances:
                raise ValueError(f"None of the specified appliances found: {appliances}")
            return df[valid_appliances].sum(axis=1)
        else:
            # Use all appliance columns
            return df[self.appliance_cols].sum(axis=1)

    def query(
        self,
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None,
        aggregation: str = "daily",
        appliances: Optional[List[str]] = None,
        metrics: Optional[List[str]] = None,
        day_filter: Optional[str] = None,
        hour_range: Optional[Tuple[int, int]] = None,
        include_breakdown: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute a flexible query on the energy data.

        Args:
            start_date: Start date (string or datetime, e.g., "2024-01-15", "last week")
            end_date: End date (string or datetime, e.g., "2024-01-21", "today")
            aggregation: Aggregation level ("raw", "15min", "hourly", "daily", "weekly", "monthly", "seasonal")
            appliances: List of appliance names to include (None = all)
            metrics: List of metrics to compute (["consumption", "cost", "peak_power", "average"])
            day_filter: Day filter ("weekday", "weekend", "monday", etc.)
            hour_range: Tuple of (start_hour, end_hour) to filter by time of day
            include_breakdown: Include per-appliance breakdown in results

        Returns:
            Dict with query results including data, statistics, and metadata
        """
        # Default metrics
        if metrics is None:
            metrics = ["consumption", "average"]

        # Parse dates if strings
        # Use parse_date_range for period-aware parsing (e.g., "last week" sets both start and end)
        # Use data's last timestamp as reference so "last week" means "week before data ends"
        start_is_string = isinstance(start_date, str)
        end_is_string = isinstance(end_date, str)

        if start_is_string or end_is_string:
            parsed_start, parsed_end = parse_date_range(
                start_str=start_date if start_is_string else None,
                end_str=end_date if end_is_string else None,
                reference_date=self.reference_date,
            )
            # Use parsed values, but preserve datetime objects if they were passed directly
            if start_is_string:
                start_date = parsed_start
            if end_is_string or (start_is_string and end_date is None):
                # If start was a period string like "last week" and no end was given,
                # use the calculated end date
                end_date = parsed_end

        # Make dates timezone-aware if data is timezone-aware
        if self.tz is not None:
            if start_date and start_date.tzinfo is None:
                start_date = pd.Timestamp(start_date).tz_localize(self.tz)
            if end_date and end_date.tzinfo is None:
                end_date = pd.Timestamp(end_date).tz_localize(self.tz)

        # Start with full dataframe
        filtered_df = self.df.copy()

        # Apply date filter
        if start_date:
            filtered_df = filtered_df[filtered_df[self.timestamp_col] >= start_date]
        if end_date:
            filtered_df = filtered_df[filtered_df[self.timestamp_col] <= end_date]

        if filtered_df.empty:
            return {
                "success": False,
                "error": "No data found for the specified date range",
                "query_params": {
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                    "aggregation": aggregation,
                    "appliances": appliances,
                }
            }

        # Apply day filter
        if day_filter:
            day_filter_lower = day_filter.lower()
            if day_filter_lower in self.DAY_FILTERS:
                filtered_df = filtered_df[
                    filtered_df['day_of_week'].isin(self.DAY_FILTERS[day_filter_lower])
                ]

        # Apply hour filter
        if hour_range:
            start_hour, end_hour = hour_range
            if start_hour <= end_hour:
                filtered_df = filtered_df[
                    (filtered_df['hour'] >= start_hour) & (filtered_df['hour'] < end_hour)
                ]
            else:
                # Wrap around midnight (e.g., 22 to 6)
                filtered_df = filtered_df[
                    (filtered_df['hour'] >= start_hour) | (filtered_df['hour'] < end_hour)
                ]

        if filtered_df.empty:
            return {
                "success": False,
                "error": "No data found after applying filters",
                "query_params": {
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                    "day_filter": day_filter,
                    "hour_range": hour_range,
                }
            }

        # Calculate consumption for selected appliances
        filtered_df = filtered_df.copy()
        filtered_df['query_consumption'] = self._calculate_total_consumption(filtered_df, appliances)

        # Perform aggregation
        aggregated_data = self._aggregate_data(filtered_df, aggregation, metrics)

        # Calculate summary statistics
        statistics = self._calculate_statistics(filtered_df, appliances, metrics)

        # Build result
        result = {
            "success": True,
            "query_params": {
                "start_date": str(start_date) if start_date else "data start",
                "end_date": str(end_date) if end_date else "data end",
                "aggregation": aggregation,
                "appliances": appliances or "all",
                "day_filter": day_filter,
                "hour_range": hour_range,
            },
            "data_range": {
                "actual_start": str(filtered_df[self.timestamp_col].min()),
                "actual_end": str(filtered_df[self.timestamp_col].max()),
                "records": len(filtered_df),
            },
            "statistics": statistics,
            "aggregated_data": aggregated_data,
        }

        # Add per-appliance breakdown if requested or for single-day queries
        is_single_day = statistics.get("num_days", 0) == 1
        should_include_breakdown = (
            include_breakdown or
            (appliances and len(appliances) <= 10) or
            (is_single_day and aggregation == "daily")
        )

        if should_include_breakdown:
            breakdown_appliances = appliances if appliances else self.appliance_cols
            result["appliance_breakdown"] = self._get_appliance_breakdown(
                filtered_df, breakdown_appliances, aggregation
            )

        # Add best/worst period identification for weekly, monthly, seasonal, daily
        if aggregation in ["daily", "weekly", "monthly", "seasonal"] and len(aggregated_data.get("records", [])) > 1:
            result["best_worst"] = self._identify_best_worst(aggregated_data["records"], aggregation)

        return result

    def _aggregate_data(
        self,
        df: pd.DataFrame,
        aggregation: str,
        metrics: List[str]
    ) -> Dict[str, Any]:
        """Aggregate data at the specified level."""
        df = df.copy()

        # Determine groupby column based on aggregation level
        if aggregation in ["raw", "15min"]:
            group_col = self.timestamp_col
        elif aggregation == "hourly":
            df['agg_key'] = df[self.timestamp_col].dt.floor('h')
            group_col = 'agg_key'
        elif aggregation == "daily":
            group_col = 'date'
        elif aggregation == "weekly":
            group_col = 'year_week'
        elif aggregation == "monthly":
            group_col = 'year_month'
        elif aggregation == "seasonal":
            group_col = 'season'
        else:
            group_col = 'date'  # Default to daily

        # Aggregate with additional date columns for period span calculation
        agg_dict = {
            'query_consumption': ['sum', 'mean', 'max', 'count'],
            self.timestamp_col: ['min', 'max']
        }
        grouped = df.groupby(group_col).agg(agg_dict)
        grouped.columns = ['total_kwh', 'avg_kw', 'peak_kw', 'intervals', 'start_ts', 'end_ts']
        grouped = grouped.reset_index()

        # Convert kWh from 15-min intervals (divide by 4 for kWh)
        if aggregation not in ["raw", "15min"]:
            grouped['total_kwh'] = grouped['total_kwh'] / 4

        # Calculate days in each period using timestamp span
        grouped['days'] = (grouped['end_ts'] - grouped['start_ts']).dt.days + 1
        grouped['daily_avg_kwh'] = grouped['total_kwh'] / grouped['days'].clip(lower=1)

        # Round for readability
        grouped['total_kwh'] = grouped['total_kwh'].round(2)
        grouped['daily_avg_kwh'] = grouped['daily_avg_kwh'].round(2)
        grouped['peak_kw'] = grouped['peak_kw'].round(3)

        # For seasonal aggregation, ensure proper ordering
        if aggregation == "seasonal":
            grouped['season_order'] = grouped['season'].map(
                {s: i for i, s in enumerate(SEASON_ORDER)}
            )
            grouped = grouped.sort_values('season_order').drop('season_order', axis=1)

        # Select columns for output based on aggregation level
        if aggregation in ["raw", "15min"]:
            output_cols = [group_col, 'total_kwh', 'avg_kw', 'peak_kw']
        else:
            output_cols = [group_col, 'total_kwh', 'daily_avg_kwh', 'peak_kw', 'days']

        # Convert to records (limit to 100 for response size)
        records = grouped[output_cols].head(100).to_dict('records')

        return {
            "level": aggregation,
            "periods": len(grouped),
            "records": records,
            "total_kwh": float(grouped['total_kwh'].sum()),
            "avg_per_period": float(grouped['total_kwh'].mean()),
        }

    def _calculate_statistics(
        self,
        df: pd.DataFrame,
        appliances: Optional[List[str]],
        metrics: List[str]
    ) -> Dict[str, Any]:
        """Calculate summary statistics."""
        consumption = df['query_consumption']

        # Convert to kWh (15-min intervals)
        total_kwh = consumption.sum() / 4

        # Number of days: use timestamp span for accurate daily average
        # This matches the ground truth calculation: (max_timestamp - min_timestamp).days + 1
        # Using timestamps (not dates) handles partial days correctly
        min_ts = df[self.timestamp_col].min()
        max_ts = df[self.timestamp_col].max()
        timestamp_span_days = (max_ts - min_ts).days + 1
        num_unique_days = df['date'].nunique()

        # Use timestamp span for average (matches ground truth calculation)
        num_days = timestamp_span_days

        stats = {
            "total_consumption_kwh": round(total_kwh, 2),
            "average_daily_kwh": round(total_kwh / max(num_days, 1), 2),
            "average_power_kw": round(consumption.mean(), 3),
            "peak_power_kw": round(consumption.max(), 3),
            "min_power_kw": round(consumption.min(), 3),
            "num_days": num_days,
            "num_unique_days": num_unique_days,
            "num_intervals": len(df),
        }

        # Add cost estimate if rate data available
        if self.rate_df is not None and "cost" in metrics:
            # Simplified cost calculation using average rate
            avg_rate = 0.15  # Default $/kWh
            stats["estimated_cost"] = round(total_kwh * avg_rate, 2)

        return stats

    def _get_appliance_breakdown(
        self,
        df: pd.DataFrame,
        appliances: List[str],
        aggregation: str
    ) -> Dict[str, Dict[str, float]]:
        """Get per-appliance consumption breakdown, sorted by consumption."""
        breakdown = {}

        # Calculate total for percentage calculation
        total_all_appliances = 0
        for appliance in appliances:
            if appliance in df.columns:
                total_all_appliances += df[appliance].sum() / 4

        for appliance in appliances:
            if appliance in df.columns:
                total_kwh = df[appliance].sum() / 4
                avg_kw = df[appliance].mean()
                peak_kw = df[appliance].max()
                percentage = (total_kwh / total_all_appliances * 100) if total_all_appliances > 0 else 0

                breakdown[appliance] = {
                    "total_kwh": round(total_kwh, 2),
                    "percentage": round(percentage, 1),
                    "average_kw": round(avg_kw, 3),
                    "peak_kw": round(peak_kw, 3),
                }

        # Sort by total_kwh descending
        breakdown = dict(sorted(breakdown.items(), key=lambda x: x[1]["total_kwh"], reverse=True))

        return breakdown

    def _identify_best_worst(
        self,
        records: List[Dict],
        aggregation: str
    ) -> Dict[str, Any]:
        """Identify best (lowest) and worst (highest) consumption periods."""
        if not records:
            return {}

        # Get the period column name based on aggregation
        period_col = {
            "daily": "date",
            "weekly": "year_week",
            "monthly": "year_month",
            "seasonal": "season",
        }.get(aggregation, "date")

        # Find best and worst by total_kwh
        best_record = min(records, key=lambda x: x.get("total_kwh", float("inf")))
        worst_record = max(records, key=lambda x: x.get("total_kwh", 0))

        return {
            "best_period": {
                "period": str(best_record.get(period_col, "N/A")),
                "total_kwh": best_record.get("total_kwh", 0),
                "daily_avg_kwh": best_record.get("daily_avg_kwh", 0),
            },
            "worst_period": {
                "period": str(worst_record.get(period_col, "N/A")),
                "total_kwh": worst_record.get("total_kwh", 0),
                "daily_avg_kwh": worst_record.get("daily_avg_kwh", 0),
            },
        }

    def calculate_rolling_average(
        self,
        window_days: int = 7,
        appliances: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Calculate rolling average consumption.

        Args:
            window_days: Rolling window size in days (default: 7)
            appliances: List of appliances to include (None = all)

        Returns:
            Dict with rolling average statistics and trend analysis
        """
        df = self.df.copy()
        df['consumption'] = self._calculate_total_consumption(df, appliances)

        # Aggregate to daily first
        daily = df.groupby('date').agg({
            'consumption': 'sum',
            self.timestamp_col: ['min', 'max']
        })
        daily.columns = ['total_kw', 'start_ts', 'end_ts']
        daily['total_kwh'] = daily['total_kw'] / 4
        daily = daily.reset_index().sort_values('date')

        if len(daily) < window_days:
            return {
                "success": False,
                "error": f"Insufficient data for {window_days}-day rolling average",
            }

        # Calculate rolling average
        daily['rolling_avg'] = daily['total_kwh'].rolling(window=window_days, min_periods=1).mean()

        # Calculate trend (compare recent vs earlier)
        if len(daily) >= window_days * 2:
            recent_avg = daily['rolling_avg'].iloc[-window_days:].mean()
            earlier_avg = daily['rolling_avg'].iloc[-window_days*2:-window_days].mean()
            if earlier_avg > 0:
                trend_pct = ((recent_avg - earlier_avg) / earlier_avg) * 100
                if trend_pct > 5:
                    trend = "increasing"
                elif trend_pct < -5:
                    trend = "decreasing"
                else:
                    trend = "stable"
            else:
                trend = "insufficient_data"
                trend_pct = 0
        else:
            trend = "insufficient_data"
            trend_pct = 0

        # Get last 30 days for chart data
        chart_data = daily[['date', 'total_kwh', 'rolling_avg']].tail(30).to_dict('records')

        return {
            "success": True,
            "statistics": {
                "window_days": window_days,
                "current_rolling_avg": round(daily['rolling_avg'].iloc[-1], 2),
                "min_rolling_avg": round(daily['rolling_avg'].min(), 2),
                "max_rolling_avg": round(daily['rolling_avg'].max(), 2),
                "overall_daily_avg": round(daily['total_kwh'].mean(), 2),
                "num_days": len(daily),
                "trend": trend,
                "trend_pct_change": round(trend_pct, 1),
            },
            "chart_data": chart_data,
        }

    def compare_weekday_weekend(
        self,
        appliances: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Compare weekday vs weekend consumption patterns.

        Args:
            appliances: List of appliances to include (None = all)

        Returns:
            Dict with weekday/weekend comparison statistics
        """
        df = self.df.copy()
        df['consumption'] = self._calculate_total_consumption(df, appliances)

        # Separate weekday and weekend data
        weekday_df = df[~df['is_weekend']]
        weekend_df = df[df['is_weekend']]

        def calc_stats(subset_df: pd.DataFrame, label: str) -> Dict[str, Any]:
            if subset_df.empty:
                return {"total_kwh": 0, "avg_daily_kwh": 0, "num_days": 0, "peak_kw": 0}

            total_kwh = subset_df['consumption'].sum() / 4
            num_days = subset_df['date'].nunique()
            avg_daily = total_kwh / max(num_days, 1)
            peak_kw = subset_df['consumption'].max()

            # Get hourly pattern
            hourly = subset_df.groupby('hour')['consumption'].mean()

            return {
                "total_kwh": round(total_kwh, 2),
                "avg_daily_kwh": round(avg_daily, 2),
                "num_days": num_days,
                "peak_kw": round(peak_kw, 3),
                "hourly_pattern": {int(h): round(v, 3) for h, v in hourly.items()},
            }

        weekday_stats = calc_stats(weekday_df, "weekday")
        weekend_stats = calc_stats(weekend_df, "weekend")

        # Calculate comparison
        diff = weekend_stats["avg_daily_kwh"] - weekday_stats["avg_daily_kwh"]
        if weekday_stats["avg_daily_kwh"] > 0:
            diff_pct = (diff / weekday_stats["avg_daily_kwh"]) * 100
        else:
            diff_pct = 0

        return {
            "success": True,
            "weekday": weekday_stats,
            "weekend": weekend_stats,
            "comparison": {
                "difference_kwh": round(diff, 2),
                "difference_pct": round(diff_pct, 1),
                "higher_on": "weekend" if diff > 0 else "weekday" if diff < 0 else "equal",
            },
        }

    def analyze_peak_hours(
        self,
        peak_start: int = 14,
        peak_end: int = 20,
        appliances: Optional[List[str]] = None,
        include_savings: bool = True,
        top_n_appliances: int = 5,
    ) -> Dict[str, Any]:
        """
        Analyze peak vs off-peak consumption with per-appliance breakdown and savings.

        Args:
            peak_start: Start hour of peak period (default: 14 / 2 PM)
            peak_end: End hour of peak period (default: 20 / 8 PM)
            appliances: List of appliances to include (None = all)
            include_savings: Include savings estimates if rate data available (default: True)
            top_n_appliances: Number of top appliances to include in breakdown (default: 5)

        Returns:
            Dict with peak/off-peak analysis, per-appliance breakdown, and savings estimates
        """
        df = self.df.copy()
        df['consumption'] = self._calculate_total_consumption(df, appliances)

        # Identify peak hours
        df['is_peak'] = (df['hour'] >= peak_start) & (df['hour'] < peak_end)

        # Calculate total consumption
        peak_kwh = df[df['is_peak']]['consumption'].sum() / 4
        off_peak_kwh = df[~df['is_peak']]['consumption'].sum() / 4
        total_kwh = peak_kwh + off_peak_kwh

        peak_pct = (peak_kwh / total_kwh * 100) if total_kwh > 0 else 0
        off_peak_pct = 100 - peak_pct

        # Calculate intensity (kWh per hour)
        peak_hours_per_day = peak_end - peak_start
        off_peak_hours_per_day = 24 - peak_hours_per_day
        num_days = df['date'].nunique()

        peak_intensity = peak_kwh / (peak_hours_per_day * num_days) if num_days > 0 else 0
        off_peak_intensity = off_peak_kwh / (off_peak_hours_per_day * num_days) if num_days > 0 else 0
        intensity_ratio = peak_intensity / off_peak_intensity if off_peak_intensity > 0 else 0

        # === PER-APPLIANCE PEAK BREAKDOWN ===
        appliance_breakdown = []
        appliance_list = appliances if appliances else self.appliance_cols

        for appliance in appliance_list:
            if appliance not in df.columns:
                continue

            app_peak_kwh = df[df['is_peak']][appliance].sum() / 4
            app_off_peak_kwh = df[~df['is_peak']][appliance].sum() / 4
            app_total_kwh = app_peak_kwh + app_off_peak_kwh

            if app_total_kwh < 0.01:  # Skip negligible appliances
                continue

            app_peak_pct = (app_peak_kwh / app_total_kwh * 100) if app_total_kwh > 0 else 0
            contribution_to_peak = (app_peak_kwh / peak_kwh * 100) if peak_kwh > 0 else 0

            app_daily_avg = app_total_kwh / num_days if num_days > 0 else 0
            app_monthly_est = app_daily_avg * 30

            appliance_breakdown.append({
                "appliance": appliance,
                "peak_kwh": round(app_peak_kwh, 2),
                "off_peak_kwh": round(app_off_peak_kwh, 2),
                "total_kwh": round(app_total_kwh, 2),
                "daily_avg_kwh": round(app_daily_avg, 2),
                "estimated_monthly_kwh": round(app_monthly_est, 0),
                "peak_pct_of_appliance": round(app_peak_pct, 1),
                "contribution_to_total_peak": round(contribution_to_peak, 1),
            })

        # Sort by peak consumption and take top N
        appliance_breakdown.sort(key=lambda x: x["peak_kwh"], reverse=True)
        appliance_breakdown = appliance_breakdown[:top_n_appliances]

        # === SAVINGS CALCULATION ===
        savings_info = None
        if include_savings:
            # Try to get rates from rate_df or use defaults
            peak_rate_cents = None
            off_peak_rate_cents = None

            if self.rate_df is not None and 'Rate (cents per kWh)' in self.rate_df.columns:
                # Get rates from actual data
                rate_col = 'Rate (cents per kWh)'
                peak_rate_cents = self.rate_df[rate_col].max()
                off_peak_rate_cents = self.rate_df[rate_col].min()
            else:
                # Use reasonable defaults (typical TOU rates)
                peak_rate_cents = 26.10  # cents/kWh
                off_peak_rate_cents = 9.28  # cents/kWh

            rate_diff_cents = peak_rate_cents - off_peak_rate_cents

            # Calculate savings: if we shift all peak consumption to off-peak
            # Savings = peak_kwh * (peak_rate - off_peak_rate)
            max_savings_dollars = (peak_kwh * rate_diff_cents) / 100

            # Calculate per-appliance savings potential
            appliance_savings = []
            for app_data in appliance_breakdown:
                # Savings from shifting this appliance's PEAK usage (not total!)
                app_savings = (app_data["peak_kwh"] * rate_diff_cents) / 100
                appliance_savings.append({
                    "appliance": app_data["appliance"],
                    "shiftable_peak_kwh": app_data["peak_kwh"],
                    "potential_savings_dollars": round(app_savings, 2),
                })

            savings_info = {
                "peak_rate_cents_per_kwh": round(peak_rate_cents, 2),
                "off_peak_rate_cents_per_kwh": round(off_peak_rate_cents, 2),
                "rate_difference_cents": round(rate_diff_cents, 2),
                "max_savings_if_all_shifted_dollars": round(max_savings_dollars, 2),
                "analysis_period_days": num_days,
                "per_appliance_savings": appliance_savings,
                "note": "Savings calculated as: shiftable_peak_kwh × rate_difference. "
                        "Only peak consumption can be shifted, not total consumption.",
            }

        # Generate insights
        insights = []
        if peak_pct > 40:
            insights.append(f"High peak usage ({peak_pct:.1f}%) - consider shifting loads to off-peak hours")
        elif peak_pct < 20:
            insights.append(f"Excellent peak management ({peak_pct:.1f}% during peak) - you're avoiding high-rate periods")

        if intensity_ratio > 1.5:
            insights.append("Peak hour intensity is 50%+ higher than off-peak - ideal candidates for load shifting")

        # Add insight about top peak consumer
        if appliance_breakdown:
            top_app = appliance_breakdown[0]
            insights.append(
                f"Top peak consumer: {top_app['appliance']} uses {top_app['peak_kwh']:.1f} kWh "
                f"during peak ({top_app['contribution_to_total_peak']:.0f}% of total peak)"
            )

        result = {
            "success": True,
            "peak_period": f"{peak_start}:00-{peak_end}:00",
            "peak_hours_per_day": peak_hours_per_day,
            "off_peak_hours_per_day": off_peak_hours_per_day,
            "num_days": num_days,
            "consumption": {
                "peak_kwh": round(peak_kwh, 2),
                "off_peak_kwh": round(off_peak_kwh, 2),
                "peak_pct": round(peak_pct, 1),
                "off_peak_pct": round(off_peak_pct, 1),
            },
            "intensity": {
                "peak_kwh_per_hour": round(peak_intensity, 3),
                "off_peak_kwh_per_hour": round(off_peak_intensity, 3),
                "ratio": round(intensity_ratio, 2),
            },
            "appliance_breakdown": appliance_breakdown,
            "insights": insights,
        }

        if savings_info:
            result["savings"] = savings_info

        return result
