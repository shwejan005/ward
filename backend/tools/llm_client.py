"""Unified async LLM client with structured output support."""

from __future__ import annotations

import json
from typing import Any

import structlog
from openai import AsyncOpenAI

from backend.settings import settings

logger = structlog.get_logger(__name__)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def call_llm_structured(
    system_prompt: str,
    user_message: str,
    model: str = "",
    response_schema: dict | None = None,
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """Call the LLM and return structured output.

    Returns a dict with:
    - findings: list of finding dicts (or whatever the schema requires)
    - model: the model used
    - tokens_in: input token count
    - tokens_out: output token count
    - cost_usd: estimated cost
    """
    model = model or settings.default_model
    client = _get_client()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    # Use response_format for structured output if schema provided
    if response_schema:
        kwargs["response_format"] = {"type": "json_object"}
        # Append JSON instruction to system prompt
        messages[0]["content"] += "\n\nRespond with valid JSON matching the requested schema."

    response = await client.chat.completions.create(**kwargs)

    choice = response.choices[0]
    content = choice.message.content or "{}"

    # Parse the JSON response
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("llm.json_parse_failed", model=model, content=content[:200])
        parsed = {"findings": []}

    # Calculate cost (approximate)
    tokens_in = response.usage.prompt_tokens if response.usage else 0
    tokens_out = response.usage.completion_tokens if response.usage else 0
    cost_usd = _estimate_cost(model, tokens_in, tokens_out)

    parsed["model"] = model
    parsed["tokens_in"] = tokens_in
    parsed["tokens_out"] = tokens_out
    parsed["cost_usd"] = cost_usd

    return parsed


def _estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """Rough cost estimation per model. Updated as pricing changes."""
    # Prices per 1M tokens (as of mid-2026, approximate)
    pricing = {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4.1": {"input": 2.00, "output": 8.00},
        "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    }
    rates = pricing.get(model, {"input": 2.50, "output": 10.00})
    return (tokens_in * rates["input"] + tokens_out * rates["output"]) / 1_000_000
