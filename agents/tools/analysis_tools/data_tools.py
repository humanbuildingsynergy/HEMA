# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/tools/analysis_tools/data_tools.py
"""Data access and loading tools for energy analysis."""
import os
from typing import Optional
from langchain_core.tools import tool
from config.config import DEFAULT_ENERGY_FILE, DEFAULT_RATE_FILE, DEFAULT_THRESHOLDS_FILE, DATA_DIR
from utils.logger import setup_logger
from .cache import _data_cache, set_simulated_time, get_eval_data_days

logger = setup_logger()


@tool
def get_data_boundaries() -> str:
    """
    Get the date boundaries and availability of the loaded energy data.

    This tool returns critical information about what data is available for analysis,
    including the date range, data completeness, and whether historical comparisons
    are possible. Use this BEFORE attempting date-based comparisons or historical analysis.

    Returns:
        Information about data boundaries including:
        - Start and end dates of available data
        - Total days of data coverage
        - Whether year-over-year comparisons are possible
        - Available months for analysis
    """
    import pandas as pd

    logger.info("Getting data boundaries")

    try:
        # Check if data is loaded
        if _data_cache["energy_df"] is None:
            return """## Data Not Loaded

No energy data is currently loaded. Please use `load_energy_data()` first to load the data, then check boundaries.

**Quick load:** `load_energy_data()` will load the default dataset."""

        energy_df = _data_cache["energy_df"]
        energy_path = _data_cache.get("energy_path", "unknown")

        # Get date column
        date_col = 'local_15min' if 'local_15min' in energy_df.columns else energy_df.columns[0]

        # Parse dates
        dates = pd.to_datetime(energy_df[date_col])
        start_date = dates.min()
        end_date = dates.max()
        total_days = (end_date - start_date).days + 1

        # Calculate data coverage
        unique_dates = dates.dt.date.nunique()
        coverage_pct = (unique_dates / total_days) * 100 if total_days > 0 else 0

        # Check for year-over-year capability
        years_covered = dates.dt.year.unique().tolist()
        has_multi_year = len(years_covered) > 1

        # Get available months
        months_available = dates.dt.to_period('M').unique().tolist()
        months_str = [str(m) for m in sorted(months_available)]

        # Build response
        response = f"""## Data Boundaries

### Date Range
- **Start Date:** {start_date.strftime('%Y-%m-%d')}
- **End Date:** {end_date.strftime('%Y-%m-%d')}
- **Total Days:** {total_days} days
- **Data Coverage:** {coverage_pct:.1f}% ({unique_dates} days with data)

### Historical Comparison Capability
- **Years in Data:** {', '.join(map(str, sorted(years_covered)))}
- **Year-over-Year Comparison:** {'Possible' if has_multi_year else 'NOT possible (single year only)'}

### Available Months
{', '.join(months_str)}

### Data Source
`{energy_path}`
"""

        # Add important warnings
        if not has_multi_year:
            response += f"""
### Important Limitation
This dataset only contains data from **{years_covered[0]}**. You cannot compare to previous years (e.g., "same month last year") because that data does not exist.

**Available comparisons:**
- Month-to-month within {years_covered[0]}
- Week-to-week within the data range
- Day-to-day patterns

**NOT available:**
- Year-over-year comparisons
- Historical trends spanning multiple years
"""

        return response

    except Exception as e:
        logger.error(f"Error getting data boundaries: {str(e)}")
        return f"Error getting data boundaries: {str(e)}"


