"""Prompt registry that loads versioned markdown prompt templates from disk with fallback."""

from __future__ import annotations

from pathlib import Path
import structlog
from backend.models.enums import AgentType

logger = structlog.get_logger(__name__)

_PROMPTS_DIR = Path(__file__).parent / "templates"


class PromptRegistry:
    """Loads and caches specialist prompt templates."""

    def __init__(self) -> None:
        self._cache: dict[AgentType, str] = {}

    def get_prompt(self, agent_type: AgentType) -> str:
        """Get the system prompt for a specialist agent."""
        if agent_type in self._cache:
            return self._cache[agent_type]

        file_map = {
            AgentType.SECURITY: "security.md",
            AgentType.QUALITY: "quality.md",
            AgentType.TESTS: "tests.md",
            AgentType.DOCS: "docs.md",
        }

        filename = file_map.get(agent_type)
        if filename:
            filepath = _PROMPTS_DIR / filename
            if filepath.exists():
                try:
                    content = filepath.read_text(encoding="utf-8")
                    self._cache[agent_type] = content
                    return content
                except Exception as e:
                    logger.warning("prompt.load_failed", path=str(filepath), error=str(e))

        # Fallback default
        return f"You are a specialist reviewing pull requests for {agent_type.value} concerns."
