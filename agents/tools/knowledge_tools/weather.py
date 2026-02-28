# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/tools/knowledge_tools/weather.py
"""Weather tools for energy-aware weather information.

Note: When simulated time is set (from energy data), weather tools automatically
fetch HISTORICAL weather for that time period instead of current weather.
This ensures consistency between energy data and weather data during evaluation.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from langchain_core.tools import tool

from config.config import DEFAULT_LOCATION, WEATHER_CACHE_TTL
from core.weather import WeatherClient
from agents.tools.analysis_tools.cache import get_simulated_time
from utils.logger import setup_logger

logger = setup_logger()

# Shared weather client instance
_weather_client: Optional[WeatherClient] = None

# Typical temperature ranges by month for US locations (broad sanity checks)
# Format: month -> (min_reasonable_f, max_reasonable_f)
# These are very broad ranges to catch only extreme outliers
TYPICAL_TEMP_RANGES = {
    1: (0, 80),    # January
    2: (0, 85),    # February
    3: (15, 90),   # March
    4: (25, 100),  # April
    5: (35, 105),  # May
    6: (45, 115),  # June
    7: (50, 120),  # July
    8: (50, 120),  # August
    9: (40, 115),  # September
    10: (25, 100), # October
    11: (10, 90),  # November
    12: (0, 80),   # December
}

# Hot-climate cities where snow in summer would be extremely unusual
HOT_CLIMATE_KEYWORDS = [
    "austin", "phoenix", "tucson", "houston", "san antonio", "dallas",
    "miami", "tampa", "las vegas", "los angeles", "san diego"
]

# WMO snow-related weather codes
SNOW_CODES = [71, 73, 75, 77, 85, 86]


def _get_reference_time() -> datetime:
    """Get the reference time for weather operations.

    Uses simulated time if set (from energy data), otherwise current time.
    This ensures weather data matches the time period of energy data during evaluation.
    """
    simulated = get_simulated_time()
    if simulated is not None:
        return simulated
    return datetime.now()


def _is_using_simulated_time() -> bool:
    """Check if we're using simulated time (evaluation mode)."""
    return get_simulated_time() is not None


def _validate_weather_data(weather: Dict[str, Any], location: str) -> List[str]:
    """
    Validate weather data for plausibility and return warnings.

    Args:
        weather: Weather data dictionary from API
        location: Location string

    Returns:
        List of warning messages (empty if data looks reasonable)
    """
    warnings = []
    location_lower = location.lower()

    # Use reference time (simulated or current) for month-based validation
    reference_time = _get_reference_time()
    reference_month = reference_time.month

    # Check temperature reasonableness
    temp_f = weather.get("temperature_f") or weather.get("high_f")
    if temp_f is not None:
        min_reasonable, max_reasonable = TYPICAL_TEMP_RANGES.get(reference_month, (-20, 130))
        if temp_f < min_reasonable - 20 or temp_f > max_reasonable + 10:
            warnings.append(
                f"Temperature ({temp_f:.0f}°F) seems unusual for this time of year. "
                "Verify this data before making decisions."
            )

    # Check for snow in hot climates during summer months
    weather_code = weather.get("weather_code", 0)
    is_hot_climate = any(city in location_lower for city in HOT_CLIMATE_KEYWORDS)
    is_summer = reference_month in [5, 6, 7, 8, 9]

    if is_hot_climate and is_summer and weather_code in SNOW_CODES:
        warnings.append(
            f"Snow indicated for {location} in summer - this is extremely unlikely. "
            "Weather data may be incorrect."
        )

    return warnings


def _add_validation_warnings(response: str, warnings: List[str]) -> str:
    """Add validation warnings to the response if any exist."""
    if not warnings:
        return response

    warning_section = "\n\n**Data Quality Note:**\n"
    for w in warnings:
        warning_section += f"- {w}\n"

    return response + warning_section


