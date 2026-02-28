# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/specialized/knowledge_agent.py
"""Knowledge Agent - handles theoretical Q&A about energy topics."""
from langgraph.prebuilt import create_react_agent

from agents.prompts import KNOWLEDGE_AGENT_SYSTEM_PROMPT
from agents.tools.knowledge_tools import (
    energy_knowledge,
    get_current_weather,
    get_weather_forecast,
    get_weather_energy_impact,
    get_historical_weather,
    search_energy_documents,
    get_knowledge_base_status,
    get_user_context,
)
from config.llm_factory import create_llm_with_cascade
from utils.logger import setup_logger

logger = setup_logger()



def create_knowledge_agent():
    """
    Create the Knowledge Agent with energy knowledge tools.

    Returns:
        A compiled ReAct agent graph ready for invocation.
    """

    logger.info("Creating Knowledge Agent")

    try:
        # Create LLM using cascade (tries multiple providers/models)
        llm = create_llm_with_cascade()
    except (ValueError, ImportError) as e:
        logger.warning(f"Failed to create LLM for Knowledge Agent: {e}")
        return None

    # Define tools (always includes RAG tools)
    tools = [
        get_user_context,  # Check user's data for personalized advice
        search_energy_documents,
        get_knowledge_base_status,
        energy_knowledge,
        get_current_weather,
        get_weather_forecast,
        get_weather_energy_impact,
        get_historical_weather,
    ]

    # Create the ReAct agent
    agent = create_react_agent(
        llm,
        tools,
        prompt=KNOWLEDGE_AGENT_SYSTEM_PROMPT,
    )

    logger.info("Knowledge Agent created with tools: " + ", ".join(t.name for t in tools))
    return agent
