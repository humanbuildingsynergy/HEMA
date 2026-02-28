# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/specialized/control_agent.py
"""Control Agent - handles IoT device control and automation.

This agent uses ADAPTIVE device tools that read all device configurations
from JSON files. No device-specific hardcoding - new devices can be added
by simply updating the configuration file.
"""
from langgraph.prebuilt import create_react_agent

from agents.prompts import CONTROL_AGENT_SYSTEM_PROMPT
from agents.tools.control_tools import (
    # Adaptive tools - work with ANY device from config
    get_device_status,
    control_device,
    get_device_list,
    get_device_energy,
    get_all_devices_energy,
    schedule_device_action,
    get_automation_rules,
    get_available_actions,
)
from agents.tools.analysis_tools import get_utility_rate
from agents.tools.knowledge_tools.weather import get_current_weather
from config.llm_factory import create_llm_with_cascade
from utils.logger import setup_logger

logger = setup_logger()



def create_control_agent():
    """
    Create the Control Agent with adaptive device control tools.

    The agent uses data-driven tools that read device configurations from JSON,
    allowing new devices to be added without code changes.

    Returns:
        A compiled ReAct agent graph ready for invocation.
    """
    logger.info("Creating Control Agent with adaptive tools")

    try:
        # Create LLM using cascade (tries multiple providers/models)
        llm = create_llm_with_cascade()
    except (ValueError, ImportError) as e:
        logger.warning(f"Failed to create LLM for Control Agent: {e}")
        return None

    # Adaptive tools - all work with any device from config
    tools = [
        # Device information
        get_device_list,
        get_device_status,
        get_available_actions,
        get_device_energy,
        get_all_devices_energy,
        # Device control
        control_device,
        schedule_device_action,
        # Automation and rates
        get_automation_rules,
        get_utility_rate,
        # Weather (for HVAC recommendations)
        get_current_weather,
    ]

    # Create the ReAct agent
    agent = create_react_agent(
        llm,
        tools,
        prompt=CONTROL_AGENT_SYSTEM_PROMPT,
    )

    logger.info("Control Agent created with tools: " + ", ".join(t.name for t in tools))
    return agent
