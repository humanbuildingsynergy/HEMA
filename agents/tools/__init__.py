# agents/tools/__init__.py
"""LangChain tools for the multi-agent system."""
from .analysis_tools import (
    # Data tools
    list_available_data,
    get_tracked_appliances,
    get_utility_rate,
    load_energy_data,
    # Consumption tools
    analyze_consumption,
    analyze_appliances,
    analyze_utility_rate,
    get_analysis_summary,
    # Query tools
    query_energy_data,
    compare_energy_periods,
    # Aggregation tools (unified flexible aggregation)
    analyze_energy_period,
    calculate_rolling_average,
    compare_weekday_weekend,
    analyze_peak_hours,
    # Frequency and variability tools
    analyze_usage_frequency,
    analyze_usage_variability,
    # Solar tools
    analyze_solar_availability,
)
from .knowledge_tools import (
    # Knowledge base tools
    energy_knowledge,
    # Weather tools
    get_current_weather,
    get_weather_forecast,
    get_weather_energy_impact,
)
from .control_tools import (
    # Device information
    get_device_status,
    get_device_list,
    get_available_actions,
    get_device_energy,
    get_all_devices_energy,
    # Device control
    control_device,
    schedule_device_action,
    # Automation
    get_automation_rules,
)

__all__ = [
    # Analysis tools - Data
    "list_available_data",
    "get_tracked_appliances",
    "get_utility_rate",
    "load_energy_data",
    # Analysis tools - Consumption
    "analyze_consumption",
    "analyze_appliances",
    "analyze_utility_rate",
    "get_analysis_summary",
    # Analysis tools - Query
    "query_energy_data",
    "compare_energy_periods",
    # Analysis tools - Aggregation (unified flexible aggregation)
    "analyze_energy_period",
    "calculate_rolling_average",
    "compare_weekday_weekend",
    "analyze_peak_hours",
    # Analysis tools - Frequency and variability
    "analyze_usage_frequency",
    "analyze_usage_variability",
    # Analysis tools - Solar
    "analyze_solar_availability",
    # Knowledge tools
    "energy_knowledge",
    # Weather tools
    "get_current_weather",
    "get_weather_forecast",
    "get_weather_energy_impact",
    # Control tools - Device information
    "get_device_status",
    "get_device_list",
    "get_available_actions",
    "get_device_energy",
    "get_all_devices_energy",
    # Control tools - Device control
    "control_device",
    "schedule_device_action",
    # Control tools - Automation
    "get_automation_rules",
]
