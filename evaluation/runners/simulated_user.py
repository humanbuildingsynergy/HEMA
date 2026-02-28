# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/runners/simulated_user.py
"""
Simulated User module for LLM-as-Simulated-User evaluation.

Uses a lower-capability LLM (Llama via Ollama) to simulate realistic user behavior,
including confusion, follow-up questions, and persona-consistent responses.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from config.config import (
    LLMProvider,
    Config,
    SIMULATED_USER_PROVIDER,
    SIMULATED_USER_MODEL,
)
from config.llm_factory import create_llm
from ..config import Persona, Scenario


class OpeningMode(Enum):
    """Mode for generating opening messages in evaluation.

    CONTROLLED: Use the scenario's opening_message template and paraphrase it.
                This provides reproducibility for controlled experiments.

    RANDOM: Generate opening purely from goal and persona, with no template.
            This provides diversity and tests robustness to varied phrasings.
    """
    CONTROLLED = "controlled"
    RANDOM = "random"

# System prompt template for simulated user
SIMULATED_USER_SYSTEM_PROMPT = """You are role-playing as a real person interacting with an energy management chatbot called HEMA.

CRITICAL INSTRUCTIONS:
1. Stay COMPLETELY in character as the persona described below
2. Your responses should be SHORT (1-3 sentences typically, like real chat)
3. You CAN and SHOULD:
   - Ask follow-up questions when confused
   - Express frustration if explanations are unclear
   - Make typos occasionally if the persona would
   - Say "I don't understand" when appropriate
4. You should NOT:
   - Break character or mention you're an AI
   - Give perfect, well-structured responses
   - Already know the answers
   - Be overly polite or formal (unless persona requires it)
   - Keep asking tangential questions after your main goal is answered

{persona_context}

{scenario_context}

## Conversation Rules
- Respond naturally as {persona_name} would
- Keep track of what the chatbot has explained so far
- If satisfied with an explanation, acknowledge it briefly and thank the chatbot
- If still confused, say so and ask for clarification
- When your goal is achieved, wrap up the conversation naturally with a thank you
- If the conversation seems stuck or unhelpful after several turns, express mild frustration

## Goal Completion Behavior

When your goal has been achieved and you feel satisfied:
- Acknowledge what you learned or what action was completed
- Express satisfaction with words like: "thanks", "perfect", "that helps", "got it", "great", "makes sense"
- Thank the chatbot briefly and naturally
- DO NOT continue asking tangential questions

**For information goals:** Your goal is met when you:
1. Received specific data/numbers answering your main question
2. Got actionable recommendations for YOUR situation
3. Understand the context (e.g., is this normal? what causes it?)

**For action/control goals:** Your goal is met when:
1. The action has been CONFIRMED as completed by the chatbot
2. You understand what was done and why

**IMPORTANT:** When you're satisfied, include clear satisfaction signals like:
- "Thanks for the help!"
- "That's perfect, exactly what I needed."
- "Great, that makes sense now."
- "Perfect, I've got what I need."
- "Appreciate it, that's very helpful!"

**Key principle:** Real users don't end conversations after getting basic info. They ask follow-up questions, seek clarification, and want specific recommendations. But once satisfied, they wrap up naturally with clear signals like thank-yous and satisfaction expressions.
"""


@dataclass
class UserTurn:
    """A single turn from the simulated user."""
    message: str
    turn_number: int
    # Token usage for this turn
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class SimulatedUser:
    """
    Simulates a user interacting with the HEMA system.

    Uses Llama (via Ollama) to generate persona-consistent responses
    that simulate realistic user behavior.
    """

    def __init__(
        self,
        persona: Persona,
        scenario: Scenario,
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        temperature: float = 0.8,  # Higher temperature for more natural variation
        opening_mode: OpeningMode = OpeningMode.CONTROLLED,
    ):
        """
        Initialize the simulated user.

        Args:
            persona: The persona to role-play
            scenario: The scenario/goal for the conversation
            provider: LLM provider (default: Google for better context handling)
            model: Specific model to use (default: gemini-2.0-flash)
            temperature: Temperature for response generation
            opening_mode: How to generate the opening message:
                - CONTROLLED: Paraphrase the scenario's opening_message template
                - RANDOM: Generate purely from goal and persona (no template)
        """
        self.persona = persona
        self.scenario = scenario
        self.temperature = temperature
        self.opening_mode = opening_mode

        # Use Google Gemini by default for better context handling
        # (different model version from evaluator which uses Gemini 2.5)
        self.provider = provider or SIMULATED_USER_PROVIDER
        self.model = model or SIMULATED_USER_MODEL

        # Create the LLM
        self.llm = create_llm(
            provider=self.provider,
            model=self.model,
            temperature=temperature,
        )

        # Build system prompt
        self.system_prompt = SIMULATED_USER_SYSTEM_PROMPT.format(
            persona_context=persona.to_prompt_context(),
            scenario_context=scenario.to_prompt_context(),
            persona_name=persona.id,
        )

        # Conversation history
        self.history: List[dict] = []
        self.turn_count = 0

    def get_opening_message(self) -> UserTurn:
        """
        Get the opening message for the conversation.

        Based on opening_mode:
        - CONTROLLED: Generates a natural variation of the scenario's opening message
        - RANDOM: Generates purely from goal and persona characteristics
        """
        if self.opening_mode == OpeningMode.CONTROLLED:
            # Controlled mode: paraphrase the template for reproducibility
            prompt = f"""Generate your opening message to start the conversation.
