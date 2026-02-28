# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# agents/graph/self_consistency_classifier.py
"""Self-Consistency Chain-of-Thought classifier with tie-based user confirmation."""
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from langchain_core.messages import HumanMessage, SystemMessage
from config.config import LLM_CASCADE, TEMPERATURE
from config.llm_factory import create_llm, create_llm_with_cascade
from utils.logger import setup_logger

logger = setup_logger()

# Number of parallel classification runs
N_SAMPLES = 4

# Agent categories (used as classification targets)
AGENT_ANALYSIS = "analysis_agent"
AGENT_KNOWLEDGE = "knowledge_agent"
AGENT_CONTROL = "control_agent"
AGENT_FALLBACK = "fallback_handler"

# Valid agents list
VALID_AGENTS = [AGENT_ANALYSIS, AGENT_KNOWLEDGE, AGENT_CONTROL, AGENT_FALLBACK]

# Intent categories by agent
ANALYSIS_INTENTS = ["data_lookup", "analysis", "rate_info", "recommendation"]
KNOWLEDGE_INTENTS = ["concept", "how_to", "comparison", "best_practice"]
CONTROL_INTENTS = ["thermostat", "schedule", "device_status", "automation"]
FALLBACK_INTENTS = ["greeting", "help", "thanks", "off_topic"]


@dataclass
class ClassificationResult:
    """Result from a single classification run."""
    agent: str
    intent: str
    reasoning: str
    confidence: float
    personalization_intent: str  # "personal", "general", or "ambiguous"


@dataclass
class ConsensusResult:
    """Result from self-consistency voting."""
    is_consensus: bool
    agent: Optional[str]
    intent: Optional[str]
    personalization_intent: Optional[str]  # Voted personalization intent
    vote_distribution: Dict[str, int]
    personalization_distribution: Dict[str, int]  # Votes for personalization intent
    needs_clarification: bool
    clarification_options: Optional[List[Dict[str, str]]]
    all_results: List[ClassificationResult]


# Chain-of-Thought prompt for agent classification
AGENT_COT_PROMPT = """You are classifying a user query for HEMA (Home Energy Management Assistant), a home energy management system.

## Your Task
Classify the query along TWO dimensions:
1. **Agent**: Which specialized agent should handle this query?
2. **Personalization Intent**: Does the user want personalized insights or general knowledge?

## Dimension 1: Agent Selection

Follow these steps to determine the appropriate agent:

0. **Consider conversation context** (if provided): What topic was being discussed?
   - Use this context to better understand what the user is asking for

1. **Identify the core request**: What is the user fundamentally asking for?
   - Information about their own energy data/usage?
   - General knowledge or explanation?
   - Device status or control action?
   - Interaction with the assistant itself?

2. **Check for data dependency**: Does answering require the user's historical energy data?
   - YES → likely analysis_agent
   - NO → continue to Step 3

3. **Check for device interaction**: Does it involve checking or controlling a smart device?
   - YES → control_agent
   - NO → continue to Step 4

4. **Check for energy and weather-related knowledge**: Is it asking about energy concepts, energy-saving guidelines, weather conditions, or general tips?
   - YES → knowledge_agent
   - NO → fallback_handler

5. **Apply critical distinctions**:
   - "my" + current device state → control_agent (not analysis_agent)
   - "my" + historical data/costs → analysis_agent (not control_agent)
   - About this system/assistant → fallback_handler (not knowledge_agent)
   - About energy topics → knowledge_agent (not fallback_handler)

## Dimension 2: Personalization Intent

Separately assess whether the user wants personalized or general information:

- **personal**: The user wants insights tailored to THEIR specific home, usage patterns, or situation. They would benefit from data-driven analysis of their actual consumption.

- **general**: The user wants universal/educational information NOT tied to their specific situation. They're seeking broadly applicable knowledge, best practices, or conceptual explanations.

- **ambiguous**: The query could reasonably be interpreted either way.

IMPORTANT: Focus on the semantic meaning and underlying intent, not surface-level keywords:
- "What does my TOU rate mean?" → general (seeking explanation, not personal data)
- "How much am I paying in TOU charges?" → personal (wants their specific costs)
- "How do heat pumps work?" → general (educational question)
- "Is my heat pump efficient?" → personal (wants analysis of their usage)
- "Tips for saving energy" → ambiguous (could be general advice or tailored to their situation)

## Agent Categories

### analysis_agent
Requires the USER'S HISTORICAL ENERGY DATA to answer.
- Consumption history, usage patterns, cost calculations over time
- Loading or analyzing the user's energy data files
- Personalized recommendations based on their actual usage
- Appliance-level breakdowns and comparisons

### control_agent
Handles queries about SMART DEVICE STATUS or CONTROL actions.
- Checking current device state (temperature, on/off, charging status, mode)
- Commanding device changes (set, turn, start, stop)
- Scheduling and automation

### knowledge_agent
Handles educational questions about ENERGY CONCEPTS, WEATHER CONDITIONS, and ENERGY-SAVING GUIDELINES.
- Definitions and explanations of energy terms and concepts
- How energy technologies and systems work
- General tips and best practices
- Comparisons between energy options
- Weather conditions and their impact on energy usage

### fallback_handler
Handles queries interacting with THIS ASSISTANT or unclear queries.
- Greetings and social exchanges
- Questions about this system's capabilities or identity
- Unclear, ambiguous, or off-topic queries

## Response Format
Apply the reasoning process above for BOTH dimensions, then provide your answer as JSON:

```json
{
  "reasoning": "Agent selection: 1. Core request: [what user wants]. 2. Data dependency: [yes/no, why]. 3. Device interaction: [yes/no, why]. 4. Energy knowledge: [yes/no, why]. 5. Critical distinctions: [if any]. Agent decision: [agent] because [reason]. Personalization: [personal/general/ambiguous] because [semantic reasoning about user's underlying intent].",
  "agent": "analysis_agent|knowledge_agent|control_agent|fallback_handler",
  "intent": "specific intent within agent's domain",
  "personalization_intent": "personal|general|ambiguous",
  "confidence": 0.0-1.0
}
```
"""


