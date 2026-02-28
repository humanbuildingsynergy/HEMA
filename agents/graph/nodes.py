# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/graph/nodes.py
"""Graph node implementations for multi-agent workflow."""
from typing import Dict, Any

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from agents.prompts import FALLBACK_HANDLER_PROMPT
from config.config import FALLBACK_MODEL, LLMProvider
from config.llm_factory import create_llm
from utils.logger import setup_logger
from .message_utils import extract_tool_calls_from_messages, _generate_conversation_summary
from .routing import route_to_agent, classify_with_self_consistency_full

logger = setup_logger()


def create_classifier_node(analysis_agent, knowledge_agent, control_agent):
    """Create the classifier node function.

    Args:
        analysis_agent: Initialized analysis agent
        knowledge_agent: Initialized knowledge agent
        control_agent: Initialized control agent

    Returns:
        The classifier_node function
    """
    def classifier_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Classify the user query using self-consistency voting with data-aware routing."""
        user_query = state.get("user_query", "")
        conversation_history = state.get("messages", [])
        data_loaded = state.get("data_loaded", False)

        # Generate conversation summary for context-aware classification
        conversation_context = _generate_conversation_summary(conversation_history)

        # Check if this is a clarification response
        clarification_response = state.get("clarification_response")
        if clarification_response:
            # User has responded to clarification - use their selected agent
            from .routing import resolve_user_clarification
            original_results = state.get("classification_results", [])
            agent, intent = resolve_user_clarification(
                clarification_response,
                original_results
            )
            logger.info(f"Clarification resolved: agent={agent}, intent={intent}")
            return {
                "target_agent": agent,
                "query_type": intent,
                "workflow_step": "classified",
                "needs_clarification": False,
            }

        # Use self-consistency classification (N=4) with full result for logging
        classification = classify_with_self_consistency_full(user_query, conversation_context)

        if classification["needs_clarification"]:
            logger.info(f"Classification tie detected for: '{user_query[:50]}...' - requesting clarification")
            logger.info(f"Vote distribution: {classification['vote_distribution']}")
            return {
                "target_agent": None,
                "query_type": None,
                "vote_distribution": classification["vote_distribution"],
                "workflow_step": "needs_clarification",
                "needs_clarification": True,
                "clarification_options": classification["clarification_options"],
            }

        agent = classification["agent"]
        intent = classification["intent"]
        personalization_intent = classification.get("personalization_intent", "ambiguous")

        # === DATA-AWARE ROUTING ADJUSTMENT ===
        # Adjust routing based on personalization intent and data availability
        original_agent = agent

        if agent == "knowledge_agent" and personalization_intent == "personal" and data_loaded:
            # User wants personalized insights and we have data - upgrade to analysis_agent
            agent = "analysis_agent"
            intent = "recommendation"
            logger.info(
                f"Data-aware routing: Upgraded knowledge_agent -> analysis_agent "
                f"(personalization={personalization_intent}, data_loaded={data_loaded})"
            )
        elif personalization_intent == "general":
            # User explicitly wants general info - keep current agent regardless of data
            logger.info(
                f"Data-aware routing: Keeping {agent} for general query "
                f"(personalization={personalization_intent})"
            )
        # For "ambiguous", keep original routing - Knowledge Agent will use get_user_context()

        logger.info(
            f"Classified: query='{user_query[:50]}...' -> agent={agent} "
            f"(original={original_agent}), intent={intent}, personalization={personalization_intent}"
        )
        logger.info(f"Vote distribution: {classification['vote_distribution']}")
        logger.info(f"Personalization distribution: {classification.get('personalization_distribution', {})}")

        return {
            "target_agent": agent,
            "query_type": intent,
            "vote_distribution": classification["vote_distribution"],
            "personalization_intent": personalization_intent,
            "workflow_step": "classified",
            "needs_clarification": False,
        }

    return classifier_node


def create_agent_node(agent, agent_name: str, step_name: str,
                      error_desc: str, default_response: str):
    """Generic factory for ReAct agent node functions.

    Creates a node function that executes an agent and handles tool calls and responses.

    Args:
        agent: Initialized ReAct agent
        agent_name: Display name for logging ("Analysis Agent", "Knowledge Agent", etc.)
        step_name: Workflow step name for state ("analysis_complete", "knowledge_complete", etc.)
        error_desc: Description for error messages ("analysis", "knowledge query", etc.)
        default_response: Default message when agent produces no response

    Returns:
        A node function that executes the agent
    """
    def agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Run the agent."""
        if agent is None:
            return {
                "final_response": f"{agent_name} unavailable. Please check your LLM configuration.",
                "workflow_step": "agent_error",
            }

        user_query = state.get("user_query", "")
        conversation_history = state.get("messages", [])

        logger.info(f"{agent_name} processing: {user_query[:50]}...")
        logger.info(f"Conversation history: {len(conversation_history)} messages")

        try:
            # Prepare input for the agent with conversation history
            messages = list(conversation_history) + [HumanMessage(content=user_query)]
            agent_input = {"messages": messages}

            # Run the agent
            input_message_count = len(messages)
            result = agent.invoke(agent_input)

            # Extract the response
            response_messages = result.get("messages", [])
            if response_messages:
                last_message = response_messages[-1]
                response = last_message.content if hasattr(last_message, 'content') else str(last_message)
            else:
                response = default_response

            # Extract tool call information
            tool_info = extract_tool_calls_from_messages(response_messages, skip_first_n=input_message_count)
            logger.info(f"{agent_name} tools used: {tool_info['unique_tools']} ({tool_info['total_tool_calls']} calls)")

            return {
                "final_response": response,
                "workflow_step": step_name,
                "messages": [HumanMessage(content=user_query), AIMessage(content=response)],
                "tool_calls": tool_info['tool_calls'],
                "tools_used": tool_info['unique_tools'],
                "tool_call_count": tool_info['total_tool_calls'],
                "tool_distribution": tool_info['tool_counts'],
            }

        except Exception as e:
            logger.error(f"{agent_name} error: {str(e)}")
            return {
                "final_response": f"Error during {error_desc}: {str(e)}",
                "workflow_step": "agent_error",
                "error": str(e),
            }

    return agent_node


