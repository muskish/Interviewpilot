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

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Provider = Literal["gemini", "groq", "openai", "anthropic", "ollama", "openrouter"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: Provider = Field(default="gemini")
    llm_model: str = Field(default="gemini-2.5-flash")
    llm_temperature: float = Field(default=0.4, ge=0.0, le=2.0)
    llm_max_retries: int = Field(default=2, ge=0, le=5)

    gemini_api_key: str | None = Field(default=None)
    google_api_key: str | None = Field(default=None)

    def resolved_api_key(self) -> str | None:
        """Return the active Gemini / Google API key."""
        import os
        key = self.gemini_api_key or self.google_api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        return key

    def require_api_key(self) -> str:
        """Fetch the Gemini API key, or raise a clear, actionable error."""
        key = self.resolved_api_key()
        if not key:
            raise RuntimeError(
                "GEMINI_API_KEY is missing. "
                "Please set GEMINI_API_KEY in your .env file or Streamlit Cloud Secrets."
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
