# evaluation/config/__init__.py
"""Configuration for evaluation experiments."""

from .personas import Persona, PERSONAS, get_persona, list_personas
from .scenarios import Scenario, SCENARIOS, get_scenario, list_scenarios

__all__ = [
    "Persona", "PERSONAS", "get_persona", "list_personas",
    "Scenario", "SCENARIOS", "get_scenario", "list_scenarios",
]
