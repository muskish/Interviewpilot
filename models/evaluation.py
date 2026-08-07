"""Output of the Evaluator agent: a structured, multi-dimensional read on one answer."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class AnswerStatus(str, Enum):
    STRONG = "strong"
    ADEQUATE = "adequate"
    INCOMPLETE = "incomplete"
    WEAK = "weak"
    INCORRECT = "incorrect"
    OFF_TOPIC = "off_topic"
    NO_ANSWER = "no_answer"


class RecommendedAction(str, Enum):
    PROBE_DEEPER = "probe_deeper"
    CLARIFY = "clarify"
    MOVE_ON = "move_on"
    REDIRECT = "redirect"
    SIMPLIFY = "simplify"
    CHANGE_TOPIC = "change_topic"


class DifficultyAdjustment(str, Enum):
    INCREASE = "increase"
    MAINTAIN = "maintain"
    DECREASE = "decrease"


class EvaluationResult(BaseModel):
    dimension_scores: dict[str, float] = Field(
        ..., description="e.g. {'clarity': 4, 'depth': 2} on a 1-5 scale."
    )
    overall_score: float = Field(..., ge=0, le=5)
    overall_level: str = Field(..., description="e.g. 'strong', 'weak' — human-readable summary tier.")
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    answer_status: AnswerStatus
    recommended_action: RecommendedAction
    follow_up_focus: str = Field(..., description="What the Interviewer should probe next, if probing.")
    difficulty_adjustment: DifficultyAdjustment
    is_fallback: bool = Field(
        default=False,
        description="True when the LLM API was unavailable and a static fallback evaluation was used instead.",
    )
