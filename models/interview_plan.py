"""Output of the Strategist agent: the plan the rest of the interview follows."""

from __future__ import annotations

from pydantic import BaseModel, Field

DIFFICULTY_MIN = 1
DIFFICULTY_MAX = 5


class InterviewStrategy(BaseModel):
    role_summary: str = Field(..., description="One-line framing of the role/level.")
    competencies: list[str] = Field(..., min_length=1, description="Skills this role requires.")
    initial_difficulty: int = Field(..., ge=DIFFICULTY_MIN, le=DIFFICULTY_MAX)
    topics: list[str] = Field(..., min_length=1, description="Topics to draw questions from.")
    evaluation_dimensions: list[str] = Field(
        ..., min_length=1, description="Dimensions the Evaluator should score against."
    )
