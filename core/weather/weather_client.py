# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# core/weather/weather_client.py
"""Weather client for Open-Meteo API."""
import time
from typing import Dict, Any, Optional, Tuple
import requests

from utils.logger import setup_logger

logger = setup_logger()

# WMO Weather interpretation codes
# https://open-meteo.com/en/docs
WMO_CODES = {
    0: ("Clear sky", "sunny"),
    1: ("Mainly clear", "mostly_sunny"),
    2: ("Partly cloudy", "partly_cloudy"),
    3: ("Overcast", "cloudy"),
    45: ("Fog", "fog"),
    48: ("Depositing rime fog", "fog"),
    51: ("Light drizzle", "drizzle"),
    53: ("Moderate drizzle", "drizzle"),
    55: ("Dense drizzle", "drizzle"),
    56: ("Light freezing drizzle", "freezing_drizzle"),
    57: ("Dense freezing drizzle", "freezing_drizzle"),
    61: ("Slight rain", "rain"),
    63: ("Moderate rain", "rain"),
    65: ("Heavy rain", "heavy_rain"),
    66: ("Light freezing rain", "freezing_rain"),
    67: ("Heavy freezing rain", "freezing_rain"),
    71: ("Slight snow fall", "snow"),
    73: ("Moderate snow fall", "snow"),
    75: ("Heavy snow fall", "heavy_snow"),
    77: ("Snow grains", "snow"),
    80: ("Slight rain showers", "showers"),
    81: ("Moderate rain showers", "showers"),
    82: ("Violent rain showers", "heavy_showers"),
    85: ("Slight snow showers", "snow_showers"),
    86: ("Heavy snow showers", "snow_showers"),
    95: ("Thunderstorm", "thunderstorm"),
    96: ("Thunderstorm with slight hail", "thunderstorm"),
    99: ("Thunderstorm with heavy hail", "thunderstorm"),
}


