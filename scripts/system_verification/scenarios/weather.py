# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# scripts/test_scenarios/scenarios/weather.py
"""WEATHER category test scenarios - Weather-related queries."""
from ..models import TestScenario

WEATHER_SCENARIOS = [
    # Basic weather queries
    TestScenario(
        id="weather_001",
        name="Current Weather Query",
        category="weather",
        input_message="What's the weather today?",
        expected_agent="knowledge_agent",
        expected_scope="GENERAL",
        expected_contains=["temperature", "°F"],
        description="Should return current weather conditions",
    ),
    TestScenario(
        id="weather_002",
        name="Current Temperature Query",
        category="weather",
        input_message="What's the temperature right now?",
        expected_agent="knowledge_agent",
        expected_scope="GENERAL",
        expected_contains=["°F"],
        description="Should return current temperature",
    ),
    TestScenario(
        id="weather_003",
        name="Weather Forecast Query",
        category="weather",
        input_message="What's the weather forecast for this week?",
        expected_agent="knowledge_agent",
        expected_scope="GENERAL",
        expected_contains=["High", "Low"],
        description="Should return multi-day forecast",
    ),
    TestScenario(
        id="weather_004",
        name="Tomorrow Weather Query",
        category="weather",
        input_message="Will it be hot tomorrow?",
        expected_agent="knowledge_agent",
        expected_scope="GENERAL",
        expected_contains=["°F"],
        description="Should return tomorrow's forecast",
    ),

    # Weather with location
    TestScenario(
        id="weather_005",
        name="Weather With Location",
        category="weather",
        input_message="What's the weather in Phoenix?",
        expected_agent="knowledge_agent",
        expected_scope="GENERAL",
        expected_contains=["Phoenix", "°F"],
        description="Should return weather for specified location",
    ),
    TestScenario(
        id="weather_006",
        name="Weather With City State",
        category="weather",
        input_message="What's the temperature in Los Angeles, CA?",
        expected_agent="knowledge_agent",
        expected_scope="GENERAL",
        expected_contains=["°F"],
        description="Should handle city, state format",
    ),

    # Weather-energy correlation queries
    TestScenario(
        id="weather_007",
        name="Weather Energy Impact",
        category="weather",
        input_message="How will the weather affect my energy usage?",
        expected_agent="knowledge_agent",
        expected_scope="GENERAL",
        expected_contains=["Cooling", "Heating"],
        description="Should analyze weather impact on energy",
    ),
    TestScenario(
        id="weather_008",
        name="AC Timing Question",
        category="weather",
        input_message="Should I run my AC now or wait until later?",
        expected_agent="knowledge_agent",
        expected_scope="GENERAL",
        expected_contains=["temperature"],
        description="Should provide weather-based AC advice",
    ),
    TestScenario(
        id="weather_009",
        name="Solar Production Weather",
        category="weather",
        input_message="Will it be sunny enough for good solar production?",
        expected_agent="knowledge_agent",
        expected_scope="GENERAL",
        expected_contains=["solar", "cloud"],
        description="Should relate weather to solar output",
    ),
    TestScenario(
        id="weather_010",
        name="Heating Demand Question",
        category="weather",
        input_message="Do I need to run the heater tonight?",
        expected_agent="knowledge_agent",
        expected_scope="GENERAL",
        expected_contains=["temperature"],
        description="Should provide heating advice based on forecast",
    ),

    # Edge cases
    TestScenario(
        id="weather_011",
        name="Weather Energy Bill Impact",
        category="weather",
        input_message="How is the weather going to impact my energy bill this week?",
        expected_agent="knowledge_agent",
        expected_scope="GENERAL",
        expected_contains=["Cooling", "energy"],
        description="Should combine weather forecast with energy impact",
    ),
    TestScenario(
        id="weather_012",
        name="Humidity Query",
        category="weather",
        input_message="What's the humidity level today?",
        expected_agent="knowledge_agent",
        expected_scope="GENERAL",
        expected_contains=["humidity", "%"],
        description="Should return humidity information",
    ),
]
