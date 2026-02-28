# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
"""LLM Factory for creating language model instances based on provider configuration."""
import os
from typing import List, Optional
from langchain_core.language_models import BaseChatModel
from langchain_core.callbacks import BaseCallbackHandler

from config.config import (
    Config,
    LLMProvider,
    OLLAMA_MODEL,
    OLLAMA_MODELS,
    OPENAI_MODEL,
    OPENAI_MODELS,
    GOOGLE_MODEL,
    ANTHROPIC_MODEL,
    OLLAMA_BASE_URL,
    TEMPERATURE,
    LLM_CASCADE,
)
from utils.logger import setup_logger
from utils.token_tracking import get_token_tracker

logger = setup_logger()


def create_llm(
    provider: Optional[LLMProvider] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    callbacks: Optional[List[BaseCallbackHandler]] = None,
    track_tokens: bool = True,
    timeout: Optional[int] = 120,
) -> BaseChatModel:
    """
    Create an LLM instance based on the specified or configured provider.

    Args:
        provider: LLM provider to use. Defaults to Config.LLM_PROVIDER.
        model: Model name to use. Defaults to provider's configured model.
        temperature: Temperature setting. Defaults to Config.TEMPERATURE.
        callbacks: Additional callback handlers to use.
        track_tokens: Whether to include the global token tracker callback.
                      Defaults to True.

    Returns:
        A configured LangChain chat model instance.

    Raises:
        ValueError: If required API key is not set or provider is unsupported.
    """
    # Use defaults from config if not specified
    provider = provider or Config.LLM_PROVIDER
    temperature = temperature if temperature is not None else TEMPERATURE

    # Build callbacks list
    all_callbacks = list(callbacks) if callbacks else []
    if track_tokens:
        all_callbacks.append(get_token_tracker())

    logger.info(f"Creating LLM: provider={provider.value}, model={model or 'default'}")

    if provider == LLMProvider.OLLAMA:
        return _create_ollama_llm(model, temperature, all_callbacks)
    elif provider == LLMProvider.OPENAI:
        return _create_openai_llm(model, temperature, all_callbacks, timeout)
    elif provider == LLMProvider.GOOGLE:
        return _create_google_llm(model, temperature, all_callbacks, timeout)
    elif provider == LLMProvider.ANTHROPIC:
        return _create_anthropic_llm(model, temperature, all_callbacks, timeout)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def _create_ollama_llm(
    model: Optional[str],
    temperature: float,
    callbacks: List[BaseCallbackHandler],
) -> BaseChatModel:
    """Create an Ollama LLM instance."""
    try:
        from langchain_ollama import ChatOllama
    except ImportError:
        raise ImportError(
            "langchain-ollama is required for Ollama support. "
            "Install it with: pip install langchain-ollama"
        )

    model = model or OLLAMA_MODEL
    logger.info(f"Using Ollama model: {model} at {OLLAMA_BASE_URL}")

    return ChatOllama(
        model=model,
        base_url=OLLAMA_BASE_URL,
        temperature=temperature,
        callbacks=callbacks if callbacks else None,
    )


def _create_openai_llm(
    model: Optional[str],
    temperature: float,
    callbacks: List[BaseCallbackHandler],
    timeout: Optional[int] = 120,
) -> BaseChatModel:
    """Create an OpenAI LLM instance."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable is required for OpenAI provider"
        )

    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise ImportError(
            "langchain-openai is required for OpenAI support. "
            "Install it with: pip install langchain-openai"
        )

    model = model or OPENAI_MODEL
    logger.info(f"Using OpenAI model: {model}")

    return ChatOpenAI(
        api_key=api_key,
        model=model,
        temperature=temperature,
        callbacks=callbacks if callbacks else None,
        timeout=timeout,
    )


def _create_google_llm(
    model: Optional[str],
    temperature: float,
    callbacks: List[BaseCallbackHandler],
    timeout: Optional[int] = 120,
) -> BaseChatModel:
    """Create a Google (Gemini) LLM instance."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY environment variable is required for Google provider"
        )

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError:
        raise ImportError(
            "langchain-google-genai is required for Google support. "
            "Install it with: pip install langchain-google-genai"
        )

    model = model or GOOGLE_MODEL
    logger.info(f"Using Google model: {model}")

    return ChatGoogleGenerativeAI(
        google_api_key=api_key,
        model=model,
        temperature=temperature,
        callbacks=callbacks if callbacks else None,
        timeout=timeout,
    )


