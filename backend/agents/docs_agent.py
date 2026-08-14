"""Docs specialist agent (L1 concern #4)."""

from __future__ import annotations

from backend.agents.base_agent import BaseSpecialist
from backend.models.enums import AgentType
from backend.prompts.registry import PromptRegistry

_prompt_registry = PromptRegistry()


class DocsAgent(BaseSpecialist):
    @property
    def agent_type(self) -> AgentType:
        return AgentType.DOCS

    @property
    def system_prompt(self) -> str:
        return _prompt_registry.get_prompt(AgentType.DOCS)
