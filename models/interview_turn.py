"""A single question (Interviewer output) and a single completed Q&A turn."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from models.evaluation import EvaluationResult
from models.interview_plan import DIFFICULTY_MAX, DIFFICULTY_MIN


class QuestionType(str, Enum):
    OPENING = "opening"
    FOLLOW_UP = "follow_up"
    NEW_TOPIC = "new_topic"
    CLARIFICATION = "clarification"
    SIMPLIFIED = "simplified"


class InterviewerQuestion(BaseModel):
    question: str = Field(..., min_length=1)
    question_type: QuestionType
    topic: str
    difficulty: int = Field(..., ge=DIFFICULTY_MIN, le=DIFFICULTY_MAX)


class InterviewTurn(BaseModel):
    turn_number: int = Field(..., ge=1)
    question: InterviewerQuestion
    answer: str
    evaluation: EvaluationResult | None = Field(
        default=None, description="Populated once the Evaluator has scored this answer."
    )
