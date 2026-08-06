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
from typing import Any, TypeVar

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
    """Robustly extract and parse a JSON dict from raw LLM text using brace counting."""
    text = text.strip()

    # 1. Direct json loads if it's pure JSON
    try:
        res = json.loads(text)
        if isinstance(res, dict):
            return res
    except Exception:
        pass

    # 2. Extract content from markdown ```json ... ``` codeblock
    codeblock_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if codeblock_match:
        try:
            res = json.loads(codeblock_match.group(1).strip())
            if isinstance(res, dict):
                return res
        except Exception:
            pass

    # 3. Match outer opening '{' to corresponding closing '}' with string awareness
    start_idx = text.find("{")
    if start_idx != -1:
        brace_count = 0
        in_string = False
        escape = False
        for i in range(start_idx, len(text)):
            char = text[i]
            if escape:
                escape = False
                continue
            if char == "\\" and in_string:
                escape = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if not in_string:
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        candidate = text[start_idx : i + 1]
                        res = json.loads(candidate)
                        if isinstance(res, dict):
                            return res

    return json.loads(text)


def _normalize_dict_for_enums(data: Any) -> Any:
    """Recursively convert uppercase Enum values to lowercase for Pydantic enum matching."""
    if isinstance(data, dict):
        new_dict = {}
        for k, v in data.items():
            if isinstance(v, str) and v.isupper() and "_" in v:
                new_dict[k] = v.lower()
            elif isinstance(v, str) and v.isupper() and len(v) < 20:
                new_dict[k] = v.lower()
            elif isinstance(v, (dict, list)):
                new_dict[k] = _normalize_dict_for_enums(v)
            else:
                new_dict[k] = v
        return new_dict
    if isinstance(data, list):
        return [_normalize_dict_for_enums(x) for x in data]
    return data


def generate_structured(
    llm: BaseChatModel,
    system_prompt: str,
    user_message: str,
    output_model: type[T],
    max_retries: int | None = None,
) -> T:
    """
    Call the LLM and force its response into `output_model` (a Pydantic model).

    Uses a 3-tier fallback hierarchy with brace counting and enum normalization:
    1. LangChain structured output (tool-calling API)
    2. json_mode fallback (Groq JSON format)
    3. Text generation + brace-count JSON extraction + Pydantic schema validation
    """
    retries = settings.llm_max_retries if max_retries is None else max_retries
    last_error: Exception | None = None

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
                normalized = _normalize_dict_for_enums(result)
                return output_model.model_validate(normalized)
            if isinstance(result, str):
                parsed = _extract_json(result)
                normalized = _normalize_dict_for_enums(parsed)
                return output_model.model_validate(normalized)
        except Exception as exc:
            last_error = exc
            logger.warning("generate_structured: attempt %d/%d API call failed: %s", attempt, retries + 1, exc)

        # Tier 3: Direct text completion + brace counting fallback
        try:
            logger.info("generate_structured: attempting Tier 3 text completion fallback...")
            raw_text = generate_text(
                llm,
                system_prompt=system_prompt + "\nOUTPUT REQUIREMENT: Output strictly a single JSON object. No extra markdown, explanations, or commentary.",
                user_message=formatted_user_msg,
            )
            parsed_dict = _extract_json(raw_text)
            normalized_dict = _normalize_dict_for_enums(parsed_dict)
            validated = output_model.model_validate(normalized_dict)
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