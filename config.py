"""
Central, validated application configuration.

Everything the app needs from the environment (.env) is loaded and validated
here, once, so no other module reaches for os.getenv() directly. Import
`settings` wherever config is needed:

    from config import settings
    settings.llm_provider
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Provider = Literal["groq", "openai", "anthropic", "ollama"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: Provider = Field(default="groq")
    llm_model: str = Field(default="llama-3.1-8b-instant")
    llm_model_structured: str = Field(
        default="llama-3.1-8b-instant",
        description=(
            "Model used for structured-output calls (evaluator, strategist). "
            "Defaults to a lighter 8B model to reduce token quota pressure. "
            "Only applied when llm_provider='groq'; other providers fall back to llm_model."
        ),
    )
    llm_temperature: float = Field(default=0.4, ge=0.0, le=2.0)
    llm_max_retries: int = Field(default=2, ge=0, le=5)

    groq_api_key: str | None = Field(default=None)
    openai_api_key: str | None = Field(default=None)
    anthropic_api_key: str | None = Field(default=None)
    # Ollama runs locally; no key required.

    def resolved_api_key(self) -> str | None:
        """Return whichever API key matches the active provider (None for ollama)."""
        return {
            "groq": self.groq_api_key,
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
            "ollama": None,
        }[self.llm_provider]

    def require_api_key(self) -> str:
        """Fetch the active provider's API key, or raise a clear, actionable error."""
        if self.llm_provider == "ollama":
            return ""  # not applicable
        key = self.resolved_api_key()
        if not key:
            env_var = f"{self.llm_provider.upper()}_API_KEY"
            raise RuntimeError(
                f"LLM_PROVIDER is set to '{self.llm_provider}' but {env_var} is missing. "
                f"Set it in your .env file (see .env.example)."
            )
        return key


# Inject Streamlit Cloud Secrets into environment if running on Streamlit Cloud
try:
    import os
    import streamlit as st
    if hasattr(st, "secrets"):
        for k, v in st.secrets.items():
            if isinstance(v, (str, int, float, bool)):
                os.environ.setdefault(k.upper(), str(v))
except Exception:
    pass

settings = Settings()