def _get_weather_client() -> WeatherClient:
    """Get or create the shared weather client instance."""
    global _weather_client
    if _weather_client is None:
        _weather_client = WeatherClient(cache_ttl=WEATHER_CACHE_TTL)
    return _weather_client


@tool
def get_current_weather(location: Optional[str] = None) -> str:
    """
    Get current weather conditions for a location.

    Use this tool to answer questions about current weather, temperature,
    or conditions. Helpful for understanding current energy demands
    (e.g., AC/heating needs).

    Note: When analyzing historical energy data, this tool automatically
    returns weather for the corresponding time period (not today's weather).

    Args:
        location: City and state/country (e.g., "Tucson, AZ", "Phoenix, Arizona").
                 If not provided, uses the default configured location.

    Returns:
        Current weather conditions including temperature, humidity,
        wind speed, and conditions.
    """
    location = location or DEFAULT_LOCATION
    reference_time = _get_reference_time()

    # Check if we're in simulation mode (historical energy data)
    if _is_using_simulated_time():
        # Fetch historical weather for the simulated date
        date_str = reference_time.strftime("%Y-%m-%d")
        logger.info(f"Getting historical weather for simulated date {date_str}: {location}")

        try:
            client = _get_weather_client()
            # Get historical weather for that specific day
            data = client.get_historical_weather(location, date_str, date_str)

            if data['days']:
                day = data['days'][0]
                high = day['high_f']
                low = day['low_f']
                avg = day.get('avg_f', (high + low) / 2 if high and low else None)
                condition = day['weather_description']

                # Validate for plausibility
                warnings = _validate_weather_data(day, location)

                response = f"""## Weather for {data['location']} on {date_str}

**High:** {high:.0f}°F | **Low:** {low:.0f}°F
**Average:** {avg:.0f}°F
**Conditions:** {condition}

*Note: This is historical weather data matching the energy data period.*
"""
                return _add_validation_warnings(response, warnings)
            else:
                return f"No weather data available for {date_str}"

        except Exception as e:
            logger.error(f"Historical weather error: {e}")
            return f"Error getting weather data for {date_str}: {e}"

    # Normal mode: fetch current weather
    logger.info(f"Getting current weather for: {location}")

    try:
        client = _get_weather_client()
        weather = client.get_current_weather(location)

        # Validate weather data for plausibility
        warnings = _validate_weather_data(weather, location)

        response = f"""## Current Weather for {weather['location']}

**Temperature:** {weather['temperature_f']:.0f}°F ({weather['temperature_c']:.1f}°C)
**Feels Like:** {weather['feels_like_f']:.0f}°F
**Conditions:** {weather['weather_description']}
**Humidity:** {weather['humidity']}%
**Wind:** {weather['wind_speed_mph']:.0f} mph
**Cloud Cover:** {weather['cloud_cover']}%
"""
        return _add_validation_warnings(response, warnings)

    except ValueError as e:
        logger.error(f"Weather error: {e}")
        return f"Error getting weather data: {e}"
    except Exception as e:
        logger.error(f"Unexpected weather error: {e}")
        return f"Error: Could not retrieve weather information. {e}"