@tool
def list_available_data() -> str:
    """
    List all available energy data files and rate files.

    Returns:
        A list of available data files that can be loaded for analysis.
    """
    logger.info("Listing available data files")

    try:
        response = "## Available Data Files\n\n"

        # List energy data files
        energy_dir = os.path.join(DATA_DIR, "home_power")
        if os.path.exists(energy_dir):
            energy_files = [f for f in os.listdir(energy_dir)
                          if f.endswith('.csv') and not f.startswith('.')]
            response += "### Energy Data Files\n"
            if energy_files:
                for f in sorted(energy_files):
                    is_default = " **(default)**" if f in DEFAULT_ENERGY_FILE else ""
                    response += f"- `{DATA_DIR}/home_power/{f}`{is_default}\n"
            else:
                response += "- No energy data files found\n"
        else:
            response += "### Energy Data Files\n- Directory not found\n"

        response += "\n"

        # List rate data files
        rate_dir = os.path.join(DATA_DIR, "utility_rate")
        if os.path.exists(rate_dir):
            rate_files = [f for f in os.listdir(rate_dir)
                         if f.endswith('.csv') and not f.startswith('.')]
            response += "### Utility Rate Files\n"
            if rate_files:
                for f in sorted(rate_files):
                    is_default = " **(default)**" if f in DEFAULT_RATE_FILE else ""
                    response += f"- `{DATA_DIR}/utility_rate/{f}`{is_default}\n"
            else:
                response += "- No rate files found\n"
        else:
            response += "### Utility Rate Files\n- Directory not found\n"

        # Add usage hint
        response += "\n### Usage\n"
        response += "Use `load_energy_data()` to load the default data, or specify a file path.\n"

        return response

    except Exception as e:
        logger.error(f"Error listing data files: {str(e)}")
        return f"Error listing data files: {str(e)}"


@tool
def get_tracked_appliances() -> str:
    """
    Get the list of appliances being tracked in the energy data.

    This tool reads the default energy data file headers to show what appliances
    are available for analysis. Does not require loading the full dataset.

    Returns:
        A list of all appliances being tracked with their names.
    """
    import pandas as pd

    logger.info("Getting tracked appliances")

    try:
        # Check if data is already loaded
        if _data_cache["energy_df"] is not None:
            energy_df = _data_cache["energy_df"]
            source = _data_cache.get("energy_path", "loaded data")
        else:
            # Read just the headers from the default file
            if not os.path.exists(DEFAULT_ENERGY_FILE):
                return f"Error: Default energy file not found: {DEFAULT_ENERGY_FILE}"

            energy_df = pd.read_csv(DEFAULT_ENERGY_FILE, nrows=0)
            source = DEFAULT_ENERGY_FILE

        # Get appliance columns (exclude non-appliance columns)
        exclude_cols = {
            'local_15min', 'dataid', 'grid', 'solar', 'solar2',
            'leg1v', 'leg2v', 'Solar power generation 1', 'Solar power generation 2'
        }
        appliances = [col for col in energy_df.columns if col not in exclude_cols]

        # Format response
        response = f"## Tracked Appliances\n\n"
        response += f"**Data source:** `{source}`\n\n"
        response += f"**Total appliances:** {len(appliances)}\n\n"
        response += "### Appliance List\n"

        for i, appliance in enumerate(appliances, 1):
            response += f"{i}. {appliance}\n"

        response += "\n### Note\n"
        response += "To analyze these appliances, use `load_energy_data()` first, then `analyze_appliances()`.\n"

        return response

    except Exception as e:
        logger.error(f"Error getting appliances: {str(e)}")
        return f"Error getting appliances: {str(e)}"


