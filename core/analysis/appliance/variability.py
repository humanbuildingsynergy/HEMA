# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# core/analysis/appliance/variability.py
"""Usage variability analysis for appliances using coefficient of variation."""
from typing import Dict, Any, List, Optional, Literal
import pandas as pd
import numpy as np
from utils.logger import setup_logger
from core.analysis.constants import NON_APPLIANCE_COLUMNS, get_appliance_columns

logger = setup_logger()

# Type alias for timeframe granularity
TimeframeGranularity = Literal["hourly", "daily", "weekly", "monthly"]


class UsageVariabilityAnalyzer:
    """
    Analyzes usage variability patterns for appliances using coefficient of variation (CV).

    The coefficient of variation (CV) is defined as:
        CV = standard_deviation / mean

    CV provides a normalized measure of variability that allows comparison across
    different appliances regardless of their absolute consumption levels.

    Interpretation:
    - CV < 0.5: Low variability (consistent usage)
    - 0.5 <= CV < 1.0: Moderate variability
    - CV >= 1.0: High variability (flexible/sporadic usage)
    """

    # Reference to shared constants for backward compatibility
    NON_APPLIANCE_COLUMNS = NON_APPLIANCE_COLUMNS

    def get_appliance_columns(self, df: pd.DataFrame) -> List[str]:
        """Get the list of appliance columns from a DataFrame."""
        return get_appliance_columns(df)

    def calculate_coefficient_of_variation(
        self,
        values: pd.Series,
        min_mean_threshold: float = 0.001
    ) -> Optional[float]:
        """
        Calculate coefficient of variation for a series of values.

        Args:
            values: Series of numeric values
            min_mean_threshold: Minimum mean value to avoid division by near-zero

        Returns:
            CV value or None if calculation is not meaningful
        """
        if values.empty:
            return None

        mean_val = values.mean()
        std_val = values.std()

        # Avoid division by very small or zero mean
        if mean_val < min_mean_threshold:
            return None

        return std_val / mean_val

    def aggregate_by_timeframe(
        self,
        df: pd.DataFrame,
        appliance: str,
        timeframe: TimeframeGranularity,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.Series:
        """
        Aggregate appliance consumption by the specified timeframe.

        Args:
            df: DataFrame with timestamp and appliance columns
            appliance: Name of appliance column
            timeframe: Aggregation level ("hourly", "daily", "weekly", "monthly")
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)

        Returns:
            Series of aggregated consumption values
        """
        # Ensure timestamp column
        if 'timestamp' not in df.columns:
            if 'local_15min' in df.columns:
                df = df.copy()
                df['timestamp'] = pd.to_datetime(df['local_15min'])
            else:
                raise ValueError("No timestamp column available")

        df = df.copy()

        # Apply date filters if provided
        if start_date:
            df = df[df['timestamp'] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df['timestamp'] <= pd.to_datetime(end_date)]

        if df.empty:
            return pd.Series(dtype=float)

        # Aggregate based on timeframe
        if timeframe == "hourly":
            # Group by date and hour
            df['period'] = df['timestamp'].dt.floor('H')
            aggregated = df.groupby('period')[appliance].sum()

        elif timeframe == "daily":
            # Group by date
            df['period'] = df['timestamp'].dt.date
            aggregated = df.groupby('period')[appliance].sum()

        elif timeframe == "weekly":
            # Group by year and week number
            df['period'] = df['timestamp'].dt.to_period('W')
            aggregated = df.groupby('period')[appliance].sum()

        elif timeframe == "monthly":
            # Group by year and month
            df['period'] = df['timestamp'].dt.to_period('M')
            aggregated = df.groupby('period')[appliance].sum()

        else:
            raise ValueError(f"Invalid timeframe: {timeframe}")

        # Convert to kWh (data is in kW, intervals are 15 min = 0.25 hours)
        aggregated = aggregated / 4

        return aggregated

    def calculate_variability(
        self,
        df: pd.DataFrame,
        appliance: str,
        timeframe: TimeframeGranularity = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate usage variability for a single appliance.

        Args:
            df: DataFrame containing appliance data
            appliance: Name of appliance column
            timeframe: Aggregation level for variability calculation
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)

        Returns:
            Dict containing:
                - cv: Coefficient of variation
                - mean: Mean consumption (kWh)
                - std: Standard deviation (kWh)
                - min: Minimum consumption (kWh)
                - max: Maximum consumption (kWh)
                - n_periods: Number of periods analyzed
                - variability_level: Categorical interpretation
        """
        try:
            logger.info(f"Calculating {timeframe} variability for {appliance}")

            # Aggregate data
            aggregated = self.aggregate_by_timeframe(
                df, appliance, timeframe, start_date, end_date
            )

            if aggregated.empty or len(aggregated) < 2:
                return {
                    'error': f'Insufficient data for {timeframe} variability calculation',
                    'n_periods': len(aggregated) if not aggregated.empty else 0
                }

            # Calculate statistics
            mean_val = aggregated.mean()
            std_val = aggregated.std()
            cv = self.calculate_coefficient_of_variation(aggregated)

            # Determine variability level
            if cv is None:
                variability_level = "unknown"
            elif cv < 0.5:
                variability_level = "low"
            elif cv < 1.0:
                variability_level = "moderate"
            else:
                variability_level = "high"

            return {
                'cv': cv,
                'mean_kwh': mean_val,
                'std_kwh': std_val,
                'min_kwh': aggregated.min(),
                'max_kwh': aggregated.max(),
                'n_periods': len(aggregated),
                'variability_level': variability_level,
                'timeframe': timeframe
            }

        except Exception as e:
            logger.error(f"Error calculating variability for {appliance}: {str(e)}")
            return {'error': str(e)}

    def analyze_usage_variability(
        self,
        df: pd.DataFrame,
        appliances: Optional[List[str]] = None,
        timeframe: TimeframeGranularity = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive usage variability analysis for multiple appliances.

        Args:
            df: DataFrame containing appliance data
            appliances: List of appliance names to analyze. If None, analyzes top 5 by consumption.
            timeframe: Aggregation level for variability calculation
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)

        Returns:
            Dict containing:
                - summary: Overall variability statistics
                - appliance_variability: Per-appliance variability metrics
                - rankings: Appliances sorted by CV (most variable first)
                - insights: Key observations
        """
        try:
            logger.info(f"Starting {timeframe} usage variability analysis")

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

            appliance_variability = {}
            valid_results = []

            for appliance in appliances:
                result = self.calculate_variability(
                    df, appliance, timeframe, start_date, end_date
                )
                appliance_variability[appliance] = result

                if 'error' not in result and result.get('cv') is not None:
                    valid_results.append({
                        'appliance': appliance,
                        'cv': result['cv'],
                        'variability_level': result['variability_level'],
                        'mean_kwh': result['mean_kwh']
                    })

            # Sort by CV (most variable first)
            rankings = sorted(valid_results, key=lambda x: x['cv'], reverse=True)

            # Generate insights
            insights = self._generate_variability_insights(rankings, timeframe)

            # Calculate summary
            if valid_results:
                cv_values = [r['cv'] for r in valid_results]
                summary = {
                    'appliances_analyzed': len(appliances),
                    'timeframe': timeframe,
                    'date_range': {
                        'start': start_date or 'all data',
                        'end': end_date or 'all data'
                    },
                    'avg_cv': np.mean(cv_values),
                    'most_variable': rankings[0]['appliance'] if rankings else None,
                    'most_consistent': rankings[-1]['appliance'] if rankings else None,
                    'high_variability_count': sum(1 for r in valid_results if r['variability_level'] == 'high'),
                    'low_variability_count': sum(1 for r in valid_results if r['variability_level'] == 'low'),
                }
            else:
                summary = {
                    'appliances_analyzed': len(appliances),
                    'timeframe': timeframe,
                    'error': 'No valid variability calculations'
                }

            return {
                'summary': summary,
                'appliance_variability': appliance_variability,
                'rankings': rankings,
                'insights': insights
            }

        except Exception as e:
            logger.error(f"Error in usage variability analysis: {str(e)}")
            raise

    def _generate_variability_insights(
        self,
        rankings: List[Dict],
        timeframe: str
    ) -> List[str]:
        """Generate insights from variability analysis."""
        insights = []

        if not rankings:
            return ["Insufficient data to generate variability insights"]

        # Most variable appliance
        most_variable = rankings[0]
        insights.append(
            f"{most_variable['appliance']} has the highest {timeframe} usage variability "
            f"(CV={most_variable['cv']:.2f}) - good candidate for load shifting"
        )

        # Most consistent appliance
        most_consistent = rankings[-1]
        if most_consistent['cv'] < 0.5:
            insights.append(
                f"{most_consistent['appliance']} has consistent {timeframe} usage "
                f"(CV={most_consistent['cv']:.2f}) - predictable baseload"
            )

        # High variability appliances (CV > 1.0)
        high_var = [r for r in rankings if r['cv'] >= 1.0]
        if high_var:
            names = ", ".join([r['appliance'] for r in high_var])
            insights.append(
                f"High variability appliances ({names}) offer the most "
                f"flexibility for demand response programs"
            )

        # Low variability (always-on) appliances
        low_var = [r for r in rankings if r['cv'] < 0.3]
        if low_var:
            names = ", ".join([r['appliance'] for r in low_var])
            insights.append(
                f"Low variability appliances ({names}) may be running continuously "
                f"- check for efficiency opportunities"
            )

        return insights
