"""
The single shared state object that flows through the LangGraph workflow
and mirrors into st.session_state. This is the source of truth for
"where is this interview right now."
"""

from __future__ import annotations

import uuid
from enum import Enum

from pydantic import BaseModel, Field

from models.candidate import CandidateProfile
from models.evaluation import RecommendedAction
from models.interview_plan import DIFFICULTY_MIN, InterviewStrategy
from models.interview_turn import InterviewerQuestion, InterviewTurn

MIN_TURNS = 5
MAX_TURNS = 7


class InterviewStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ENDED_EARLY = "ended_early"


class InterviewState(BaseModel):
    session_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])

    candidate: CandidateProfile
    strategy: InterviewStrategy | None = None

    transcript: list[InterviewTurn] = Field(default_factory=list)

    current_turn: int = 0
    max_turns: int = MAX_TURNS
    current_topic: str | None = None
    current_difficulty: int = DIFFICULTY_MIN

    next_action: RecommendedAction | None = None
    current_question: InterviewerQuestion | None = None

    enable_webcam: bool = False
    status: InterviewStatus = InterviewStatus.NOT_STARTED
    final_report: str | None = None
