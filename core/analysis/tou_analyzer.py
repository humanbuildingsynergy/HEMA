# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
from typing import Dict, Any, Optional, List
import pandas as pd
from utils.logger import setup_logger

logger = setup_logger()


class TOUAnalyzer:
    """Handles analysis of utility rate patterns - supports both TOU and flat rates."""

    # Default TOU periods (can be customized based on utility)
    DEFAULT_PERIODS = {
        'off_peak': list(range(0, 6)) + list(range(22, 24)),  # 10PM-6AM
        'mid_peak': list(range(6, 14)) + list(range(20, 22)),  # 6AM-2PM, 8PM-10PM
        'on_peak': list(range(14, 20)),  # 2PM-8PM
    }

    def analyze(self, df: pd.DataFrame, rate_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Analyze energy usage relative to utility rate structure.

        Automatically detects rate type (TOU vs flat) and provides appropriate analysis:
        - TOU: Peak/off-peak breakdown and load shifting savings
        - Flat: Time-of-day patterns and total consumption costs

        Args:
            df: DataFrame containing energy consumption data
            rate_df: Optional DataFrame with rate data

        Returns:
            Dict containing rate-appropriate metrics, savings potential, and recommendations
        """
        try:
            # Detect rate type
            is_tou = self._detect_rate_type(rate_df)
            rate_type = "tou" if is_tou else "flat"
            logger.info(f"Analyzing utility rate patterns (rate_type={rate_type})")

            df = df.copy()

            # Ensure timestamp and hour columns exist
            if 'timestamp' not in df.columns:
                if 'local_15min' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['local_15min'])
                else:
                    raise ValueError("No timestamp column available for rate analysis")

            if 'hour' not in df.columns:
                df['hour'] = df['timestamp'].dt.hour

            # Determine consumption column
            consumption_col = self._get_consumption_column(df)

            if is_tou:
                return self._analyze_tou(df, consumption_col, rate_df)
            else:
                return self._analyze_flat_rate(df, consumption_col, rate_df)

        except Exception as e:
            logger.error(f"Error in rate analysis: {str(e)}")
            raise

    def _detect_rate_type(self, rate_df: Optional[pd.DataFrame]) -> bool:
        """
        Detect whether the rate structure is TOU or flat.

        Returns:
            True if TOU (time-varying rates), False if flat rate
        """
        if rate_df is None:
            # Default to TOU if no rate data provided
            logger.info("No rate data provided, defaulting to TOU analysis")
            return True

        # Check if rate varies by time of day
        if 'Start Time' in rate_df.columns:
            unique_times = rate_df['Start Time'].nunique()
            is_tou = unique_times > 1
            logger.info(f"Rate type detection: {unique_times} unique time periods -> {'TOU' if is_tou else 'Flat'}")
            return is_tou
        elif 'hour' in rate_df.columns:
            unique_hours = rate_df['hour'].nunique()
            return unique_hours > 1

        # Default to TOU
        return True

    def _get_consumption_column(self, df: pd.DataFrame) -> str:
        """Determine the consumption column to use."""
        if 'net_consumption' in df.columns:
            return 'net_consumption'
        elif 'total_consumption' in df.columns:
            return 'total_consumption'
        else:
            # Calculate from appliance columns
            non_appliance = {
                'local_15min', 'timestamp', 'hour', 'day', 'day_of_week',
                'is_weekend', 'dataid', 'grid', 'solar', 'solar2',
                'Solar power generation 1', 'Solar power generation 2'
            }
            appliance_cols = [c for c in df.columns
                              if c not in non_appliance and pd.api.types.is_numeric_dtype(df[c])]
            if appliance_cols:
                df['_consumption'] = df[appliance_cols].sum(axis=1)
                return '_consumption'
            else:
                raise ValueError("No consumption data available for analysis")

    def _analyze_tou(
        self,
        df: pd.DataFrame,
        consumption_col: str,
        rate_df: Optional[pd.DataFrame]
    ) -> Dict[str, Any]:
        """Analyze consumption for TOU rate structure."""
        # Assign TOU periods based on hour
        df['tou_period'] = df['hour'].apply(self._get_period)

        # Calculate consumption by period
        period_breakdown = {}
        total_consumption = df[consumption_col].sum()

        for period in ['off_peak', 'mid_peak', 'on_peak']:
            period_data = df[df['tou_period'] == period]
            period_kwh = period_data[consumption_col].sum() / 4  # Convert to kWh
            period_pct = (period_data[consumption_col].sum() / total_consumption * 100) if total_consumption > 0 else 0

            period_breakdown[period] = {
                'kwh': period_kwh,
                'percentage': period_pct
            }

        # Calculate savings potential
        savings_potential = self._calculate_tou_savings(df, consumption_col, rate_df)

        # Generate recommendations
        recommendations = self._generate_tou_recommendations(period_breakdown)

        return {
            'rate_type': 'tou',
            'period_breakdown': period_breakdown,
            'savings_potential': savings_potential,
            'recommendations': recommendations,
        }

    def _analyze_flat_rate(
        self,
        df: pd.DataFrame,
        consumption_col: str,
        rate_df: Optional[pd.DataFrame]
    ) -> Dict[str, Any]:
        """Analyze consumption for flat rate structure."""
        # For flat rate, analyze time-of-day patterns for general insights
        total_kwh = df[consumption_col].sum() / 4  # Convert to kWh

        # Calculate hourly profile
        hourly_avg = df.groupby('hour')[consumption_col].mean() / 4  # kW average per hour
        peak_hour = hourly_avg.idxmax()
        min_hour = hourly_avg.idxmin()

        # Time-of-day breakdown (morning, afternoon, evening, night)
        time_periods = {
            'night': list(range(0, 6)),      # 12AM-6AM
            'morning': list(range(6, 12)),   # 6AM-12PM
            'afternoon': list(range(12, 18)),  # 12PM-6PM
            'evening': list(range(18, 24)),  # 6PM-12AM
        }

        period_breakdown = {}
        total_consumption = df[consumption_col].sum()

        for period_name, hours in time_periods.items():
            period_data = df[df['hour'].isin(hours)]
            period_kwh = period_data[consumption_col].sum() / 4
            period_pct = (period_data[consumption_col].sum() / total_consumption * 100) if total_consumption > 0 else 0

            period_breakdown[period_name] = {
                'kwh': period_kwh,
                'percentage': period_pct
            }

        # Get flat rate from rate_df if available
        flat_rate = self._get_flat_rate(rate_df)
        total_cost = total_kwh * flat_rate

        # Calculate cost optimization potential (demand management)
        savings_potential = self._calculate_flat_rate_savings(df, consumption_col, flat_rate)

        # Generate flat-rate specific recommendations
        recommendations = self._generate_flat_rate_recommendations(
            period_breakdown, peak_hour, total_kwh
        )

        return {
            'rate_type': 'flat',
            'total_kwh': total_kwh,
            'total_cost': total_cost,
            'flat_rate': flat_rate,
            'period_breakdown': period_breakdown,
            'peak_hour': int(peak_hour),
            'min_hour': int(min_hour),
            'savings_potential': savings_potential,
            'recommendations': recommendations,
        }

    def _get_period(self, hour: int) -> str:
        """Determine TOU period based on hour."""
        if hour in self.DEFAULT_PERIODS['off_peak']:
            return 'off_peak'
        elif hour in self.DEFAULT_PERIODS['on_peak']:
            return 'on_peak'
        else:
            return 'mid_peak'

    def _get_flat_rate(self, rate_df: Optional[pd.DataFrame]) -> float:
        """Extract flat rate from rate data."""
        if rate_df is None:
            return 0.12  # Default estimate

        rate_col = 'Rate (cents per kWh)' if 'Rate (cents per kWh)' in rate_df.columns else 'rate_kwh'
        if rate_col in rate_df.columns:
            # Convert cents to dollars if needed
            rate = rate_df[rate_col].mean()
            if rate > 1:  # Likely in cents
                return rate / 100
            return rate

        return 0.12  # Default

    def _calculate_tou_savings(
        self,
        df: pd.DataFrame,
        consumption_col: str,
        rate_df: Optional[pd.DataFrame]
    ) -> Dict[str, float]:
        """Estimate potential savings from load shifting for TOU rates."""
        # Default rate estimates if no rate data provided
        rates = {
            'off_peak': 0.08,
            'mid_peak': 0.12,
            'on_peak': 0.20,
        }

        on_peak_consumption = df[df['tou_period'] == 'on_peak'][consumption_col].sum() / 4

        # Estimate 20% of on-peak could be shifted to off-peak
        shiftable_kwh = on_peak_consumption * 0.2
        rate_difference = rates['on_peak'] - rates['off_peak']
        monthly_savings = shiftable_kwh * rate_difference

        return {
            'monthly_savings': monthly_savings,
            'peak_reduction_kwh': shiftable_kwh,
        }

    def _calculate_flat_rate_savings(
        self,
        df: pd.DataFrame,
        consumption_col: str,
        flat_rate: float
    ) -> Dict[str, float]:
        """Estimate potential savings for flat rate through consumption reduction."""
        total_kwh = df[consumption_col].sum() / 4

        # Estimate 10% reduction through efficiency improvements
        reduction_kwh = total_kwh * 0.10
        monthly_savings = reduction_kwh * flat_rate

        # Calculate peak demand for demand charge awareness
        peak_demand_kw = df[consumption_col].max()

        return {
            'monthly_savings': monthly_savings,
            'reduction_potential_kwh': reduction_kwh,
            'peak_demand_kw': peak_demand_kw,
        }

    def _generate_tou_recommendations(self, period_breakdown: Dict) -> List[str]:
        """Generate recommendations for TOU rate customers."""
        recommendations = []

        on_peak_pct = period_breakdown.get('on_peak', {}).get('percentage', 0)
        off_peak_pct = period_breakdown.get('off_peak', {}).get('percentage', 0)

        if on_peak_pct > 40:
            recommendations.append(
                f"High on-peak usage ({on_peak_pct:.0f}%). Consider shifting laundry, "
                "dishwasher, and EV charging to off-peak hours."
            )

        if off_peak_pct < 20:
            recommendations.append(
                "Low off-peak usage. Pre-cool/heat your home during off-peak hours "
                "to reduce on-peak HVAC load."
            )

        recommendations.append(
            "Schedule high-power appliances (washer, dryer, dishwasher) "
            "for evening/overnight off-peak periods."
        )

        return recommendations

    def _generate_flat_rate_recommendations(
        self,
        period_breakdown: Dict,
        peak_hour: int,
        total_kwh: float
    ) -> List[str]:
        """Generate recommendations for flat rate customers."""
        recommendations = []

        # Focus on total consumption reduction
        recommendations.append(
            "With a flat rate, focus on reducing total consumption rather than "
            "shifting usage times. Each kWh saved directly reduces your bill."
        )

        # Identify highest usage period
        max_period = max(period_breakdown.items(), key=lambda x: x[1]['kwh'])
        recommendations.append(
            f"Highest usage is during {max_period[0]} ({max_period[1]['percentage']:.0f}% of total). "
            f"Review appliance usage during this time for efficiency opportunities."
        )

        # Peak hour insight
        recommendations.append(
            f"Peak demand occurs around {peak_hour}:00. Avoid running multiple "
            "high-power appliances simultaneously to reduce demand spikes."
        )

        # Consider TOU if beneficial
        if period_breakdown.get('night', {}).get('percentage', 0) > 25:
            recommendations.append(
                "You have significant overnight usage. Consider switching to a TOU rate plan - "
                "you could benefit from lower off-peak rates."
            )

        return recommendations