@tool
def get_weather_forecast(location: Optional[str] = None, days: int = 3) -> str:
    """
    Get weather forecast for upcoming days.

    Use this tool for questions about future weather, upcoming temperature
    changes, or planning energy usage around expected conditions.

    Note: When analyzing historical energy data, this returns the actual
    weather that occurred during that period (not a future forecast).

    Args:
        location: City and state/country (e.g., "Tucson, AZ").
                 If not provided, uses the default configured location.
        days: Number of days to forecast (1-7, default 3).

    Returns:
        Weather forecast with daily high/low temperatures, conditions,
        and precipitation probability.
    """
    location = location or DEFAULT_LOCATION
    days = min(max(days, 1), 7)  # Clamp to 1-7 for reasonable output
    reference_time = _get_reference_time()

    # Check if we're in simulation mode (historical energy data)
    if _is_using_simulated_time():
        # Fetch historical weather for the simulated period
        start_date = reference_time.strftime("%Y-%m-%d")
        end_date = (reference_time + timedelta(days=days-1)).strftime("%Y-%m-%d")
        logger.info(f"Getting historical weather for simulated period {start_date} to {end_date}: {location}")

        try:
            client = _get_weather_client()
            data = client.get_historical_weather(location, start_date, end_date)

            # Validate each day's data for plausibility
            all_warnings = []
            for day in data['days']:
                day_warnings = _validate_weather_data(day, location)
                all_warnings.extend(day_warnings)

            response = f"## {days}-Day Weather for {data['location']}\n"
            response += f"*Period: {start_date} to {end_date} (historical data matching energy data)*\n\n"

            for day in data['days']:
                date = day['date']
                high = day['high_f']
                low = day['low_f']
                condition = day['weather_description']
                precip = day.get('precipitation_sum', 0)

                response += f"### {date}\n"
                response += f"- **High:** {high:.0f}°F | **Low:** {low:.0f}°F\n"
                response += f"- **Conditions:** {condition}\n"
                if precip and precip > 0:
                    response += f"- **Precipitation:** {precip:.2f} inches\n"
                response += "\n"

            # Add warnings (deduplicated)
            unique_warnings = list(set(all_warnings))
            return _add_validation_warnings(response, unique_warnings)

        except Exception as e:
            logger.error(f"Historical forecast error: {e}")
            return f"Error getting weather data for {start_date} to {end_date}: {e}"

    # Normal mode: fetch current forecast
    logger.info(f"Getting {days}-day forecast for: {location}")

    try:
        client = _get_weather_client()
        forecast = client.get_forecast(location, days=days)

        # Validate each day's forecast for plausibility
        all_warnings = []
        for day in forecast['days']:
            day_warnings = _validate_weather_data(day, location)
            all_warnings.extend(day_warnings)

        response = f"## {days}-Day Weather Forecast for {forecast['location']}\n\n"

        for day in forecast['days']:
            date = day['date']
            high = day['high_f']
            low = day['low_f']
            condition = day['weather_description']
            precip = day['precipitation_prob']

            response += f"### {date}\n"
            response += f"- **High:** {high:.0f}°F | **Low:** {low:.0f}°F\n"
            response += f"- **Conditions:** {condition}\n"
            if precip > 0:
                response += f"- **Precipitation chance:** {precip}%\n"
            response += "\n"

        # Add warnings (deduplicated)
        unique_warnings = list(set(all_warnings))
        return _add_validation_warnings(response, unique_warnings)

    except ValueError as e:
        logger.error(f"Forecast error: {e}")
        return f"Error getting forecast data: {e}"
    except Exception as e:
        logger.error(f"Unexpected forecast error: {e}")
        return f"Error: Could not retrieve forecast information. {e}"