@tool
def get_utility_rate(rate_type: Optional[str] = None) -> str:
    """
    Get information about the utility rate structure.

    This tool reads the utility rate files and displays the rate schedule,
    showing different rates for different times of day and seasons.

    Args:
        rate_type: Type of rate to display. Options are:
                  - "tou" or "time-of-use": Time-of-use rate with peak/off-peak pricing
                  - "flat": Flat rate (same price all day)
                  - None (default): Shows the default TOU rate

    Returns:
        Detailed information about the utility rate structure including
        rates by time period and season.
    """
    import pandas as pd

    logger.info(f"Getting utility rate information (type: {rate_type})")

    try:
        # Determine which rate file to use
        rate_dir = os.path.join(DATA_DIR, "utility_rate")

        if rate_type and rate_type.lower() in ["flat", "fixed"]:
            rate_file = os.path.join(rate_dir, "utility_rate_flat.csv")
            rate_name = "Flat Rate"
        else:
            rate_file = os.path.join(rate_dir, "utility_rate_sample.csv")
            rate_name = "Time-of-Use (TOU) Rate"

        if not os.path.exists(rate_file):
            return f"Error: Rate file not found: {rate_file}"

        # Load rate data
        df = pd.read_csv(rate_file)

        # Build response
        response = f"## {rate_name} Structure\n\n"
        response += f"**Source:** `{rate_file}`\n\n"

        # Group by season/month pattern
        if 'Month' in df.columns:
            # Determine seasons
            summer_months = ['May', 'June', 'July', 'August', 'September', 'October']
            winter_months = ['November', 'December', 'January', 'February', 'March', 'April']

            # Check if it's TOU (multiple time periods) or flat rate
            is_tou = len(df['Start Time'].unique()) > 1 if 'Start Time' in df.columns else False

            if is_tou:
                response += "### Rate Schedule\n\n"
                response += "This is a **Time-of-Use** rate where prices vary by time of day and season.\n\n"

                # Summer rates (peak season)
                summer_df = df[df['Month'].isin(summer_months)]
                if not summer_df.empty:
                    response += "#### Summer Season (May - October)\n"

                    # Find peak rates (highest rate)
                    rate_col = 'Rate (cents per kWh)'
                    if rate_col in summer_df.columns:
                        peak_rate = summer_df[rate_col].max()
                        off_peak_rate = summer_df[rate_col].min()

                        # Get time periods for each rate
                        peak_periods = summer_df[summer_df[rate_col] == peak_rate]
                        off_peak_periods = summer_df[summer_df[rate_col] == off_peak_rate]

                        response += f"- **Peak Rate:** {peak_rate:.2f} ¢/kWh\n"
                        if not peak_periods.empty:
                            times = peak_periods[['Start Time', 'End Time']].drop_duplicates()
                            for _, row in times.iterrows():
                                response += f"  - {row['Start Time']} - {row['End Time']}\n"

                        response += f"- **Off-Peak Rate:** {off_peak_rate:.2f} ¢/kWh\n"
                        if not off_peak_periods.empty:
                            times = off_peak_periods[['Start Time', 'End Time']].drop_duplicates()
                            for _, row in times.iterrows():
                                response += f"  - {row['Start Time']} - {row['End Time']}\n"

                    response += "\n"

                # Winter rates
                winter_df = df[df['Month'].isin(winter_months)]
                if not winter_df.empty:
                    response += "#### Winter Season (November - April)\n"

                    if rate_col in winter_df.columns:
                        peak_rate = winter_df[rate_col].max()
                        off_peak_rate = winter_df[rate_col].min()

                        peak_periods = winter_df[winter_df[rate_col] == peak_rate]
                        off_peak_periods = winter_df[winter_df[rate_col] == off_peak_rate]

                        response += f"- **Peak Rate:** {peak_rate:.2f} ¢/kWh\n"
                        if not peak_periods.empty:
                            times = peak_periods[['Start Time', 'End Time']].drop_duplicates()
                            for _, row in times.iterrows():
                                response += f"  - {row['Start Time']} - {row['End Time']}\n"

                        response += f"- **Off-Peak Rate:** {off_peak_rate:.2f} ¢/kWh\n"
                        if not off_peak_periods.empty:
                            times = off_peak_periods[['Start Time', 'End Time']].drop_duplicates()
                            for _, row in times.iterrows():
                                response += f"  - {row['Start Time']} - {row['End Time']}\n"

                    response += "\n"

            else:
                # Flat rate
                response += "### Rate Schedule\n\n"
                response += "This is a **Flat Rate** where the price is the same throughout the day.\n\n"

                rate_col = 'Rate (cents per kWh)'
                if rate_col in df.columns:
                    # Summer
                    summer_df = df[df['Month'].isin(summer_months)]
                    if not summer_df.empty:
                        summer_rate = summer_df[rate_col].iloc[0]
                        response += f"- **Summer (May - October):** {summer_rate:.2f} ¢/kWh\n"

                    # Winter
                    winter_df = df[df['Month'].isin(winter_months)]
                    if not winter_df.empty:
                        winter_rate = winter_df[rate_col].iloc[0]
                        response += f"- **Winter (November - April):** {winter_rate:.2f} ¢/kWh\n"

                response += "\n"

        # Add tips
        response += "### Energy Saving Tips\n"
        if is_tou if 'is_tou' in dir() else True:
            response += "- Shift high-power appliances (dishwasher, laundry, EV charging) to off-peak hours\n"
            response += "- Pre-cool/heat your home before peak hours\n"
            response += "- Use timers to automate appliance scheduling\n"
        else:
            response += "- Consider switching to a TOU rate if you can shift usage to off-peak hours\n"
            response += "- Reduce overall consumption to lower your bill\n"

        # Available rate files
        response += "\n### Available Rate Plans\n"
        if os.path.exists(rate_dir):
            rate_files = [f for f in os.listdir(rate_dir) if f.endswith('.csv')]
            for f in rate_files:
                response += f"- `{f}`\n"

        return response

    except Exception as e:
        logger.error(f"Error getting utility rate: {str(e)}")
        return f"Error getting utility rate: {str(e)}"