The scenario suggests starting with something like: "{self.scenario.opening_message}"

Paraphrase this naturally in your own words as {self.persona.id} would say it.
Keep it short and natural (1-2 sentences). Don't be overly formal."""
        else:
            # Random mode: generate purely from goal and persona (no template)
            prompt = f"""Generate your opening message to start a conversation with an energy management chatbot.

Your goal is: {self.scenario.primary_goal}

You are {self.persona.id}, and you should express yourself naturally based on your background and communication style.
Keep it short and natural (1-2 sentences). Don't be overly formal.
Do NOT mention specific energy terms or concepts you wouldn't naturally know based on your technical level.
Just express your need or question in your own words."""

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=prompt),
        ]

        response = self.llm.invoke(messages)
        message = response.content.strip()

        # Extract token usage from response metadata
        input_tokens = 0
        output_tokens = 0
        if hasattr(response, 'response_metadata') and response.response_metadata:
            usage = response.response_metadata.get('usage', {}) or response.response_metadata.get('token_usage', {})
            input_tokens = usage.get('prompt_tokens', 0) or usage.get('input_tokens', 0)
            output_tokens = usage.get('completion_tokens', 0) or usage.get('output_tokens', 0)

        self.turn_count = 1
        self.history.append({"role": "user", "content": message})

        return UserTurn(
            message=message,
            turn_number=self.turn_count,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        )

    def respond_to_system(self, system_response: str) -> UserTurn:
        """
        Generate a response to the HEMA system's message.

        Args:
            system_response: The response from the HEMA system

        Returns:
            UserTurn with the simulated user's response
        """
        # Add system response to history
        self.history.append({"role": "assistant", "content": system_response})

        # Build conversation context
        conversation_context = self._build_conversation_context()

        # Goal reminder for context (goal completion is evaluated separately)
        goal_reminder = f"""
**Reminder:** Your primary goal is: {self.scenario.primary_goal}
If the chatbot has addressed your goal, wrap up naturally with a thank you.
If not, continue the conversation to get what you need.
"""

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""Here is the conversation so far:

{conversation_context}

Now respond as {self.persona.id}. Remember:
- Keep it short and natural (1-3 sentences)
- Stay in character
- Ask follow-up questions if still confused about your PRIMARY goal
- If satisfied, wrap up naturally with a brief thank you
{goal_reminder}
Your response:"""),
        ]

        response = self.llm.invoke(messages)
        message = response.content.strip()

        # Extract token usage from response metadata
        input_tokens = 0
        output_tokens = 0
        if hasattr(response, 'response_metadata') and response.response_metadata:
            usage = response.response_metadata.get('usage', {}) or response.response_metadata.get('token_usage', {})
            input_tokens = usage.get('prompt_tokens', 0) or usage.get('input_tokens', 0)
            output_tokens = usage.get('completion_tokens', 0) or usage.get('output_tokens', 0)

        self.turn_count += 1
        self.history.append({"role": "user", "content": message})

        return UserTurn(
            message=message,
            turn_number=self.turn_count,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        )

    def detect_wrap_up_signal(self, user_message: str) -> bool:
        """
        Detect if the user message contains a natural wrap-up signal.

        Real users signal conversation completion through:
        - Explicit thanks/gratitude
        - Satisfaction indicators
        - Closure statements

        This is more reliable than external goal evaluation because the signal
        is explicit in the user's natural response.

        Args:
            user_message: The user's message to analyze

        Returns:
            True if message contains wrap-up signals, False otherwise
        """
        if not user_message:
            return False

        message_lower = user_message.lower()

        # Wrap-up signal keywords (user is signaling they're satisfied/done)
        wrap_up_signals = [
            # Gratitude
            "thank", "thanks", "appreciate", "grateful",
            # Satisfaction
            "perfect", "great", "excellent", "helpful", "exactly",
            "that's what", "just what", "that helps", "got it",
            # Closure
            "got it", "all set", "all good", "good to go", "ready to",
            "makes sense", "understand now", "clear now",
            # Persona-specific closures
            "sounds good", "works for me", "i'm good", "that's all",
        ]

        # Check if message contains any wrap-up signals
        for signal in wrap_up_signals:
            if signal in message_lower:
                return True

        return False

    def _build_conversation_context(self) -> str:
        """Build a string representation of the conversation history."""
        lines = []
        for turn in self.history:
            if turn["role"] == "user":
                lines.append(f"You ({self.persona.id}): {turn['content']}")
            else:
                lines.append(f"HEMA (chatbot): {turn['content']}")
        return "\n\n".join(lines)

    def get_conversation_history(self) -> List[dict]:
        """Get the full conversation history."""
        return self.history.copy()

    def reset(self) -> None:
        """Reset the conversation state."""
        self.history = []
        self.turn_count = 0
