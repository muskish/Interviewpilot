"""
Unit tests for the deterministic Decision Engine (Phase 5).

Tests all routing rules, difficulty bounds, topic switching, infinite probe prevention,
turn limits, and fallback behavior without calling any LLM API.
"""

from __future__ import annotations

import pytest

from models.candidate import CandidateProfile, FocusArea
from models.evaluation import AnswerStatus, DifficultyAdjustment, EvaluationResult, RecommendedAction
from models.interview_plan import InterviewStrategy
from models.interview_state import InterviewState, InterviewStatus
from models.interview_turn import InterviewerQuestion, InterviewTurn, QuestionType
from orchestration.decision_engine import (
    MAX_CONSECUTIVE_PROBES,
    DecisionResult,
    count_consecutive_probes,
    process_turn_decision,
    select_next_topic,
)


@pytest.fixture
def sample_candidate() -> CandidateProfile:
    return CandidateProfile(
        target_role="Frontend Engineer",
        background="2 years experience with React and JS",
        focus_area=FocusArea.TECHNICAL,
    )


@pytest.fixture
def sample_strategy() -> InterviewStrategy:
    return InterviewStrategy(
        role_summary="Entry-level frontend engineer",
        competencies=["JavaScript", "React", "State Management"],
        initial_difficulty=3,
        topics=["React Basics", "State Management", "Performance Optimization"],
        evaluation_dimensions=["technical_correctness", "clarity", "depth"],
    )


@pytest.fixture
def initial_state(sample_candidate: CandidateProfile, sample_strategy: InterviewStrategy) -> InterviewState:
    return InterviewState(
        candidate=sample_candidate,
        strategy=sample_strategy,
        current_turn=1,
        max_turns=5,
        current_topic="React Basics",
        current_difficulty=3,
        status=InterviewStatus.IN_PROGRESS,
    )


def test_strong_answer_moves_on_and_increases_difficulty(initial_state: InterviewState):
    """Test 1: Strong answer moves on to next topic and increases difficulty."""
    eval_result = EvaluationResult(
        dimension_scores={"technical_correctness": 5.0, "clarity": 5.0},
        overall_score=5.0,
        overall_level="strong",
        strengths=["Clear explanation", "Solid React mental model"],
        weaknesses=[],
        answer_status=AnswerStatus.STRONG,
        recommended_action=RecommendedAction.MOVE_ON,
        follow_up_focus="",
        difficulty_adjustment=DifficultyAdjustment.INCREASE,
    )

    decision = process_turn_decision(initial_state, eval_result)

    assert decision.is_complete is False
    assert decision.next_action == RecommendedAction.MOVE_ON
    assert decision.next_difficulty == 4  # 3 -> 4
    assert decision.next_topic == "State Management"  # Moved to next topic in strategy


def test_weak_answer_triggers_probing(initial_state: InterviewState):
    """Test 2: Weak/vague answer triggers probing on the same topic."""
    eval_result = EvaluationResult(
        dimension_scores={"technical_correctness": 2.0, "clarity": 3.0},
        overall_score=2.5,
        overall_level="weak",
        strengths=[],
        weaknesses=["Vague response", "Lacks specific details"],
        answer_status=AnswerStatus.WEAK,
        recommended_action=RecommendedAction.PROBE_DEEPER,
        follow_up_focus="Ask for concrete state management example",
        difficulty_adjustment=DifficultyAdjustment.DECREASE,
    )

    decision = process_turn_decision(initial_state, eval_result)

    assert decision.is_complete is False
    assert decision.next_action == RecommendedAction.PROBE_DEEPER
    assert decision.next_difficulty == 2  # 3 -> 2
    assert decision.next_topic == "React Basics"  # Remains on current topic


def test_off_topic_triggers_redirect(initial_state: InterviewState):
    """Test 3: Off-topic answer triggers redirect back to current question."""
    eval_result = EvaluationResult(
        dimension_scores={"role_relevance": 1.0},
        overall_score=1.0,
        overall_level="off_topic",
        strengths=[],
        weaknesses=["Answer talked about unrelated backend database"],
        answer_status=AnswerStatus.OFF_TOPIC,
        recommended_action=RecommendedAction.REDIRECT,
        follow_up_focus="Redirect back to React Basics",
        difficulty_adjustment=DifficultyAdjustment.MAINTAIN,
    )

    decision = process_turn_decision(initial_state, eval_result)

    assert decision.is_complete is False
    assert decision.next_action == RecommendedAction.REDIRECT
    assert decision.next_difficulty == 3  # Maintains difficulty
    assert decision.next_topic == "React Basics"  # Remains on current topic