def _parse_classification_response(response_text: str) -> Optional[ClassificationResult]:
    """Parse the LLM's classification response."""
    try:
        text = response_text.strip()

        # Handle markdown code blocks
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.index("```") + 3
            end = text.index("```", start)
            text = text[start:end].strip()
        elif "{" in text and "}" in text:
            start = text.index("{")
            end = text.rindex("}") + 1
            text = text[start:end]

        result = json.loads(text)

        agent = result.get("agent", "").lower()
        if agent not in VALID_AGENTS:
            logger.warning(f"Invalid agent '{agent}', defaulting to fallback_handler")
            agent = AGENT_FALLBACK

        # Parse personalization intent with validation
        personalization = result.get("personalization_intent", "ambiguous").lower()
        if personalization not in ["personal", "general", "ambiguous"]:
            logger.warning(f"Invalid personalization_intent '{personalization}', defaulting to ambiguous")
            personalization = "ambiguous"

        return ClassificationResult(
            agent=agent,
            intent=result.get("intent", "general"),
            reasoning=result.get("reasoning", ""),
            confidence=float(result.get("confidence", 0.5)),
            personalization_intent=personalization
        )
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.warning(f"Failed to parse classification response: {e}")
        return None


def _run_single_classification(
    query: str,
    temperature: float,
    conversation_context: Optional[str] = None
) -> Optional[ClassificationResult]:
    """Run a single classification with the given temperature.

    Args:
        query: The user's query string
        temperature: Temperature for LLM diversity
        conversation_context: Optional recent conversation summary for context
    """
    try:
        # Use cascade to automatically fallback to available providers
        llm = create_llm_with_cascade(temperature=temperature)

        # Build prompt with optional conversation context
        if conversation_context:
            context_section = f"""## Conversation Context
The following is the recent conversation history. Use this to understand if the current query is a follow-up:

{conversation_context}

---

"""
            prompt = AGENT_COT_PROMPT.replace("## Your Task", f"{context_section}## Your Task")
        else:
            prompt = AGENT_COT_PROMPT

        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=query)
        ]

        response = llm.invoke(messages)
        return _parse_classification_response(response.content)

    except Exception as e:
        logger.warning(f"Classification run failed: {e}")
        return None


