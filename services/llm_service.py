"""
Reusable, provider-agnostic LLM service.

Every agent talks to the LLM through this module only — no agent imports
langchain_groq/openai/anthropic/ollama directly. That's what makes
LLM_PROVIDER swappable via .env without touching agent code.
"""
from __future__ import annotations

import json
import re
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

    raise RuntimeError(f"Unknown LLM_PROVIDER: {provider}")


def _extract_json(text: str) -> dict:
    """Extract JSON object from markdown codeblock or raw text string."""
    # Search for ```json { ... } ``` block first
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    # Search for raw { ... }
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    return json.loads(text.strip())


def generate_structured(
    llm: BaseChatModel,
    system_prompt: str,
    user_message: str,
    output_model: type[T],
    max_retries: int | None = None,
) -> T:
    """
    Call the LLM and force its response into `output_model` (a Pydantic model).

    Uses a 3-tier fallback hierarchy:
    1. LangChain structured output (tool-calling API)
    2. json_mode fallback (Groq JSON format)
    3. Text generation + regex JSON extraction + Pydantic schema validation
    """
    retries = settings.llm_max_retries if max_retries is None else max_retries
    last_error: Exception | None = None

    # Guarantee "json" is present in user message for Groq json_mode compatibility
    formatted_user_msg = user_message
    if "json" not in formatted_user_msg.lower():
        try:
            schema_json = json.dumps(output_model.model_json_schema(), indent=2)
            formatted_user_msg += f"\n\nRespond strictly with a JSON object matching this schema:\n{schema_json}"
        except Exception:
            formatted_user_msg += "\n\nRespond strictly with a valid JSON object."

    for attempt in range(1, retries + 2):
        # Tier 1 & 2: Structured Output API
        try:
            if attempt == 1:
                structured_llm = llm.with_structured_output(output_model)
            else:
                structured_llm = llm.with_structured_output(output_model, method="json_mode")

            result = structured_llm.invoke(
                [
                    {"role": "system", "content": system_prompt + "\nYou must return valid json."},
                    {"role": "user", "content": formatted_user_msg},
                ]
            )
            if isinstance(result, output_model):
                return result
            if isinstance(result, dict):
                return output_model.model_validate(result)
            if isinstance(result, str):
                return output_model.model_validate(_extract_json(result))
        except Exception as exc:
            last_error = exc
            logger.warning("generate_structured: attempt %d/%d API call failed: %s", attempt, retries + 1, exc)

        # Tier 3: Direct text completion + regex extraction fallback
        try:
            logger.info("generate_structured: attempting Tier 3 text completion fallback...")
            raw_text = generate_text(
                llm,
                system_prompt=system_prompt + "\nOUTPUT REQUIREMENT: Output strictly a single JSON object. No extra markdown, explanations, or commentary.",
                user_message=formatted_user_msg,
            )
            parsed_dict = _extract_json(raw_text)
            validated = output_model.model_validate(parsed_dict)
            logger.info("generate_structured: Tier 3 fallback successfully parsed %s!", output_model.__name__)
            return validated
        except Exception as exc3:
            last_error = exc3
            logger.warning("generate_structured: Tier 3 fallback failed: %s", exc3)

        time.sleep(1)

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