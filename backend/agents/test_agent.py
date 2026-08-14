"""Test specialist agent (L1 concern #3)."""

from __future__ import annotations

from backend.agents.base_agent import BaseSpecialist
from backend.models.enums import AgentType
from backend.prompts.registry import PromptRegistry

_prompt_registry = PromptRegistry()


class TestAgent(BaseSpecialist):
    @property
    def agent_type(self) -> AgentType:
        return AgentType.TESTS

    @property
    def system_prompt(self) -> str:
        return _prompt_registry.get_prompt(AgentType.TESTS)
