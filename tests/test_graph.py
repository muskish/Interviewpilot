"""
Unit tests for LangGraph Workflow Orchestration (Phase 7).

Tests end-to-end multi-agent orchestration flows with mocked LLM calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from models.candidate import CandidateProfile, FocusArea
from models.evaluation import AnswerStatus, DifficultyAdjustment, EvaluationResult, RecommendedAction
from models.interview_plan import InterviewStrategy
from models.interview_state import InterviewState, InterviewStatus
from models.interview_turn import InterviewerQuestion, QuestionType
from orchestration.graph import run_answer_turn, run_start_interview


@pytest.fixture
def candidate_profile() -> CandidateProfile:
    return CandidateProfile(
        target_role="Data Analyst",
        background="Experience with SQL and Python",
        focus_area=FocusArea.TECHNICAL,
    )


@pytest.fixture
def sample_strategy() -> InterviewStrategy:
    return InterviewStrategy(
        role_summary="Data Analyst role",
        competencies=["SQL", "Python", "Data Viz"],
        initial_difficulty=2,
        topics=["SQL Queries", "Data Cleaning"],
        evaluation_dimensions=["technical_correctness", "clarity"],
    )


@pytest.fixture
def sample_question() -> InterviewerQuestion:
    return InterviewerQuestion(
        question="How do you perform a LEFT JOIN in SQL?",
        question_type=QuestionType.OPENING,
        topic="SQL Queries",
        difficulty=2,
    )


@pytest.fixture
def sample_evaluation() -> EvaluationResult:
    return EvaluationResult(
        dimension_scores={"technical_correctness": 4.5, "clarity": 4.0},
        overall_score=4.2,
        overall_level="strong",
        strengths=["Clear syntax explanation"],
        weaknesses=[],
        answer_status=AnswerStatus.STRONG,
        recommended_action=RecommendedAction.MOVE_ON,
        follow_up_focus="",
        difficulty_adjustment=DifficultyAdjustment.INCREASE,
    )


@patch("orchestration.graph.generate_question")
@patch("orchestration.graph.create_strategy")
def test_run_start_interview(
    mock_create_strat: MagicMock,
    mock_gen_q: MagicMock,
    candidate_profile: CandidateProfile,
    sample_strategy: InterviewStrategy,
    sample_question: InterviewerQuestion,
):
    """Test initializing a new interview session."""
    mock_create_strat.return_value = sample_strategy
    mock_gen_q.return_value = sample_question

    state = run_start_interview(candidate_profile)

    assert state.status == InterviewStatus.IN_PROGRESS
    assert state.strategy == sample_strategy
    assert state.current_topic == "SQL Queries"
    assert state.current_difficulty == 2
    assert state.current_question == sample_question
    assert state.current_turn == 0
    assert len(state.transcript) == 0


@patch("orchestration.graph.generate_question")
@patch("orchestration.graph.evaluate_answer")
def test_run_answer_turn_continues(
    mock_eval: MagicMock,
    mock_gen_q: MagicMock,
    candidate_profile: CandidateProfile,
    sample_strategy: InterviewStrategy,
    sample_question: InterviewerQuestion,
    sample_evaluation: EvaluationResult,
):
    """Test submitting an answer and generating the next question."""
    initial_state = InterviewState(
        candidate=candidate_profile,
        strategy=sample_strategy,
        current_turn=0,
        max_turns=5,
        current_topic="SQL Queries",
        current_difficulty=2,
        current_question=sample_question,
        status=InterviewStatus.IN_PROGRESS,
    )

    next_question = InterviewerQuestion(
        question="What is the difference between WHERE and HAVING?",
        question_type=QuestionType.NEW_TOPIC,
        topic="Data Cleaning",
        difficulty=3,
    )

    mock_eval.return_value = sample_evaluation
    mock_gen_q.return_value = next_question

    updated_state = run_answer_turn(initial_state, "A LEFT JOIN returns all rows from left table...")

    assert updated_state.current_turn == 1
    assert len(updated_state.transcript) == 1
    assert updated_state.transcript[0].answer == "A LEFT JOIN returns all rows from left table..."
    assert updated_state.transcript[0].evaluation == sample_evaluation
    assert updated_state.current_difficulty == 3  # Increased by 1 due to strong answer
    assert updated_state.status == InterviewStatus.IN_PROGRESS
    assert updated_state.current_question == next_question


@patch("orchestration.graph.generate_question")
@patch("orchestration.graph.evaluate_answer")
def test_run_answer_turn_completes_at_max_turns(
    mock_eval: MagicMock,
    mock_gen_q: MagicMock,
    candidate_profile: CandidateProfile,
    sample_strategy: InterviewStrategy,
    sample_question: InterviewerQuestion,
    sample_evaluation: EvaluationResult,
):
    """Test submitting the final turn answer marks interview COMPLETED."""
    initial_state = InterviewState(
        candidate=candidate_profile,
        strategy=sample_strategy,
        current_turn=4,  # Next turn will be 5 == max_turns
        max_turns=5,
        current_topic="SQL Queries",
        current_difficulty=2,
        current_question=sample_question,
        status=InterviewStatus.IN_PROGRESS,
    )

    mock_eval.return_value = sample_evaluation

    updated_state = run_answer_turn(initial_state, "Final turn answer.")

    assert updated_state.current_turn == 5
    assert updated_state.status == InterviewStatus.COMPLETED
    assert updated_state.current_question is None