@tool
def load_energy_data(
    energy_file_path: Optional[str] = None,
    rate_file_path: Optional[str] = None,
    apply_standby_filter: bool = True,
    data_days: Optional[int] = None
) -> str:
    """
    Load energy consumption data from a CSV file.

    Args:
        energy_file_path: Path to the energy consumption CSV file. If not provided, uses the default file.
        rate_file_path: Path to utility rate CSV file. If not provided, uses the default TOU rate file.
        apply_standby_filter: Whether to filter out standby power using appliance thresholds (default True).
                             When True, readings below each appliance's threshold are treated as
                             standby/phantom load and set to zero for more accurate active usage analysis.
        data_days: Optional number of days of data to load from the start of the dataset.
                   If not provided, loads all available data.

    Returns:
        A summary of the loaded data including number of rows, columns, and date range.
    """
    import pandas as pd
    from core.data.data_validator import DataValidator
    from core.data.rate_handler import RateHandler

    # Use defaults if not provided
    energy_path = energy_file_path or DEFAULT_ENERGY_FILE
    rate_path = rate_file_path or DEFAULT_RATE_FILE

    # Determine thresholds file path based on energy file
    # Try to find a matching thresholds file (e.g., energy_data_sample.csv -> appliance_thresholds_sample.csv)
    thresholds_path = None
    if apply_standby_filter:
        thresholds_path = DEFAULT_THRESHOLDS_FILE
        # Also try to find a matching thresholds file for this specific data file
        if energy_path:
            import re
            match = re.search(r'(\d+)\.csv$', energy_path)
            if match:
                home_id = match.group(1)
                potential_path = os.path.join(DATA_DIR, "home_power", f"appliance_thresholds_{home_id}.csv")
                if os.path.exists(potential_path):
                    thresholds_path = potential_path

    logger.info(f"Loading energy data from {energy_path}")
    if thresholds_path:
        logger.info(f"Using thresholds file: {thresholds_path}")

    try:
        # Validate file exists
        if not os.path.exists(energy_path):
            return f"Error: File not found: {energy_path}"

        # Load and validate energy data (with optional threshold filtering)
        validator = DataValidator()
        energy_df = validator.load_and_validate(
            energy_path,
            thresholds_file=thresholds_path,
            apply_thresholds=apply_standby_filter
        )

        if energy_df is None or energy_df.empty:
            return f"Error: Failed to load or validate data from {energy_path}"

        # Filter to specified number of days from the start of the dataset
        # Use explicit parameter if provided, otherwise check eval config
        effective_data_days = data_days if data_days is not None else get_eval_data_days()
        if effective_data_days is not None:
            date_col = 'local_15min' if 'local_15min' in energy_df.columns else energy_df.columns[0]
            energy_df[date_col] = pd.to_datetime(energy_df[date_col])
            start_date = energy_df[date_col].min()
            end_date = start_date + pd.Timedelta(days=effective_data_days)
            energy_df = energy_df[energy_df[date_col] < end_date]
            logger.info(f"Filtered data to first {effective_data_days} days: {start_date} to {end_date}")

        # Store in cache
        _data_cache["energy_df"] = energy_df
        _data_cache["energy_path"] = energy_path

        # Detect solar presence from energy data columns
        solar_cols = {'solar', 'solar2', 'Solar power generation 1', 'Solar power generation 2'}
        has_solar = any(col in energy_df.columns for col in solar_cols)
        _data_cache["has_solar"] = has_solar
        logger.info(f"Solar detection: has_solar={has_solar}")

        # Load rate data (optional - continue if rate loading fails)
        rate_summary = ""
        rate_type = "tou"  # Default
        if rate_path and os.path.exists(rate_path):
            try:
                # Try to load with RateHandler first (expects specific columns)
                rate_handler = RateHandler()
                rate_df = rate_handler.load_rate_data(rate_path)
                _data_cache["rate_df"] = rate_df
                _data_cache["rate_path"] = rate_path
                rate_info = rate_handler.get_rate_summary(rate_df)
                rate_summary = f"\n- **Rate data:** {rate_info.get('total_rate_periods', 0)} rate periods from `{rate_path}`"
            except Exception as e:
                # Fall back to simple CSV load for alternative formats (like utility_rate_sample.csv)
                logger.warning(f"RateHandler failed: {e}. Trying simple CSV load.")
                try:
                    rate_df = pd.read_csv(rate_path)
                    _data_cache["rate_df"] = rate_df
                    _data_cache["rate_path"] = rate_path

                    # Detect rate type from CSV structure
                    if 'Start Time' in rate_df.columns:
                        unique_times = rate_df['Start Time'].nunique()
                        rate_type = "tou" if unique_times > 1 else "flat"
                    rate_summary = f"\n- **Rate data:** Loaded from `{rate_path}` ({rate_type.upper()} rate)"
                except Exception as e2:
                    logger.warning(f"Could not load rate data: {e2}. Continuing without rate data.")
                    rate_summary = "\n- **Rate data:** Not loaded (rate analysis will use defaults)"

        _data_cache["rate_type"] = rate_type
        logger.info(f"Rate type detection: rate_type={rate_type}")

        # Threshold info
        threshold_summary = ""
        if apply_standby_filter and thresholds_path:
            threshold_summary = f"\n- **Standby filter:** Applied using `{thresholds_path}`"
        elif not apply_standby_filter:
            threshold_summary = "\n- **Standby filter:** Disabled (raw readings used)"

        # Get data summary
        date_col = 'local_15min' if 'local_15min' in energy_df.columns else energy_df.columns[0]
        if date_col in energy_df.columns:
            date_range = f"{energy_df[date_col].min()} to {energy_df[date_col].max()}"
        else:
            date_range = "Unknown"

        # Get appliance columns
        exclude_cols = {
            'local_15min', 'dataid', 'grid', 'solar', 'solar2',
            'leg1v', 'leg2v', 'Solar power generation 1', 'Solar power generation 2'
        }
        appliance_cols = [col for col in energy_df.columns if col not in exclude_cols]

        # Build household configuration summary
        config_summary = f"\n- **Rate type:** {rate_type.upper()}"
        config_summary += f"\n- **Solar PV:** {'Yes' if has_solar else 'No'}"

        summary = f"""## Energy Data Loaded Successfully

### Data Summary
- **File:** `{energy_path}`
- **Rows:** {len(energy_df):,}
- **Date range:** {date_range}
- **Appliances detected:** {len(appliance_cols)}{rate_summary}{threshold_summary}{config_summary}

### Appliances
{', '.join(appliance_cols)}

### Next Steps
Data is ready for analysis. You can now use:
- `analyze_consumption()` - Overall consumption patterns
- `analyze_appliances()` - Appliance-level breakdown
- `analyze_utility_rate()` - Rate structure analysis (adapts to {rate_type.upper()} rate)"""

        # Add solar-specific suggestion if solar is present
        if has_solar:
            summary += "\n- `analyze_solar_availability()` - Solar generation patterns"

        logger.info(f"Data loaded: {len(energy_df)} rows, {len(appliance_cols)} appliances")

        # Extract and cache household profile for case study comparisons
        try:
            from evaluation.data.household_metrics import extract_household_profile
            profile = extract_household_profile(
                energy_df=energy_df,
                data_file=energy_path,
                rate_df=_data_cache.get("rate_df"),
            )
            _data_cache["household_profile"] = profile
            logger.info(f"Household profile extracted: {profile.household_id}")
        except Exception as e:
            logger.warning(f"Could not extract household profile: {e}")
            _data_cache["household_profile"] = None

        # Extract and cache simulated time (last timestamp from energy data)
        # This is used for device control operations to ensure TOU calculations
        # are consistent with the energy data time period
        try:
            date_col = 'local_15min' if 'local_15min' in energy_df.columns else energy_df.columns[0]
            last_timestamp = pd.to_datetime(energy_df[date_col].iloc[-1])
            # Remove timezone info for compatibility (convert to naive datetime)
            if last_timestamp.tzinfo is not None:
                last_timestamp = last_timestamp.tz_localize(None)
            set_simulated_time(last_timestamp)
            logger.info(f"Simulated time set to: {last_timestamp}")
        except Exception as e:
            logger.warning(f"Could not set simulated time: {e}")
            set_simulated_time(None)

        return summary

    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        return f"Error loading data: {str(e)}"
