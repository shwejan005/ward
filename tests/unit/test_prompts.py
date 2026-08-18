"""Unit tests for prompt registry and template loading."""

from __future__ import annotations

from backend.models.enums import AgentType
from backend.prompts.registry import PromptRegistry


def test_prompt_registry_loads_templates():
    registry = PromptRegistry()
    for agent_type in [AgentType.SECURITY, AgentType.QUALITY, AgentType.TESTS, AgentType.DOCS]:
        prompt = registry.get_prompt(agent_type)
        assert len(prompt) > 50
        assert "System Prompt" in prompt or "Specialist" in prompt
