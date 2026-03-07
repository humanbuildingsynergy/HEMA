# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
"""Configuration settings for the HEMA energy analysis system."""
import os
from enum import Enum
from typing import Optional


class LLMProvider(Enum):
    """Supported LLM providers."""
    OLLAMA = "ollama"
    OPENAI = "openai"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"


class Config:
    """Configuration settings for the energy analysis system."""

    # LLM Provider Settings
    # Change LLM_PROVIDER to switch between providers
    LLM_PROVIDER: LLMProvider = LLMProvider.OPENAI

    # Provider-specific model names
    OLLAMA_MODEL = "llama3.1:8b"  # Primary Ollama model
    OPENAI_MODEL = "gpt-4o-mini"  # Primary OpenAI model
    GOOGLE_MODEL = "gemini-1.5-flash"
    ANTHROPIC_MODEL = "claude-3-haiku-20240307"

    # Lightweight model for simple conversational responses (fallback handler)
    FALLBACK_MODEL = "gpt-4o-mini"  # Cheapest, fastest model for greetings/help

    # Simulated User Configuration (for LLM-as-user evaluation)
    # Uses Google Gemini for better context handling than local models
    SIMULATED_USER_PROVIDER: LLMProvider = LLMProvider.GOOGLE
    SIMULATED_USER_MODEL = "gemini-2.0-flash"

    # Evaluator Configuration (for LLM-as-judge evaluation)
    # Uses a more capable model version for sophisticated evaluation judgment
    EVALUATOR_PROVIDER: LLMProvider = LLMProvider.GOOGLE
    EVALUATOR_MODEL = "gemini-2.5-flash"  # More capable model for evaluation

    # Available OpenAI models (for cascade within OpenAI)
    OPENAI_MODELS = [
        "gpt-4o-mini",      # Primary: Fast, capable, cost-effective
        "gpt-4o",           # Fallback: More capable
    ]

    # Ollama settings
    OLLAMA_BASE_URL = "http://localhost:11434"

    # Available Ollama models (for cascade within Ollama)
    OLLAMA_MODELS = [
        "llama3.1:8b",      # Primary: Llama 3.1 8B
        "llama2:7b-chat",   # Fallback 1: Llama 2 7B Chat
        "codellama:latest", # Fallback 2: Code Llama
    ]

    # Common settings
    TEMPERATURE = 0.2  # Low randomness for consistent analysis (0.0-2.0)

    # LLM Cascade Configuration
    # Order of providers to try if the primary fails
    # The system will try each provider in order until one succeeds
    LLM_CASCADE = [
        LLMProvider.OPENAI,      # Primary: OpenAI
        LLMProvider.OLLAMA,      # Fallback 1: Local Ollama
        LLMProvider.GOOGLE,      # Fallback 2: Google
        LLMProvider.ANTHROPIC,   # Fallback 3: Anthropic
    ]

    # Data paths
    DATA_DIR = "data"

    # Default data (sample data for quick start and demonstration)
    DEFAULT_ENERGY_FILE = "data/home_power/energy_data_sample.csv"
    DEFAULT_RATE_FILE = "data/utility_rate/utility_rate_sample.csv"
    DEFAULT_THRESHOLDS_FILE = "data/home_power/appliance_thresholds_sample.csv"

    # Weather Configuration
    # Default to Austin, TX (sample data location)
    DEFAULT_LOCATION = os.getenv("HOME_LOCATION", "Austin, TX")
    WEATHER_CACHE_TTL = 600  # Cache weather data for 10 minutes

    @classmethod
    def get_current_model(cls) -> str:
        """Get the model name for the current provider."""
        model_map = {
            LLMProvider.OLLAMA: cls.OLLAMA_MODEL,
            LLMProvider.OPENAI: cls.OPENAI_MODEL,
            LLMProvider.GOOGLE: cls.GOOGLE_MODEL,
            LLMProvider.ANTHROPIC: cls.ANTHROPIC_MODEL,
        }
        return model_map.get(cls.LLM_PROVIDER, cls.OPENAI_MODEL)

    @classmethod
    def get_provider_info(cls) -> dict:
        """Get information about the current LLM provider configuration."""
        return {
            "provider": cls.LLM_PROVIDER.value,
            "model": cls.get_current_model(),
            "temperature": cls.TEMPERATURE,
        }


# Module-level exports for direct import
LLM_PROVIDER = Config.LLM_PROVIDER
OLLAMA_MODEL = Config.OLLAMA_MODEL
OLLAMA_MODELS = Config.OLLAMA_MODELS
OPENAI_MODEL = Config.OPENAI_MODEL
OPENAI_MODELS = Config.OPENAI_MODELS
GOOGLE_MODEL = Config.GOOGLE_MODEL
ANTHROPIC_MODEL = Config.ANTHROPIC_MODEL
FALLBACK_MODEL = Config.FALLBACK_MODEL
OLLAMA_BASE_URL = Config.OLLAMA_BASE_URL
TEMPERATURE = Config.TEMPERATURE

# Simulated user configuration exports
SIMULATED_USER_PROVIDER = Config.SIMULATED_USER_PROVIDER
SIMULATED_USER_MODEL = Config.SIMULATED_USER_MODEL

# Evaluator configuration exports
EVALUATOR_PROVIDER = Config.EVALUATOR_PROVIDER
EVALUATOR_MODEL = Config.EVALUATOR_MODEL

# Data path exports
DATA_DIR = Config.DATA_DIR
DEFAULT_ENERGY_FILE = Config.DEFAULT_ENERGY_FILE
DEFAULT_RATE_FILE = Config.DEFAULT_RATE_FILE
DEFAULT_THRESHOLDS_FILE = Config.DEFAULT_THRESHOLDS_FILE

# LLM cascade export
LLM_CASCADE = Config.LLM_CASCADE

# Weather configuration exports
DEFAULT_LOCATION = Config.DEFAULT_LOCATION
WEATHER_CACHE_TTL = Config.WEATHER_CACHE_TTL