def test_i_dont_know_triggers_simplification(initial_state: InterviewState):
    """Test 4: Candidate saying 'I don't know' triggers simplification and lower difficulty."""
    eval_result = EvaluationResult(
        dimension_scores={"technical_depth": 1.0},
        overall_score=1.0,
        overall_level="no_answer",
        strengths=[],
        weaknesses=["Candidate stated they do not know"],
        answer_status=AnswerStatus.NO_ANSWER,
        recommended_action=RecommendedAction.SIMPLIFY,
        follow_up_focus="Reframe with basic foundational concept",
        difficulty_adjustment=DifficultyAdjustment.DECREASE,
    )

    decision = process_turn_decision(initial_state, eval_result)

    assert decision.is_complete is False
    assert decision.next_action == RecommendedAction.SIMPLIFY
    assert decision.next_difficulty == 2
    assert decision.next_topic == "React Basics"


def test_turn_limit_ends_interview(initial_state: InterviewState):
    """Test 5: Interview ends when current_turn reaches max_turns."""
    initial_state.current_turn = 5  # Max turns is 5

    eval_result = EvaluationResult(
        dimension_scores={"technical_correctness": 4.0},
        overall_score=4.0,
        overall_level="adequate",
        strengths=["Good response"],
        weaknesses=[],
        answer_status=AnswerStatus.ADEQUATE,
        recommended_action=RecommendedAction.MOVE_ON,
        follow_up_focus="",
        difficulty_adjustment=DifficultyAdjustment.MAINTAIN,
    )

    decision = process_turn_decision(initial_state, eval_result)

    assert decision.is_complete is True
    assert "Reached turn limit" in decision.reasoning


def test_infinite_probing_prevention(initial_state: InterviewState):
    """Test 6: Overrides PROBE_DEEPER to CHANGE_TOPIC after MAX_CONSECUTIVE_PROBES."""
    probe_eval = EvaluationResult(
        dimension_scores={"clarity": 2.0},
        overall_score=2.0,
        overall_level="incomplete",
        strengths=[],
        weaknesses=["Lacks depth"],
        answer_status=AnswerStatus.INCOMPLETE,
        recommended_action=RecommendedAction.PROBE_DEEPER,
        follow_up_focus="Probe further",
        difficulty_adjustment=DifficultyAdjustment.MAINTAIN,
    )

    question = InterviewerQuestion(
        question="Tell me about React hooks",
        question_type=QuestionType.FOLLOW_UP,
        topic="React Basics",
        difficulty=3,
    )

    # Add 2 consecutive probe turns to transcript
    initial_state.transcript = [
        InterviewTurn(turn_number=1, question=question, answer="Vague answer 1", evaluation=probe_eval),
        InterviewTurn(turn_number=2, question=question, answer="Vague answer 2", evaluation=probe_eval),
    ]

    # Current evaluation also recommends PROBE_DEEPER
    decision = process_turn_decision(initial_state, probe_eval)

    # Decision engine should override to CHANGE_TOPIC to prevent infinite probing
    assert decision.next_action == RecommendedAction.CHANGE_TOPIC
    assert decision.next_topic == "State Management"
    assert "Overrode probing action" in decision.reasoning


def test_difficulty_upper_bound_clamping(initial_state: InterviewState):
    """Test 7a: Difficulty cannot exceed max difficulty (5)."""
    initial_state.current_difficulty = 5

    eval_result = EvaluationResult(
        dimension_scores={"technical_correctness": 5.0},
        overall_score=5.0,
        overall_level="strong",
        strengths=["Perfect answer"],
        weaknesses=[],
        answer_status=AnswerStatus.STRONG,
        recommended_action=RecommendedAction.MOVE_ON,
        follow_up_focus="",
        difficulty_adjustment=DifficultyAdjustment.INCREASE,
    )

    decision = process_turn_decision(initial_state, eval_result)
    assert decision.next_difficulty == 5


def test_difficulty_lower_bound_clamping(initial_state: InterviewState):
    """Test 7b: Difficulty cannot drop below min difficulty (1)."""
    initial_state.current_difficulty = 1

    eval_result = EvaluationResult(
        dimension_scores={"technical_correctness": 1.0},
        overall_score=1.0,
        overall_level="weak",
        strengths=[],
        weaknesses=["Incorrect answer"],
        answer_status=AnswerStatus.INCORRECT,
        recommended_action=RecommendedAction.SIMPLIFY,
        follow_up_focus="",
        difficulty_adjustment=DifficultyAdjustment.DECREASE,
    )

    decision = process_turn_decision(initial_state, eval_result)
    assert decision.next_difficulty == 1


def test_missing_evaluation_fallback(initial_state: InterviewState):
    """Test 8: Missing evaluation result is handled safely with sensible defaults."""
    decision = process_turn_decision(initial_state, evaluation=None)

    assert decision.is_complete is False
    assert decision.next_action == RecommendedAction.MOVE_ON
    assert decision.next_difficulty == initial_state.current_difficulty
    assert decision.next_topic == "State Management"
    assert "No evaluation result provided" in decision.reasoning
