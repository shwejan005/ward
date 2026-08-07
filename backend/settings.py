"""Application settings loaded from environment variables via pydantic-settings.

All secrets and configuration live in .env, never in source code.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for WARD. Reads from .env file and environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──
    tiger_database_url: str = "postgres://localhost:5432/ward"

    # ── Redis ──
    redis_url: str = "redis://localhost:6379/0"

    # ── OpenAI ──
    openai_api_key: str = ""

    # ── GitHub App ──
    github_app_id: str = ""
    github_webhook_secret: str = ""
    github_private_key_path: str = ""

    # ── Application ──
    environment: str = "development"
    log_level: str = "INFO"

    # ── Budget / Cost Control (ADR-004) ──
    daily_budget_usd: float = 50.0
    per_review_budget_usd: float = 2.0

    # ── HITL Gate (L7) ──
    confidence_threshold: float = 0.7
    auto_post_enabled: bool = True

    # ── Embedding ──
    embedding_model: str = "text-embedding-3-large"
    embedding_dimensions: int = 256

    # ── LLM ──
    default_model: str = "gpt-4o"
    fast_model: str = "gpt-4o-mini"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


# Singleton instance — import this everywhere
settings = Settings()