@tool
def get_weather_energy_impact(location: Optional[str] = None) -> str:
    """
    Analyze how current and forecasted weather affects energy usage.

    Use this tool for questions about:
    - How weather impacts energy bills
    - Whether to run AC/heating now or wait
    - Solar production expectations
    - Energy planning based on weather

    Note: When analyzing historical energy data, this returns the actual
    weather conditions during that period with energy impact analysis.

    Args:
        location: City and state/country (e.g., "Tucson, AZ").
                 If not provided, uses the default configured location.

    Returns:
        Energy impact analysis including cooling/heating demand levels,
        solar potential, and specific recommendations.
    """
    location = location or DEFAULT_LOCATION
    reference_time = _get_reference_time()

    # Check if we're in simulation mode (historical energy data)
    if _is_using_simulated_time():
        # Fetch historical weather for the simulated period
        start_date = reference_time.strftime("%Y-%m-%d")
        end_date = (reference_time + timedelta(days=2)).strftime("%Y-%m-%d")
        logger.info(f"Getting historical weather energy impact for {start_date} to {end_date}: {location}")

        try:
            client = _get_weather_client()
            data = client.get_historical_weather(location, start_date, end_date)

            if not data['days']:
                return f"No weather data available for {start_date}"

            # Use first day as "current"
            current_day = data['days'][0]
            high = current_day['high_f']
            low = current_day['low_f']
            avg = current_day.get('avg_f', (high + low) / 2 if high and low else 70)

            # Calculate energy demand levels based on historical temps
            if avg >= 95:
                cooling_demand = "extreme"
            elif avg >= 85:
                cooling_demand = "high"
            elif avg >= 75:
                cooling_demand = "moderate"
            else:
                cooling_demand = "low"

            if avg <= 32:
                heating_demand = "extreme"
            elif avg <= 45:
                heating_demand = "high"
            elif avg <= 55:
                heating_demand = "moderate"
            else:
                heating_demand = "low"

            # Solar potential based on weather description
            condition_lower = current_day['weather_description'].lower()
            if 'clear' in condition_lower or 'sunny' in condition_lower:
                solar_potential = "excellent"
            elif 'partly' in condition_lower:
                solar_potential = "good"
            elif 'cloud' in condition_lower or 'overcast' in condition_lower:
                solar_potential = "moderate"
            else:
                solar_potential = "poor"

            # Validate data
            warnings = _validate_weather_data(current_day, location)

            response = f"""## Weather Energy Impact Analysis for {data['location']}
*Based on historical weather data for {start_date}*

### Conditions on {start_date}
- **High:** {high:.0f}°F | **Low:** {low:.0f}°F | **Average:** {avg:.0f}°F
- **Conditions:** {current_day['weather_description']}

### Energy Demand Levels
- **Cooling Demand:** {cooling_demand.upper()}
- **Heating Demand:** {heating_demand.upper()}
- **Solar Potential:** {solar_potential.upper()}

### 3-Day Weather
"""
            for day in data['days'][:3]:
                response += f"- **{day['date']}:** {day['weather_description']}, High {day['high_f']:.0f}°F / Low {day['low_f']:.0f}°F\n"

            # Generate recommendations based on actual conditions
            recommendations = []
            if cooling_demand in ["high", "extreme"]:
                recommendations.append(
                    f"High cooling demand (avg {avg:.0f}°F). "
                    "Pre-cool home during off-peak hours to save on TOU rates."
                )
            if heating_demand in ["high", "extreme"]:
                recommendations.append(
                    f"High heating demand (avg {avg:.0f}°F). "
                    "Lower thermostat when away to reduce costs."
                )
            if solar_potential in ["excellent", "good"]:
                recommendations.append(
                    f"Good solar conditions ({current_day['weather_description']}). "
                    "Run high-energy appliances during midday for solar alignment."
                )

            if recommendations:
                response += "\n### Energy Recommendations\n"
                for rec in recommendations:
                    response += f"- {rec}\n"

            return _add_validation_warnings(response, warnings)

        except Exception as e:
            logger.error(f"Historical energy impact error: {e}")
            return f"Error analyzing weather impact for {start_date}: {e}"

    # Normal mode: use current weather
    logger.info(f"Analyzing weather energy impact for: {location}")

    try:
        client = _get_weather_client()
        analysis = client.get_weather_for_energy_analysis(location)

        current = analysis['current']

        # Validate current weather data
        warnings = _validate_weather_data(current, location)

        # Also validate forecast summary
        for day_summary in analysis.get('forecast_summary', []):
            day_warnings = _validate_weather_data(
                {'high_f': day_summary.get('high'), 'weather_code': 0},
                location
            )
            warnings.extend(day_warnings)

        response = f"""## Weather Energy Impact Analysis for {current['location']}

### Current Conditions
- **Temperature:** {current['temperature_f']:.0f}°F (feels like {current['feels_like_f']:.0f}°F)
- **Conditions:** {current['weather_description']}
- **Humidity:** {current['humidity']}%
- **Cloud Cover:** {current['cloud_cover']}%

### Energy Demand Levels
- **Cooling Demand:** {analysis['cooling_demand'].upper()}
- **Heating Demand:** {analysis['heating_demand'].upper()}
- **Solar Potential:** {analysis['solar_potential'].upper()}

### 3-Day Outlook
"""
        for day in analysis['forecast_summary']:
            response += f"- **{day['date']}:** {day['condition']}, High {day['high']:.0f}°F / Low {day['low']:.0f}°F\n"

        if analysis['recommendations']:
            response += "\n### Energy Recommendations\n"
            for rec in analysis['recommendations']:
                response += f"- {rec}\n"

        # Add deduplicated warnings
        unique_warnings = list(set(warnings))
        return _add_validation_warnings(response, unique_warnings)

    except ValueError as e:
        logger.error(f"Energy impact analysis error: {e}")
        return f"Error analyzing weather impact: {e}"
    except Exception as e:
        logger.error(f"Unexpected analysis error: {e}")
        return f"Error: Could not analyze weather energy impact. {e}"


