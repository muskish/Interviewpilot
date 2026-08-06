"""
Unit tests for the Interviewer Agent (Phase 6).

Tests prompt formatting and structured output parsing using mocked LLM responses.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agents.interviewer import format_transcript, generate_question
from models.candidate import CandidateProfile, FocusArea
from models.evaluation import AnswerStatus, DifficultyAdjustment, EvaluationResult, RecommendedAction
from models.interview_plan import InterviewStrategy
from models.interview_state import InterviewState, InterviewStatus
from models.interview_turn import InterviewerQuestion, InterviewTurn, QuestionType


@pytest.fixture
def sample_candidate() -> CandidateProfile:
    return CandidateProfile(
        target_role="Frontend Engineer",
        background="React and JS developer",
        focus_area=FocusArea.TECHNICAL,
    )


@pytest.fixture
def sample_strategy() -> InterviewStrategy:
    return InterviewStrategy(
        role_summary="Frontend engineer role",
        competencies=["JavaScript", "React"],
        initial_difficulty=2,
        topics=["React Hooks", "DOM Manipulation"],
        evaluation_dimensions=["technical_correctness", "clarity"],
    )


@pytest.fixture
def initial_state(sample_candidate: CandidateProfile, sample_strategy: InterviewStrategy) -> InterviewState:
    return InterviewState(
        candidate=sample_candidate,
        strategy=sample_strategy,
        current_turn=0,
        max_turns=5,
        current_topic="React Hooks",
        current_difficulty=2,
        status=InterviewStatus.IN_PROGRESS,
    )


def test_format_transcript_empty(initial_state: InterviewState):
    """Test format_transcript when transcript is empty."""
    res = format_transcript(initial_state)
    assert "(No prior questions — this is turn 1)" in res


def test_format_transcript_with_turns(initial_state: InterviewState):
    """Test format_transcript with past Q&A turns."""
    question = InterviewerQuestion(
        question="What is useEffect?",
        question_type=QuestionType.OPENING,
        topic="React Hooks",
        difficulty=2,
    )
    evaluation = EvaluationResult(
        dimension_scores={"clarity": 4.0},
        overall_score=4.0,
        overall_level="adequate",
        strengths=["Good response"],
        weaknesses=[],
        answer_status=AnswerStatus.ADEQUATE,
        recommended_action=RecommendedAction.MOVE_ON,
        follow_up_focus="",
        difficulty_adjustment=DifficultyAdjustment.MAINTAIN,
    )
    turn = InterviewTurn(
        turn_number=1,
        question=question,
        answer="It handles side effects in functional components.",
        evaluation=evaluation,
    )
    initial_state.transcript.append(turn)

    res = format_transcript(initial_state)
    assert "Turn 1:" in res
    assert "What is useEffect?" in res
    assert "It handles side effects" in res


@patch("agents.interviewer.get_llm")
@patch("agents.interviewer.generate_structured")
def test_generate_question_opening(
    mock_gen_struct: MagicMock,
    mock_get_llm: MagicMock,
    initial_state: InterviewState,
):
    """Test generating an opening question."""
    expected_q = InterviewerQuestion(
        question="Can you explain how state management works in React?",
        question_type=QuestionType.OPENING,
        topic="React Hooks",
        difficulty=2,
    )
    mock_gen_struct.return_value = expected_q

    q = generate_question(
        state=initial_state,
        action=RecommendedAction.MOVE_ON,
        target_topic="React Hooks",
        target_difficulty=2,
        latest_evaluation=None,
    )

    assert q.question == expected_q.question
    assert q.question_type == QuestionType.OPENING
    assert q.topic == "React Hooks"
    assert q.difficulty == 2
    mock_gen_struct.assert_called_once()


@patch("agents.interviewer.get_llm")
@patch("agents.interviewer.generate_structured")
def test_generate_question_follow_up(
    mock_gen_struct: MagicMock,
    mock_get_llm: MagicMock,
    initial_state: InterviewState,
):
    """Test generating a follow-up probing question."""
    eval_result = EvaluationResult(
        dimension_scores={"depth": 2.0},
        overall_score=2.5,
        overall_level="weak",
        strengths=[],
        weaknesses=["Lacks dependency array explanation"],
        answer_status=AnswerStatus.INCOMPLETE,
        recommended_action=RecommendedAction.PROBE_DEEPER,
        follow_up_focus="Ask about dependency array edge cases",
        difficulty_adjustment=DifficultyAdjustment.MAINTAIN,
    )

    expected_q = InterviewerQuestion(
        question="What happens if you omit the dependency array in useEffect?",
        question_type=QuestionType.FOLLOW_UP,
        topic="React Hooks",
        difficulty=2,
    )
    mock_gen_struct.return_value = expected_q

    q = generate_question(
        state=initial_state,
        action=RecommendedAction.PROBE_DEEPER,
        target_topic="React Hooks",
        target_difficulty=2,
        latest_evaluation=eval_result,
    )

    assert q.question_type == QuestionType.FOLLOW_UP
    assert q.question == expected_q.question
    mock_gen_struct.assert_called_once()