def classify_with_self_consistency(
    query: str,
    conversation_context: Optional[str] = None,
    n_samples: int = N_SAMPLES,
    temperature: float = 0.7
) -> ConsensusResult:
    """
    Classify a query using self-consistency with N parallel runs.

    Uses temperature > 0 to get diverse reasoning paths, then votes on agent
    and personalization intent. Ties trigger user confirmation.

    Args:
        query: The user's query string
        conversation_context: Optional recent conversation summary for context
        n_samples: Number of parallel classification runs (default 4)
        temperature: Temperature for diversity (default 0.7)

    Returns:
        ConsensusResult with voting outcome and clarification options if needed
    """
    logger.info(f"Starting self-consistency classification with N={n_samples}")

    # Run N classifications in parallel using ThreadPoolExecutor
    results: List[ClassificationResult] = []

    with ThreadPoolExecutor(max_workers=n_samples) as executor:
        futures = [
            executor.submit(_run_single_classification, query, temperature, conversation_context)
            for _ in range(n_samples)
        ]

        for future in futures:
            try:
                result = future.result(timeout=30)
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning(f"Classification future failed: {e}")

    if not results:
        logger.error("All classification runs failed")
        return ConsensusResult(
            is_consensus=False,
            agent=AGENT_FALLBACK,
            intent="general",
            personalization_intent="ambiguous",
            vote_distribution={},
            personalization_distribution={},
            needs_clarification=False,
            clarification_options=None,
            all_results=[]
        )

    # Count votes by agent
    vote_counts: Dict[str, int] = {}
    for result in results:
        vote_counts[result.agent] = vote_counts.get(result.agent, 0) + 1

    # Count votes by personalization intent
    personalization_counts: Dict[str, int] = {}
    for result in results:
        p = result.personalization_intent
        personalization_counts[p] = personalization_counts.get(p, 0) + 1

    logger.info(f"Vote distribution: {vote_counts}")
    logger.info(f"Personalization distribution: {personalization_counts}")

    # Determine if there's a clear winner for agent
    max_votes = max(vote_counts.values())
    winners = [agent for agent, count in vote_counts.items() if count == max_votes]

    # Check for tie (multiple agents with same max votes)
    is_tie = len(winners) > 1

    if is_tie:
        # Tie detected - need user clarification
        logger.info(f"Tie detected between: {winners}")

        clarification_options = _generate_clarification_options(winners, query)

        return ConsensusResult(
            is_consensus=False,
            agent=None,
            intent=None,
            personalization_intent=None,
            vote_distribution=vote_counts,
            personalization_distribution=personalization_counts,
            needs_clarification=True,
            clarification_options=clarification_options,
            all_results=results
        )

    # Clear winner for agent
    winning_agent = winners[0]

    # Get most common intent for the winning agent
    agent_results = [r for r in results if r.agent == winning_agent]
    intent_counts: Dict[str, int] = {}
    for r in agent_results:
        intent_counts[r.intent] = intent_counts.get(r.intent, 0) + 1
    winning_intent = max(intent_counts, key=intent_counts.get)

    # Determine winning personalization intent (simple majority across all votes)
    winning_personalization = max(personalization_counts, key=personalization_counts.get)

    logger.info(f"Consensus reached: agent={winning_agent}, intent={winning_intent}, personalization={winning_personalization}")

    return ConsensusResult(
        is_consensus=True,
        agent=winning_agent,
        intent=winning_intent,
        personalization_intent=winning_personalization,
        vote_distribution=vote_counts,
        personalization_distribution=personalization_counts,
        needs_clarification=False,
        clarification_options=None,
        all_results=results
    )


def _generate_clarification_options(
    tied_agents: List[str],
    query: str
) -> List[Dict[str, str]]:
    """Generate user-friendly clarification options for tied agents."""
    options = []

    agent_descriptions = {
        AGENT_ANALYSIS: {
            "label": "My specific data",
            "description": "Show me information from my energy data or rate plan"
        },
        AGENT_KNOWLEDGE: {
            "label": "General explanation",
            "description": "Explain this concept or provide general information"
        },
        AGENT_CONTROL: {
            "label": "Control a device",
            "description": "Change a setting or control a smart device"
        },
        AGENT_FALLBACK: {
            "label": "Just chatting",
            "description": "General conversation or help with the system"
        }
    }

    for agent in tied_agents:
        if agent in agent_descriptions:
            options.append({
                "agent": agent,
                **agent_descriptions[agent]
            })

    return options


def resolve_clarification(
    selected_agent: str,
    original_results: List[ClassificationResult]
) -> Tuple[str, str]:
    """
    Resolve classification after user clarification.

    Args:
        selected_agent: The agent selected by the user
        original_results: The original classification results

    Returns:
        Tuple of (agent, intent)
    """
    # Find the most common intent for the selected agent
    agent_results = [r for r in original_results if r.agent == selected_agent]

    if agent_results:
        intent_counts: Dict[str, int] = {}
        for r in agent_results:
            intent_counts[r.intent] = intent_counts.get(r.intent, 0) + 1
        intent = max(intent_counts, key=intent_counts.get)
    else:
        # Fallback intents by agent
        default_intents = {
            AGENT_ANALYSIS: "data_lookup",
            AGENT_KNOWLEDGE: "concept",
            AGENT_CONTROL: "device_status",
            AGENT_FALLBACK: "general"
        }
        intent = default_intents.get(selected_agent, "general")

    return selected_agent, intent


# Convenience function for direct use
def classify_query(
    query: str,
    conversation_context: Optional[str] = None
) -> Tuple[str, str, bool, Optional[List[Dict[str, str]]]]:
    """
    Classify a query and return routing information.

    Args:
        query: The user's query string
        conversation_context: Optional recent conversation summary for context

    Returns:
        Tuple of (agent, intent, needs_clarification, clarification_options)
    """
    result = classify_with_self_consistency(query, conversation_context)

    if result.needs_clarification:
        return (
            None,
            None,
            True,
            result.clarification_options
        )

    return (
        result.agent,
        result.intent,
        False,
        None
    )


def classify_query_full(
    query: str,
    conversation_context: Optional[str] = None
) -> ConsensusResult:
    """
    Classify a query and return the full ConsensusResult.

    This is useful when you need access to vote_distribution and other
    detailed classification information for logging/debugging.

    Args:
        query: The user's query string
        conversation_context: Optional recent conversation summary for context

    Returns:
        Full ConsensusResult with all classification details
    """
    return classify_with_self_consistency(query, conversation_context)
