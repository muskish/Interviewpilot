"""
Reusable, provider-agnostic LLM service.

Every agent talks to the LLM through this module only — no agent imports
langchain_groq/openai/anthropic/ollama directly. That's what makes
LLM_PROVIDER swappable via .env without touching agent code.
"""
from __future__ import annotations

import time
from typing import TypeVar

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, ValidationError

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


def get_llm(temperature: float | None = None) -> BaseChatModel:
    """
    Build a chat model for whichever provider is active in settings.

    Raises RuntimeError immediately (via settings.require_api_key()) if the
    active provider's key is missing — fail fast at startup, not mid-interview.
    """
    temp = settings.llm_temperature if temperature is None else temperature
    provider = settings.llm_provider

    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(api_key=settings.require_api_key(), model=settings.llm_model, temperature=temp)

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(api_key=settings.require_api_key(), model=settings.llm_model, temperature=temp)

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(api_key=settings.require_api_key(), model=settings.llm_model, temperature=temp)

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=settings.llm_model, temperature=temp)

    raise RuntimeError(f"Unknown LLM_PROVIDER: {provider}")  # unreachable — config.py already restricts this


def generate_structured(
    llm: BaseChatModel,
    system_prompt: str,
    user_message: str,
    output_model: type[T],
    max_retries: int | None = None,
) -> T:
    """
    Call the LLM and force its response into `output_model` (a Pydantic model).

    Retries on validation/parsing failure — LLMs occasionally return output
    that doesn't match the schema. A bounded retry handles transient cases;
    if it still fails after max_retries, we raise loudly instead of letting
    bad data flow downstream into agent/decision-engine logic.
    """
    retries = settings.llm_max_retries if max_retries is None else max_retries
    structured_llm = llm.with_structured_output(output_model)

    last_error: Exception | None = None
    for attempt in range(1, retries + 2):  # +1 so "2 retries" means 3 total attempts
        try:
            result = structured_llm.invoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ]
            )
            if not isinstance(result, output_model):
                result = output_model.model_validate(result)
            return result
        except (ValidationError, ValueError, TypeError) as exc:
            last_error = exc
            logger.warning(
                "generate_structured: attempt %d/%d failed validating %s: %s",
                attempt, retries + 1, output_model.__name__, exc,
            )
            time.sleep(min(attempt, 3))  # small, capped backoff

    logger.error("generate_structured: giving up after %d attempts for %s", retries + 1, output_model.__name__)
    raise RuntimeError(
        f"LLM failed to return valid {output_model.__name__} after {retries + 1} attempts: {last_error}"
    )


def generate_text(
    llm: BaseChatModel,
    system_prompt: str,
    user_message: str,
) -> str:
    """Call the LLM and return raw text string response (used for Markdown reports)."""
    response = llm.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
    )
    return str(response.content)