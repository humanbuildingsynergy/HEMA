# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
from typing import Optional, List
import pandas as pd
from utils.logger import setup_logger
from core.analysis.constants import NON_APPLIANCE_COLUMNS, get_appliance_columns

logger = setup_logger()


class FeatureEngineer:
    """Handles feature engineering for energy consumption data."""

    # Reference to shared constants for backward compatibility
    NON_APPLIANCE_COLUMNS = NON_APPLIANCE_COLUMNS

    def __init__(self, rate_handler=None):
        """
        Initialize FeatureEngineer.

        Args:
            rate_handler: Optional RateHandler for cost calculations
        """
        self.rate_handler = rate_handler

    def get_appliance_columns(self, df: pd.DataFrame) -> List[str]:
        """Get the list of appliance columns from a DataFrame."""
        return get_appliance_columns(df)

    def add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add time-based features to the DataFrame."""
        df = df.copy()
        df['timestamp'] = pd.to_datetime(df['local_15min'])
        df['hour'] = df['timestamp'].dt.hour
        df['day'] = df['timestamp'].dt.day
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['is_weekend'] = df['timestamp'].dt.dayofweek.isin([5, 6]).astype(int)
        return df

    def add_energy_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate comprehensive energy consumption metrics.

        Works with both grid-based data and appliance-only data.

        Args:
            df: DataFrame with energy consumption data

        Returns:
            DataFrame with additional energy metrics
        """
        try:
            logger.info("Calculating energy consumption metrics")
            df = df.copy()

            # Get appliance columns
            appliance_cols = self.get_appliance_columns(df)
            logger.info(f"Found {len(appliance_cols)} appliance columns for metrics")

            # Check if we have a grid column or need to sum appliances
            has_grid = 'grid' in df.columns and not df['grid'].isna().all()

            # Check for solar data (various column names)
            solar_cols = ['solar', 'Solar power generation 1', 'Solar power generation 2']
            solar_col = None
            for col in solar_cols:
                if col in df.columns and not df[col].isna().all():
                    solar_col = col
                    break
            has_solar = solar_col is not None

            if has_grid:
                # Use grid column for total consumption
                df['total_consumption'] = df['grid'].fillna(0)
                df['net_consumption'] = df['grid'].fillna(0)
            else:
                # Sum appliance columns for total consumption
                if appliance_cols:
                    df['total_consumption'] = df[appliance_cols].sum(axis=1)
                    df['net_consumption'] = df['total_consumption']
                else:
                    logger.warning("No appliance columns found to calculate consumption")
                    df['total_consumption'] = 0
                    df['net_consumption'] = 0

            if has_solar:
                logger.info(f"Solar data detected in column: {solar_col}")
                solar_values = df[solar_col].fillna(0)
                df['solar_generation'] = solar_values

                # Solar contribution percentage
                df['solar_contribution'] = (
                    (solar_values / df['total_consumption'].replace(0, 1)) * 100
                ).clip(0, 100)

                # Grid dependency
                df['grid_dependency'] = 100 - df['solar_contribution']
            else:
                logger.info("No solar data - calculating consumption-only metrics")
                df['solar_generation'] = 0
                df['solar_contribution'] = 0
                df['grid_dependency'] = 100

            # Flag periods of potential grid export (net negative consumption)
            df['is_exporting'] = df['net_consumption'] < 0
            df['export_amount'] = df['net_consumption'].clip(upper=0).abs()

            logger.info(f"Energy metrics calculation completed (solar: {'yes' if has_solar else 'no'})")
            return df

        except Exception as e:
            logger.error(f"Error calculating energy metrics: {str(e)}")
            raise
    
    def add_cost_features(self, df: pd.DataFrame, rate_data: pd.DataFrame) -> pd.DataFrame:
        """Add comprehensive cost-related features including appliance-specific costs."""
        try:
            logger.info("Adding cost features including appliance-specific costs")
            
            # Get electricity rate for each timestamp
            df['rate'] = df.apply(
                lambda x: self.rate_handler.get_rate(x['timestamp'], rate_data), axis=1
            )
            
            # Calculate total interval cost (net grid consumption)
            df['interval_cost'] = df['net_consumption'] * df['rate'] / 4
            
            # Identify appliance columns (exclude system columns)
            system_columns = {
                'dataid', 'local_15min', 'timestamp', 'hour', 'day', 'day_of_week', 
                'is_weekend', 'grid', 'solar', 'total_consumption', 
                'net_consumption', 'solar_contribution', 'grid_dependency', 
                'is_exporting', 'export_amount', 'rate', 'interval_cost', 'rate_period'
            }
            
            # Find appliance columns (numeric columns that aren't system columns)
            appliance_columns = []
            for col in df.columns:
                if (col not in system_columns and 
                    pd.api.types.is_numeric_dtype(df[col]) and 
                    not col.endswith('_cost')):  # Avoid processing already created cost columns
                    appliance_columns.append(col)
            
            # Calculate cost for each detected appliance
            appliances_with_costs = []
            for appliance in appliance_columns:
                try:
                    cost_column = f'{appliance}_cost'
                    df[cost_column] = df[appliance] * df['rate'] / 4
                    appliances_with_costs.append(appliance)
                except Exception as e:
                    logger.warning(f"Could not calculate cost for {appliance}: {str(e)}")
            
            
            # Calculate solar-related costs if solar data exists
            if 'solar' in df.columns and not df['solar'].isna().all():
                # Solar savings = solar generation × current rate
                df['solar_savings'] = df['solar'].fillna(0) * df['rate'] / 4
                
                # Net export revenue (when exporting to grid)
                df['export_revenue'] = df.apply(
                    lambda x: abs(x['grid']) * x['rate'] / 4 if x.get('is_exporting', False) else 0,
                    axis=1
                )
            
            # Add rate period for TOU analysis (using hour as simple rate period indicator)
            df['rate_period'] = df['hour']
            
            logger.info(f"Cost features added successfully. Appliances with costs: {appliances_with_costs}")
            return df
            
        except Exception as e:
            logger.error(f"Error adding cost features: {str(e)}")
            raise
