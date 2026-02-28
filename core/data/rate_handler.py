# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
import pandas as pd
from utils.logger import setup_logger
from typing import Optional

logger = setup_logger()

class RateHandler:
    """Handles all time-of-use (TOU) rate operations for energy data."""
    
    def __init__(self):
        self.rate_lookup_cache = {}  # Cache for performance
        
    def load_rate_data(self, rate_file: str) -> pd.DataFrame:
        """Load and validate utility rate data."""
        try:
            logger.info(f"Loading rate data from {rate_file}")
            rate_df = pd.read_csv(rate_file)

            # Validate required columns
            required_columns = ['hour_start', 'hour_end', 'month', 'day_type_id', 'rate_kwh']
            missing_columns = [col for col in required_columns if col not in rate_df.columns]
            if missing_columns:
                raise ValueError(f"Missing required rate data columns: {missing_columns}")

            # Convert hour and month columns to integers
            rate_df['hour_start'] = rate_df['hour_start'].astype(int)
            rate_df['hour_end'] = rate_df['hour_end'].astype(int)
            rate_df['month'] = rate_df['month'].astype(int)
            rate_df['day_type_id'] = rate_df['day_type_id'].astype(int)

            # Add adjustment column if not present (default to 0)
            if 'adjustment_kwh' not in rate_df.columns:
                rate_df['adjustment_kwh'] = 0.0
                logger.info("No adjustment_kwh column found, defaulting to 0")

            # Validate data ranges
            self._validate_rate_data(rate_df)

            # Expand hour ranges for efficient lookup
            rate_df = self._expand_hour_ranges(rate_df)

            logger.info(f"Rate data loaded successfully. {len(rate_df)} rate periods found")
            return rate_df

        except Exception as e:
            logger.error(f"Error loading rate data: {str(e)}")
            raise
    
    def _validate_rate_data(self, rate_df: pd.DataFrame):
        """Validate rate data for completeness and correctness."""
        # Check hour ranges
        invalid_hours = rate_df[
            (rate_df['hour_start'] < 0) | (rate_df['hour_start'] > 23) |
            (rate_df['hour_end'] < 0) | (rate_df['hour_end'] > 23) |
            (rate_df['hour_start'] > rate_df['hour_end'])
        ]
        if not invalid_hours.empty:
            raise ValueError(f"Invalid hour ranges found in rate data: {invalid_hours}")
        
        # Check month ranges
        invalid_months = rate_df[(rate_df['month'] < 1) | (rate_df['month'] > 12)]
        if not invalid_months.empty:
            raise ValueError(f"Invalid months found in rate data: {invalid_months}")
        
        # Check day types (0=weekday, 1=weekend)
        invalid_day_types = rate_df[~rate_df['day_type_id'].isin([0, 1])]
        if not invalid_day_types.empty:
            raise ValueError(f"Invalid day_type_id found (must be 0 or 1): {invalid_day_types}")
        
        # Check for negative rates
        negative_rates = rate_df[rate_df['rate_kwh'] < 0]
        if not negative_rates.empty:
            logger.warning(f"Negative rates found (export rates?): {len(negative_rates)} entries")
    
    def _expand_hour_ranges(self, rate_df: pd.DataFrame) -> pd.DataFrame:
        """Expand hour ranges into individual hour entries for faster lookup."""
        expanded_rows = []

        for _, row in rate_df.iterrows():
            # Ensure hour values are integers
            hour_start = int(row['hour_start'])
            hour_end = int(row['hour_end'])

            # Handle hour ranges that cross midnight (e.g., 22-5)
            if hour_start <= hour_end:
                hours = list(range(hour_start, hour_end + 1))
            else:
                # Cross midnight: 22-5 becomes [22,23,0,1,2,3,4,5]
                hours = list(range(hour_start, 24)) + list(range(0, hour_end + 1))

            for hour in hours:
                expanded_row = row.copy()
                expanded_row['hour'] = hour
                expanded_rows.append(expanded_row)

        return pd.DataFrame(expanded_rows)
    
    def get_rate(self, timestamp: pd.Timestamp, rate_data: pd.DataFrame) -> float:
        """Get the appropriate TOU rate for a given timestamp."""
        try:
            month = timestamp.month
            hour = timestamp.hour
            is_weekend = 1 if timestamp.dayofweek >= 5 else 0
            
            # Create cache key for performance
            cache_key = (month, hour, is_weekend)
            if cache_key in self.rate_lookup_cache:
                return self.rate_lookup_cache[cache_key]
            
            # Find matching rate
            rate_row = rate_data[
                (rate_data['month'] == month) &
                (rate_data['day_type_id'] == is_weekend) &
                (rate_data['hour'] == hour)
            ]
            
            if rate_row.empty:
                # Try to find a default rate (any month, same hour and day type)
                fallback_rate = rate_data[
                    (rate_data['day_type_id'] == is_weekend) &
                    (rate_data['hour'] == hour)
                ]
                
                if fallback_rate.empty:
                    logger.error(f"No rate found for {timestamp} (month={month}, hour={hour}, weekend={is_weekend})")
                    raise ValueError(f"No rate available for timestamp {timestamp}")
                else:
                    rate_row = fallback_rate.iloc[[0]]  # Use first available fallback
                    logger.warning(f"Using fallback rate for {timestamp}")
            
            # Calculate total rate
            total_rate = float(rate_row['rate_kwh'].iloc[0] + rate_row['adjustment_kwh'].iloc[0])
            
            # Cache result
            self.rate_lookup_cache[cache_key] = total_rate
            
            return total_rate
            
        except Exception as e:
            logger.error(f"Error getting rate for {timestamp}: {str(e)}")
            raise
    
    def get_rate_summary(self, rate_data: pd.DataFrame) -> dict:
        """Get summary statistics about the rate structure."""
        try:
            summary = {
                'total_rate_periods': len(rate_data),
                'unique_months': sorted(rate_data['month'].unique().tolist()),
                'rate_range': {
                    'min': float(rate_data['rate_kwh'].min()),
                    'max': float(rate_data['rate_kwh'].max()),
                    'avg': float(rate_data['rate_kwh'].mean())
                },
                'has_adjustments': (rate_data['adjustment_kwh'] != 0).any(),
                'weekend_rates': len(rate_data[rate_data['day_type_id'] == 1]) > 0,
                'hours_covered': sorted(rate_data['hour'].unique().tolist())
            }
            
            logger.info(f"Rate summary: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating rate summary: {str(e)}")
            return {}
    
    def clear_cache(self):
        """Clear the rate lookup cache."""
        self.rate_lookup_cache.clear()
        logger.info("Rate lookup cache cleared")
