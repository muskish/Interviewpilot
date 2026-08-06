"""
Unit tests for JSON Session Storage (Phase 10).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from models.candidate import CandidateProfile, FocusArea
from models.evaluation import AnswerStatus, DifficultyAdjustment, EvaluationResult, RecommendedAction
from models.interview_plan import InterviewStrategy
from models.interview_state import InterviewState, InterviewStatus
from models.interview_turn import InterviewerQuestion, InterviewTurn, QuestionType
from services.session_service import list_saved_sessions, load_session, save_session


@pytest.fixture
def sample_state() -> InterviewState:
    candidate = CandidateProfile(
        target_role="Product Manager",
        background="APM with 1 year experience",
        focus_area=FocusArea.BEHAVIORAL,
    )
    strategy = InterviewStrategy(
        role_summary="Entry-level PM role",
        competencies=["Product Sense", "Leadership"],
        initial_difficulty=2,
        topics=["Prioritization", "Stakeholder Management"],
        evaluation_dimensions=["clarity", "relevance"],
    )
    question = InterviewerQuestion(
        question="Tell me about a time you prioritized features.",
        question_type=QuestionType.OPENING,
        topic="Prioritization",
        difficulty=2,
    )
    evaluation = EvaluationResult(
        dimension_scores={"clarity": 4.5, "relevance": 4.0},
        overall_score=4.25,
        overall_level="adequate",
        strengths=["Clear framework"],
        weaknesses=[],
        answer_status=AnswerStatus.ADEQUATE,
        recommended_action=RecommendedAction.MOVE_ON,
        follow_up_focus="",
        difficulty_adjustment=DifficultyAdjustment.MAINTAIN,
    )
    turn = InterviewTurn(
        turn_number=1,
        question=question,
        answer="I used the RICE framework to rank backlog items.",
        evaluation=evaluation,
    )
    return InterviewState(
        candidate=candidate,
        strategy=strategy,
        transcript=[turn],
        current_turn=1,
        max_turns=5,
        status=InterviewStatus.COMPLETED,
        final_report="# Interview Feedback\nGood job.",
    )


def test_save_and_load_session(sample_state: InterviewState, tmp_path: Path):
    """Test saving an InterviewState to JSON and loading it back."""
    saved_path = save_session(sample_state, sessions_dir=tmp_path)

    assert saved_path.exists()
    assert saved_path.name == f"{sample_state.session_id}.json"

    loaded_state = load_session(sample_state.session_id, sessions_dir=tmp_path)

    assert loaded_state.session_id == sample_state.session_id
    assert loaded_state.candidate.target_role == "Product Manager"
    assert loaded_state.current_turn == 1
    assert len(loaded_state.transcript) == 1
    assert loaded_state.transcript[0].question.question == "Tell me about a time you prioritized features."
    assert loaded_state.final_report == "# Interview Feedback\nGood job."


def test_list_saved_sessions(sample_state: InterviewState, tmp_path: Path):
    """Test listing saved session IDs."""
    save_session(sample_state, sessions_dir=tmp_path)
    session_ids = list_saved_sessions(sessions_dir=tmp_path)

    assert sample_state.session_id in session_ids


def test_load_non_existent_session_raises_error(tmp_path: Path):
    """Test attempting to load a non-existent session raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_session("non_existent_id_9999", sessions_dir=tmp_path)