@tool
def get_historical_weather(
    start_date: str,
    end_date: str,
    location: Optional[str] = None,
) -> str:
    """
    Get historical weather data for a past date range.

    Use this tool to correlate energy usage with weather conditions during
    the same time period. Essential for understanding why energy usage was
    high or low on specific days.

    Use cases:
    - "What was the weather like during my highest energy usage days?"
    - "How hot was it last week when my AC was running so much?"
    - "Get weather data for July 2023 to compare with my energy bills"
    - "Were there any heat waves during the summer that explain my high usage?"

    Args:
        start_date: Start date in YYYY-MM-DD format (e.g., "2023-07-01")
        end_date: End date in YYYY-MM-DD format (e.g., "2023-07-31")
        location: City and state/country (e.g., "Austin, TX").
                 If not provided, uses the default configured location.

    Returns:
        Historical weather data including daily temperatures, conditions,
        and summary statistics for the period.
    """
    location = location or DEFAULT_LOCATION
    logger.info(f"Getting historical weather for {location} from {start_date} to {end_date}")

    try:
        client = _get_weather_client()
        data = client.get_historical_weather(location, start_date, end_date)

        summary = data['summary']
        days = data['days']

        response = f"""## Historical Weather for {data['location']}
**Period:** {data['start_date']} to {data['end_date']} ({summary['num_days']} days)

### Summary Statistics
- **Average High:** {summary['avg_high_f']}°F
- **Average Low:** {summary['avg_low_f']}°F
- **Total Precipitation:** {summary['total_precipitation_in']} inches
- **Hot Days (≥90°F):** {summary['hot_days_90f_plus']}
- **Cold Days (≤32°F):** {summary['cold_days_32f_minus']}

### Daily Details
"""
        # Show up to 14 days of detail, summarize if more
        display_days = days[:14] if len(days) > 14 else days

        for day in display_days:
            high = day['high_f']
            low = day['low_f']
            condition = day['weather_description']
            precip = day['precipitation_sum']

            response += f"- **{day['date']}:** {condition}, "
            response += f"High {high:.0f}°F / Low {low:.0f}°F"
            if precip and precip > 0:
                response += f", {precip:.2f}\" rain"
            response += "\n"

        if len(days) > 14:
            response += f"\n*({len(days) - 14} more days not shown)*\n"

        return response

    except ValueError as e:
        logger.error(f"Historical weather error: {e}")
        return f"Error getting historical weather data: {e}"
    except Exception as e:
        logger.error(f"Unexpected historical weather error: {e}")
        return f"Error: Could not retrieve historical weather information. {e}"