# Backward compatibility aliases (for code that might reference the old function names)
def create_analysis_agent_node(analysis_agent):
    """Create the analysis agent node function. (Deprecated: use create_agent_node directly)"""
    return create_agent_node(analysis_agent, "Analysis Agent", "analysis_complete", "analysis",
                            "Analysis completed but no response generated.")


def create_knowledge_agent_node(knowledge_agent):
    """Create the knowledge agent node function. (Deprecated: use create_agent_node directly)"""
    return create_agent_node(knowledge_agent, "Knowledge Agent", "knowledge_complete", "knowledge query",
                            "Knowledge query processed but no response generated.")


def create_control_agent_node(control_agent):
    """Create the control agent node function. (Deprecated: use create_agent_node directly)"""
    return create_agent_node(control_agent, "Control Agent", "control_complete", "device control",
                            "Control command processed but no response generated.")


def fallback_handler_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Handle general conversation using a lightweight LLM."""
    user_query = state.get("user_query", "")

    logger.info(f"Fallback handler processing: {user_query[:50]}...")

    try:
        # Use the lightweight model for simple conversational responses
        llm = create_llm(
            provider=LLMProvider.OPENAI,
            model=FALLBACK_MODEL,
            temperature=0.7,  # Slightly higher for natural conversation
        )

        messages = [
            SystemMessage(content=FALLBACK_HANDLER_PROMPT),
            HumanMessage(content=user_query),
        ]

        result = llm.invoke(messages)
        response = result.content

        logger.info(f"Fallback handler generated response using {FALLBACK_MODEL}")

    except Exception as e:
        logger.error(f"Fallback handler LLM error: {str(e)}")
        # Graceful degradation: provide a helpful static response
        response = """I'm HEMA, your Home Energy Management Assistant. I can help you with:

1. **Energy Analysis** - Analyze your consumption patterns and costs
2. **Energy Knowledge** - Explain concepts like TOU rates, solar, heat pumps
3. **Device Control** - Check and control smart home devices

How can I assist you today?"""

    return {
        "final_response": response,
        "workflow_step": "fallback_complete",
        "messages": [HumanMessage(content=user_query), AIMessage(content=response)],
    }


def clarification_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Handle classification tie - request user clarification."""
    user_query = state.get("user_query", "")
    options = state.get("clarification_options", [])

    logger.info(f"Requesting clarification for: {user_query[:50]}...")

    # Build clarification message
    option_text = "\n".join([
        f"  {i+1}. **{opt['label']}** - {opt['description']}"
        for i, opt in enumerate(options)
    ])

    response = f"""I want to make sure I understand your question correctly.

When you asked: "{user_query}"

Did you mean:
{option_text}

Please reply with the number (1, 2, etc.) or describe what you meant."""

    return {
        "final_response": response,
        "workflow_step": "awaiting_clarification",
        "needs_clarification": True,
        "messages": [HumanMessage(content=user_query), AIMessage(content=response)],
    }


def route_after_classification(state: Dict[str, Any]) -> str:
    """Route based on classification result - either to agent or clarification."""
    if state.get("needs_clarification"):
        return "clarification"
    return route_to_agent(state)
