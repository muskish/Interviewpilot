"""Loads agent system prompts from prompts/*.txt, cached after first read."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    """
    Load prompts/{name}.txt. `name` is the file stem, e.g. "strategist_prompt".

    Cached with lru_cache: prompt files don't change at runtime, and every
    agent call would otherwise re-read the same file from disk.
    """
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {path}. Expected prompts/{name}.txt to exist."
        )
    return path.read_text(encoding="utf-8").strip()