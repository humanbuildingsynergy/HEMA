# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
from typing import Optional
import pandas as pd
from utils.logger import setup_logger

logger = setup_logger()


class DataValidator:
    """Handles data validation for energy consumption data."""

    def __init__(self):
        # Only local_15min is truly required - appliance columns vary by dataset
        self.required_columns = {'local_15min'}
        # Optional columns that may be present
        self.optional_columns = {'dataid', 'grid', 'solar', 'solar2'}
        # Columns to exclude when identifying appliances
        self.non_appliance_columns = {
            'local_15min', 'dataid', 'grid', 'solar', 'solar2',
            'leg1v', 'leg2v', 'Solar power generation 1', 'Solar power generation 2'
        }
        # Threshold handler for filtering standby power
        self._threshold_handler = None

    def load_and_validate(
        self,
        file_path: str,
        thresholds_file: Optional[str] = None,
        apply_thresholds: bool = True
    ) -> pd.DataFrame:
        """
        Load data from a CSV file and validate it.

        Args:
            file_path: Path to the CSV file
            thresholds_file: Optional path to appliance thresholds CSV file.
                            If provided and apply_thresholds=True, values below
                            threshold will be zeroed out (treated as standby power).
            apply_thresholds: Whether to apply threshold filtering (default True)

        Returns:
            pd.DataFrame: Validated DataFrame ready for analysis

        Raises:
            ValueError: If the file cannot be loaded or validation fails
        """
        logger.info(f"Loading data from: {file_path}")

        try:
            df = pd.read_csv(file_path)
            logger.info(f"Loaded {len(df)} rows with {len(df.columns)} columns")

            # Validate the data
            validated_df = self.validate_data(df)

            # Apply thresholds if provided
            if thresholds_file and apply_thresholds:
                validated_df = self._apply_thresholds(validated_df, thresholds_file)

            return validated_df

        except Exception as e:
            logger.error(f"Error loading file {file_path}: {str(e)}")
            raise ValueError(f"Failed to load data: {str(e)}")

    def _apply_thresholds(self, df: pd.DataFrame, thresholds_file: str) -> pd.DataFrame:
        """
        Apply appliance thresholds to filter standby power.

        Args:
            df: Validated DataFrame
            thresholds_file: Path to thresholds CSV file

        Returns:
            DataFrame with standby power filtered out
        """
        from core.data.threshold_handler import ThresholdHandler

        try:
            if self._threshold_handler is None:
                self._threshold_handler = ThresholdHandler()

            self._threshold_handler.load_thresholds(thresholds_file)
            df = self._threshold_handler.apply_thresholds(df, mode='zero_below')
            logger.info("Appliance thresholds applied - standby power filtered")
            return df

        except Exception as e:
            logger.warning(f"Could not apply thresholds: {e}. Continuing without filtering.")
            return df

    def validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate the input data format and content.

        Args:
            df (pd.DataFrame): Input DataFrame containing energy consumption data

        Returns:
            pd.DataFrame: Cleaned DataFrame with invalid rows removed

        Raises:
            ValueError: If required columns are missing from the DataFrame
        """
        # Check if required columns exist
        missing_columns = self.required_columns - set(df.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        # Log initial data shape
        initial_rows = len(df)
        logger.info(f"Initial number of rows: {initial_rows}")

        # Make a copy to avoid modifying the original
        cleaned_df = df.copy()

        # Convert timestamp column
        try:
            cleaned_df['local_15min'] = pd.to_datetime(cleaned_df['local_15min'])
            logger.info("Timestamp column converted successfully")
        except Exception as e:
            logger.error(f"Error converting timestamp: {str(e)}")
            raise ValueError(f"Timestamp conversion failed: {str(e)}")

        # Remove rows with null timestamps
        cleaned_df = cleaned_df.dropna(subset=['local_15min'])

        # Log number of rows removed
        removed_rows = initial_rows - len(cleaned_df)
        if removed_rows > 0:
            logger.warning(f"Removed {removed_rows} rows with null timestamps")

        # Handle optional columns if present
        if 'dataid' in cleaned_df.columns:
            cleaned_df['dataid'] = pd.to_numeric(cleaned_df['dataid'], errors='coerce')

        if 'grid' in cleaned_df.columns:
            cleaned_df['grid'] = pd.to_numeric(cleaned_df['grid'], errors='coerce')

        # Identify appliance columns and ensure they are numeric
        appliance_cols = [col for col in cleaned_df.columns if col not in self.non_appliance_columns]
        for col in appliance_cols:
            cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors='coerce')

        logger.info(f"Found {len(appliance_cols)} appliance columns")
        logger.info(f"Final number of rows after validation: {len(cleaned_df)}")

        # Log summary statistics for total consumption if possible
        if appliance_cols:
            total_consumption = cleaned_df[appliance_cols].sum(axis=1)
            logger.info(f"\nTotal consumption statistics (kWh per 15-min interval):")
            logger.info(f"  Mean: {total_consumption.mean():.4f}")
            logger.info(f"  Max: {total_consumption.max():.4f}")
            logger.info(f"  Min: {total_consumption.min():.4f}")

        return cleaned_df

    def get_appliance_columns(self, df: pd.DataFrame) -> list:
        """
        Get the list of appliance columns from a DataFrame.

        Args:
            df: DataFrame to analyze

        Returns:
            List of appliance column names
        """
        return [col for col in df.columns if col not in self.non_appliance_columns]