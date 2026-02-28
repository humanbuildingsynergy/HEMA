# agents/tools/analysis_tools/__init__.py
"""Analysis tools package for the Energy Analysis Agent.

This package provides modular analysis tools organized by functionality:
- data_tools: Data loading and access tools
- consumption_tools: Consumption and appliance analysis
- query_tools: Flexible querying and period comparison
- aggregation_tools: Time-based aggregations (weekly, monthly, seasonal)
- frequency_tools: Usage frequency and variability analysis
- solar_tools: Solar power availability analysis
"""

from .cache import get_data_cache, clear_data_cache

# TOU rate utilities
from .tou_utils import (
    is_peak_hour,
    is_off_peak_hour,
    get_tou_classification,
    get_current_rate_info,
    get_optimal_hours_for_month,
    clear_tou_cache,
)

# Data access tools
from .data_tools import (
    get_data_boundaries,
    list_available_data,
    get_tracked_appliances,
    get_utility_rate,
    load_energy_data,
)

# Consumption and appliance analysis tools
from .consumption_tools import (
    analyze_consumption,
    analyze_appliances,
    analyze_utility_rate,
    get_analysis_summary,
)

# Flexible query tools
from .query_tools import (
    query_energy_data,
    compare_energy_periods,
)

# Aggregation tools (unified flexible aggregation)
from .aggregation_tools import (
    analyze_energy_period,
    calculate_rolling_average,
    compare_weekday_weekend,
    analyze_peak_hours,
)

# Frequency and variability analysis tools
from .frequency_tools import (
    analyze_usage_frequency,
    analyze_usage_variability,
)

# Solar analysis tools
from .solar_tools import (
    analyze_solar_availability,
    analyze_solar_alignment,
)

__all__ = [
    # Cache utilities
    "get_data_cache",
    "clear_data_cache",
    # TOU rate utilities
    "is_peak_hour",
    "is_off_peak_hour",
    "get_tou_classification",
    "get_current_rate_info",
    "get_optimal_hours_for_month",
    "clear_tou_cache",
    # Data tools
    "get_data_boundaries",
    "list_available_data",
    "get_tracked_appliances",
    "get_utility_rate",
    "load_energy_data",
    # Consumption tools
    "analyze_consumption",
    "analyze_appliances",
    "analyze_utility_rate",
    "get_analysis_summary",
    # Query tools
    "query_energy_data",
    "compare_energy_periods",
    # Aggregation tools (unified flexible aggregation)
    "analyze_energy_period",
    "calculate_rolling_average",
    "compare_weekday_weekend",
    "analyze_peak_hours",
    # Frequency and variability tools
    "analyze_usage_frequency",
    "analyze_usage_variability",
    # Solar tools
    "analyze_solar_availability",
    "analyze_solar_alignment",
]
