# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
"""
Utility functions for file operations and validation.
"""

from pathlib import Path
from typing import Tuple
from utils.logger import setup_logger

logger = setup_logger()

def validate_files(data_file: str, rate_file: str) -> Tuple[Path, Path]:
    """
    Validate energy data and rate files existence and format.
    
    This function checks if the provided files exist and are in CSV format.
    It converts the file paths to Path objects for better path handling.
    
    Args:
        data_file: Path to energy consumption data file
        rate_file: Path to rate data file
        
    Returns:
        Tuple[Path, Path]: Tuple containing validated Path objects for data_file and rate_file
        
    Raises:
        FileNotFoundError: If either file doesn't exist
        ValueError: If files are not in CSV format
    """
    data_path = Path(data_file)
    rate_path = Path(rate_file)
    
    # Check if files exist
    if not data_path.exists():
        logger.error(f"Energy data file not found: {data_file}")
        raise FileNotFoundError(f"Energy data file not found: {data_file}")
    if not rate_path.exists():
        logger.error(f"Rate file not found: {rate_file}")
        raise FileNotFoundError(f"Rate file not found: {rate_file}")
        
    # Check if files are CSV
    if data_path.suffix.lower() != '.csv':
        logger.error(f"Energy data file must be CSV format: {data_file}")
        raise ValueError(f"Energy data file must be CSV format: {data_file}")
    if rate_path.suffix.lower() != '.csv':
        logger.error(f"Rate file must be CSV format: {rate_file}")
        raise ValueError(f"Rate file must be CSV format: {rate_file}")
        
    return data_path, rate_path