class WeatherClient:
    """Client for Open-Meteo weather API with caching."""

    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
    GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

    def __init__(self, cache_ttl: int = 600):
        """
        Initialize the weather client.

        Args:
            cache_ttl: Cache time-to-live in seconds (default 10 minutes)
        """
        self.cache: Dict[str, Tuple[float, Any]] = {}
        self.cache_ttl = cache_ttl
        self.coord_cache: Dict[str, Tuple[float, float]] = {}

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached value if still valid."""
        if key in self.cache:
            timestamp, value = self.cache[key]
            if time.time() - timestamp < self.cache_ttl:
                logger.debug(f"Cache hit for: {key}")
                return value
            else:
                del self.cache[key]
        return None

    def _set_cached(self, key: str, value: Any) -> None:
        """Store value in cache."""
        self.cache[key] = (time.time(), value)

    def geocode(self, location: str) -> Tuple[float, float]:
        """
        Convert location name to coordinates.

        Args:
            location: City name or address (e.g., "Tucson, AZ")

        Returns:
            Tuple of (latitude, longitude)

        Raises:
            ValueError: If location cannot be geocoded
        """
        # Check coordinate cache (no TTL - coordinates don't change)
        if location in self.coord_cache:
            return self.coord_cache[location]

        logger.info(f"Geocoding location: {location}")

        try:
            # Extract city name (Open-Meteo works best with just city name)
            # Handle formats like "Tucson, AZ" or "Phoenix, Arizona"
            search_name = location.split(",")[0].strip()

            response = requests.get(
                self.GEOCODING_URL,
                params={"name": search_name, "count": 5, "language": "en", "format": "json"},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("results"):
                raise ValueError(f"Could not find location: {location}")

            # If state/country provided, try to match it
            result = data["results"][0]  # Default to first result
            if "," in location:
                region = location.split(",")[1].strip().lower()
                # Try to find a result matching the region
                for r in data["results"]:
                    admin1 = r.get("admin1", "").lower()
                    country = r.get("country", "").lower()
                    country_code = r.get("country_code", "").lower()
                    # Match state abbreviation, full state name, or country
                    if region in [admin1, country, country_code]:
                        result = r
                        break
                    # Handle US state abbreviations
                    if country_code == "us" and len(region) == 2:
                        # Check if admin1 starts with similar letters
                        if admin1.startswith(region[0]):
                            result = r
                            break

            lat = result["latitude"]
            lon = result["longitude"]

            # Cache the coordinates
            self.coord_cache[location] = (lat, lon)

            logger.info(f"Geocoded '{location}' to ({lat}, {lon})")
            return lat, lon

        except requests.RequestException as e:
            logger.error(f"Geocoding request failed: {e}")
            raise ValueError(f"Failed to geocode location: {e}")

    def get_current_weather(self, location: str) -> Dict[str, Any]:
        """
        Get current weather conditions.

        Args:
            location: City name or address

        Returns:
            Dictionary with current weather data:
            - temperature_f: Temperature in Fahrenheit
            - temperature_c: Temperature in Celsius
            - humidity: Relative humidity percentage
            - wind_speed_mph: Wind speed in mph
            - cloud_cover: Cloud cover percentage
            - weather_code: WMO weather code
            - weather_description: Human-readable weather description
            - weather_category: Simplified category (sunny, cloudy, rain, etc.)
            - location: Location name used
        """
        cache_key = f"current:{location}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        lat, lon = self.geocode(location)

        logger.info(f"Fetching current weather for {location}")

        try:
            response = requests.get(
                self.BASE_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": [
                        "temperature_2m",
                        "relative_humidity_2m",
                        "weather_code",
                        "wind_speed_10m",
                        "cloud_cover",
                        "apparent_temperature",
                    ],
                    "temperature_unit": "fahrenheit",
                    "wind_speed_unit": "mph",
                    "timezone": "auto",
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            current = data.get("current", {})
            weather_code = current.get("weather_code", 0)
            description, category = WMO_CODES.get(weather_code, ("Unknown", "unknown"))

            result = {
                "temperature_f": current.get("temperature_2m"),
                "temperature_c": round((current.get("temperature_2m", 32) - 32) * 5 / 9, 1),
                "feels_like_f": current.get("apparent_temperature"),
                "humidity": current.get("relative_humidity_2m"),
                "wind_speed_mph": current.get("wind_speed_10m"),
                "cloud_cover": current.get("cloud_cover"),
                "weather_code": weather_code,
                "weather_description": description,
                "weather_category": category,
                "location": location,
                "timestamp": current.get("time"),
            }

            self._set_cached(cache_key, result)
            return result

        except requests.RequestException as e:
            logger.error(f"Weather request failed: {e}")
            raise ValueError(f"Failed to fetch weather: {e}")

    def get_forecast(self, location: str, days: int = 7) -> Dict[str, Any]:
        """
        Get multi-day weather forecast.

        Args:
            location: City name or address
            days: Number of days to forecast (1-16)

        Returns:
            Dictionary with forecast data:
            - location: Location name used
            - days: List of daily forecasts with:
                - date: Date string (YYYY-MM-DD)
                - high_f: High temperature in Fahrenheit
                - low_f: Low temperature in Fahrenheit
                - weather_code: WMO weather code
                - weather_description: Human-readable description
                - precipitation_prob: Precipitation probability percentage
                - precipitation_sum: Total precipitation in inches
        """
        days = min(max(days, 1), 16)  # Clamp to 1-16

        cache_key = f"forecast:{location}:{days}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        lat, lon = self.geocode(location)

        logger.info(f"Fetching {days}-day forecast for {location}")

        try:
            response = requests.get(
                self.BASE_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "daily": [
                        "temperature_2m_max",
                        "temperature_2m_min",
                        "weather_code",
                        "precipitation_probability_max",
                        "precipitation_sum",
                        "sunrise",
                        "sunset",
                    ],
                    "temperature_unit": "fahrenheit",
                    "precipitation_unit": "inch",
                    "timezone": "auto",
                    "forecast_days": days,
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            daily = data.get("daily", {})
            dates = daily.get("time", [])
            highs = daily.get("temperature_2m_max", [])
            lows = daily.get("temperature_2m_min", [])
            codes = daily.get("weather_code", [])
            precip_probs = daily.get("precipitation_probability_max", [])
            precip_sums = daily.get("precipitation_sum", [])

            forecast_days = []
            for i in range(len(dates)):
                code = codes[i] if i < len(codes) else 0
                description, category = WMO_CODES.get(code, ("Unknown", "unknown"))

                forecast_days.append({
                    "date": dates[i],
                    "high_f": highs[i] if i < len(highs) else None,
                    "low_f": lows[i] if i < len(lows) else None,
                    "weather_code": code,
                    "weather_description": description,
                    "weather_category": category,
                    "precipitation_prob": precip_probs[i] if i < len(precip_probs) else 0,
                    "precipitation_sum": precip_sums[i] if i < len(precip_sums) else 0,
                })

            result = {
                "location": location,
                "days": forecast_days,
            }

            self._set_cached(cache_key, result)
            return result

        except requests.RequestException as e:
            logger.error(f"Forecast request failed: {e}")
            raise ValueError(f"Failed to fetch forecast: {e}")

    def get_weather_for_energy_analysis(self, location: str) -> Dict[str, Any]:
        """
        Get weather data specifically formatted for energy impact analysis.

        Args:
            location: City name or address

        Returns:
            Dictionary with energy-relevant weather analysis:
            - current: Current conditions
            - forecast_summary: Summary of upcoming conditions
            - cooling_demand: Estimated cooling demand level (low/moderate/high/extreme)
            - heating_demand: Estimated heating demand level
            - solar_potential: Estimated solar production potential
            - recommendations: List of energy recommendations
        """
        current = self.get_current_weather(location)
        forecast = self.get_forecast(location, days=3)

        temp_f = current.get("temperature_f", 70)
        humidity = current.get("humidity", 50)
        cloud_cover = current.get("cloud_cover", 50)
        category = current.get("weather_category", "unknown")

        # Determine cooling demand
        if temp_f >= 95:
            cooling_demand = "extreme"
        elif temp_f >= 85:
            cooling_demand = "high"
        elif temp_f >= 75:
            cooling_demand = "moderate"
        else:
            cooling_demand = "low"

        # Determine heating demand
        if temp_f <= 32:
            heating_demand = "extreme"
        elif temp_f <= 45:
            heating_demand = "high"
        elif temp_f <= 55:
            heating_demand = "moderate"
        else:
            heating_demand = "low"

        # Determine solar potential
        if cloud_cover <= 20 and category in ["sunny", "mostly_sunny"]:
            solar_potential = "excellent"
        elif cloud_cover <= 50:
            solar_potential = "good"
        elif cloud_cover <= 80:
            solar_potential = "moderate"
        else:
            solar_potential = "poor"

        # Generate recommendations
        recommendations = []

        if cooling_demand in ["high", "extreme"]:
            recommendations.append(
                f"High cooling demand expected ({temp_f}°F). "
                "Consider pre-cooling home during off-peak hours."
            )
            if humidity > 60:
                recommendations.append(
                    "High humidity detected. AC will work harder - ensure filters are clean."
                )

        if heating_demand in ["high", "extreme"]:
            recommendations.append(
                f"Cold temperatures ({temp_f}°F) will increase heating costs. "
                "Consider lowering thermostat when away."
            )

        if solar_potential in ["excellent", "good"]:
            recommendations.append(
                f"Good solar conditions ({100-cloud_cover}% clear). "
                "Ideal day for solar energy production."
            )
        elif solar_potential == "poor":
            recommendations.append(
                f"Cloudy conditions ({cloud_cover}% cloud cover) will reduce solar production."
            )

        # Check forecast for upcoming changes
        if forecast.get("days") and len(forecast["days"]) >= 2:
            tomorrow = forecast["days"][1]
            temp_change = (tomorrow.get("high_f", temp_f) - temp_f)
            if abs(temp_change) >= 10:
                direction = "warmer" if temp_change > 0 else "cooler"
                recommendations.append(
                    f"Temperature changing significantly tomorrow "
                    f"({direction} by {abs(temp_change):.0f}°F). Plan accordingly."
                )

        # Summarize forecast
        forecast_summary = []
        for day in forecast.get("days", [])[:3]:
            forecast_summary.append({
                "date": day.get("date"),
                "high": day.get("high_f"),
                "low": day.get("low_f"),
                "condition": day.get("weather_description"),
            })

        return {
            "current": current,
            "forecast_summary": forecast_summary,
            "cooling_demand": cooling_demand,
            "heating_demand": heating_demand,
            "solar_potential": solar_potential,
            "recommendations": recommendations,
        }

    def get_historical_weather(
        self,
        location: str,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """
        Get historical weather data for a date range.

        Uses Open-Meteo Archive API which provides historical data from 1940 to present.

        Args:
            location: City name or address (e.g., "Austin, TX")
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            Dictionary with historical weather data:
            - location: Location name used
            - start_date: Start date of data
            - end_date: End date of data
            - days: List of daily weather records with:
                - date: Date string (YYYY-MM-DD)
                - high_f: High temperature in Fahrenheit
                - low_f: Low temperature in Fahrenheit
                - avg_f: Average temperature in Fahrenheit
                - weather_code: WMO weather code
                - weather_description: Human-readable description
                - precipitation_sum: Total precipitation in inches
                - wind_speed_max_mph: Maximum wind speed in mph
            - summary: Aggregated statistics for the period
        """
        cache_key = f"historical:{location}:{start_date}:{end_date}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        lat, lon = self.geocode(location)

        logger.info(f"Fetching historical weather for {location} from {start_date} to {end_date}")

        try:
            response = requests.get(
                self.ARCHIVE_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "start_date": start_date,
                    "end_date": end_date,
                    "daily": [
                        "temperature_2m_max",
                        "temperature_2m_min",
                        "temperature_2m_mean",
                        "weather_code",
                        "precipitation_sum",
                        "wind_speed_10m_max",
                    ],
                    "temperature_unit": "fahrenheit",
                    "precipitation_unit": "inch",
                    "wind_speed_unit": "mph",
                    "timezone": "auto",
                },
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()

            daily = data.get("daily", {})
            dates = daily.get("time", [])
            highs = daily.get("temperature_2m_max", [])
            lows = daily.get("temperature_2m_min", [])
            avgs = daily.get("temperature_2m_mean", [])
            codes = daily.get("weather_code", [])
            precip_sums = daily.get("precipitation_sum", [])
            wind_maxs = daily.get("wind_speed_10m_max", [])

            historical_days = []
            total_high = 0
            total_low = 0
            total_precip = 0
            hot_days = 0  # Days >= 90°F
            cold_days = 0  # Days <= 32°F

            for i in range(len(dates)):
                code = codes[i] if i < len(codes) else 0
                description, category = WMO_CODES.get(code, ("Unknown", "unknown"))
                high = highs[i] if i < len(highs) else None
                low = lows[i] if i < len(lows) else None
                avg = avgs[i] if i < len(avgs) else None
                precip = precip_sums[i] if i < len(precip_sums) else 0

                historical_days.append({
                    "date": dates[i],
                    "high_f": high,
                    "low_f": low,
                    "avg_f": avg,
                    "weather_code": code,
                    "weather_description": description,
                    "weather_category": category,
                    "precipitation_sum": precip,
                    "wind_speed_max_mph": wind_maxs[i] if i < len(wind_maxs) else None,
                })

                # Aggregate stats
                if high is not None:
                    total_high += high
                    if high >= 90:
                        hot_days += 1
                if low is not None:
                    total_low += low
                    if low <= 32:
                        cold_days += 1
                if precip is not None:
                    total_precip += precip

            num_days = len(dates)
            summary = {
                "num_days": num_days,
                "avg_high_f": round(total_high / num_days, 1) if num_days > 0 else None,
                "avg_low_f": round(total_low / num_days, 1) if num_days > 0 else None,
                "total_precipitation_in": round(total_precip, 2),
                "hot_days_90f_plus": hot_days,
                "cold_days_32f_minus": cold_days,
            }

            result = {
                "location": location,
                "start_date": start_date,
                "end_date": end_date,
                "days": historical_days,
                "summary": summary,
            }

            self._set_cached(cache_key, result)
            return result

        except requests.RequestException as e:
            logger.error(f"Historical weather request failed: {e}")
            raise ValueError(f"Failed to fetch historical weather: {e}")