def _create_anthropic_llm(
    model: Optional[str],
    temperature: float,
    callbacks: List[BaseCallbackHandler],
    timeout: Optional[int] = 120,
) -> BaseChatModel:
    """Create an Anthropic (Claude) LLM instance."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable is required for Anthropic provider"
        )

    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError:
        raise ImportError(
            "langchain-anthropic is required for Anthropic support. "
            "Install it with: pip install langchain-anthropic"
        )

    model = model or ANTHROPIC_MODEL
    logger.info(f"Using Anthropic model: {model}")

    return ChatAnthropic(
        api_key=api_key,
        model=model,
        temperature=temperature,
        callbacks=callbacks if callbacks else None,
        default_request_timeout=timeout,
    )


def create_llm_with_cascade(
    temperature: Optional[float] = None,
    callbacks: Optional[List[BaseCallbackHandler]] = None,
    track_tokens: bool = True,
    timeout: Optional[int] = 120,
) -> BaseChatModel:
    """
    Create an LLM instance using cascade logic.

    Tries providers in order defined by LLM_CASCADE config.
    For Ollama, tries multiple models defined in OLLAMA_MODELS.

    Args:
        temperature: Temperature setting. Defaults to Config.TEMPERATURE.
        callbacks: Additional callback handlers to use.
        track_tokens: Whether to include the global token tracker callback.
                      Defaults to True.
        timeout: Request timeout in seconds. Defaults to 120.

    Returns:
        A configured LangChain chat model instance.

    Raises:
        ValueError: If no provider could be initialized.
    """
    temperature = temperature if temperature is not None else TEMPERATURE

    # Build callbacks list
    all_callbacks = list(callbacks) if callbacks else []
    if track_tokens:
        all_callbacks.append(get_token_tracker())

    errors = []

    for provider in LLM_CASCADE:
        logger.info(f"Trying provider: {provider.value}")

        if provider == LLMProvider.OLLAMA:
            # Try multiple Ollama models
            for model in OLLAMA_MODELS:
                try:
                    llm = _create_ollama_llm(model, temperature, all_callbacks)
                    # Test the connection with a simple call
                    logger.info(f"Successfully created Ollama LLM with model: {model}")
                    return llm
                except Exception as e:
                    logger.warning(f"Failed to create Ollama with {model}: {e}")
                    errors.append(f"Ollama/{model}: {e}")
        elif provider == LLMProvider.OPENAI:
            # Try multiple OpenAI models
            for model in OPENAI_MODELS:
                try:
                    llm = _create_openai_llm(model, temperature, all_callbacks, timeout)
                    logger.info(f"Successfully created OpenAI LLM with model: {model}")
                    return llm
                except Exception as e:
                    logger.warning(f"Failed to create OpenAI with {model}: {e}")
                    errors.append(f"OpenAI/{model}: {e}")
        else:
            try:
                # For other providers, use create_llm but don't double-add tracker
                llm = create_llm(
                    provider=provider,
                    temperature=temperature,
                    callbacks=all_callbacks,
                    track_tokens=False,  # Already added above
                    timeout=timeout,
                )
                logger.info(f"Successfully created LLM with provider: {provider.value}")
                return llm
            except Exception as e:
                logger.warning(f"Failed to create {provider.value} LLM: {e}")
                errors.append(f"{provider.value}: {e}")

    raise ValueError(f"Failed to create LLM with any provider. Errors: {errors}")


def get_available_providers() -> list[dict]:
    """
    Get a list of available LLM providers with their status.

    Returns:
        List of provider info dicts with availability status.
    """
    providers = []

    # Ollama - check if server is reachable
    ollama_available = False
    try:
        import requests
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        ollama_available = response.status_code == 200
    except Exception:
        pass

    providers.append({
        "provider": LLMProvider.OLLAMA.value,
        "model": OLLAMA_MODEL,
        "available": ollama_available,
        "reason": None if ollama_available else "Ollama server not reachable",
    })

    # OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    providers.append({
        "provider": LLMProvider.OPENAI.value,
        "model": OPENAI_MODEL,
        "available": bool(openai_key),
        "reason": None if openai_key else "OPENAI_API_KEY not set",
    })

    # Google
    google_key = os.getenv("GOOGLE_API_KEY")
    providers.append({
        "provider": LLMProvider.GOOGLE.value,
        "model": GOOGLE_MODEL,
        "available": bool(google_key),
        "reason": None if google_key else "GOOGLE_API_KEY not set",
    })

    # Anthropic
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    providers.append({
        "provider": LLMProvider.ANTHROPIC.value,
        "model": ANTHROPIC_MODEL,
        "available": bool(anthropic_key),
        "reason": None if anthropic_key else "ANTHROPIC_API_KEY not set",
    })

    return providers
