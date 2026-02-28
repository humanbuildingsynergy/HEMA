# agents/tools/knowledge_tools/__init__.py
"""Knowledge tools package for the Knowledge Agent.

This package provides knowledge and informational tools:
- knowledge_base: Energy knowledge base and topic lookup
- weather: Weather queries and energy impact analysis
- rag: Document retrieval from indexed PDFs and guides
- context: User context for personalized recommendations
"""

from .knowledge_base import energy_knowledge
from .weather import (
    get_current_weather,
    get_weather_forecast,
    get_weather_energy_impact,
    get_historical_weather,
)
from .rag import (
    search_energy_documents,
    get_knowledge_base_status,
)
from .context import get_user_context

__all__ = [
    # User context tool (for personalized recommendations)
    "get_user_context",
    # RAG tools (document search)
    "search_energy_documents",
    "get_knowledge_base_status",
    # Knowledge base tools
    "energy_knowledge",
    # Weather tools
    "get_current_weather",
    "get_weather_forecast",
    "get_weather_energy_impact",
    "get_historical_weather",
]
