"""
Unit tests for the Coach Agent (Phase 8).

Tests final Markdown report generation, prompt formatting, and heading validation with mocked LLM outputs.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agents.coach import format_full_transcript_and_evaluations, generate_coaching_report
from models.candidate import CandidateProfile, FocusArea
from models.evaluation import AnswerStatus, DifficultyAdjustment, EvaluationResult, RecommendedAction
from models.interview_plan import InterviewStrategy
from models.interview_state import InterviewState, InterviewStatus
from models.interview_turn import InterviewerQuestion, InterviewTurn, QuestionType

REQUIRED_HEADINGS = [
    "# Interview Feedback",
    "## Overall Assessment",
    "## Overall Score",
    "## Dimension-wise Performance",
    "## Strengths",
    "## Key Gaps",
    "## Evidence From Your Answers",
    "## Priority Practice Plan",
    "## Example Improvement Approach",
    "## Suggested Focus for Your Next Session",
]


@pytest.fixture
def sample_state() -> InterviewState:
    candidate = CandidateProfile(
        target_role="Software Engineer",
        background="CS student with Python experience",
        focus_area=FocusArea.TECHNICAL,
    )
    strategy = InterviewStrategy(
        role_summary="Entry-level software engineer",
        competencies=["Data Structures", "Algorithms"],
        initial_difficulty=2,
        topics=["Arrays", "Trees"],
        evaluation_dimensions=["technical_correctness", "clarity"],
    )
    question = InterviewerQuestion(
        question="How do you invert a Binary Tree?",
        question_type=QuestionType.OPENING,
        topic="Trees",
        difficulty=2,
    )
    evaluation = EvaluationResult(
        dimension_scores={"technical_correctness": 4.0, "clarity": 4.5},
        overall_score=4.25,
        overall_level="adequate",
        strengths=["Clear recursion approach"],
        weaknesses=["Did not mention space complexity"],
        answer_status=AnswerStatus.ADEQUATE,
        recommended_action=RecommendedAction.MOVE_ON,
        follow_up_focus="",
        difficulty_adjustment=DifficultyAdjustment.MAINTAIN,
    )
    turn = InterviewTurn(
        turn_number=1,
        question=question,
        answer="I would swap the left and right children recursively.",
        evaluation=evaluation,
    )
    return InterviewState(
        candidate=candidate,
        strategy=strategy,
        transcript=[turn],
        current_turn=1,
        max_turns=5,
        status=InterviewStatus.COMPLETED,
    )


def test_format_full_transcript_and_evaluations(sample_state: InterviewState):
    """Test formatting transcript and evaluations for Coach prompt."""
    res = format_full_transcript_and_evaluations(sample_state)
    assert "Turn 1" in res
    assert "How do you invert a Binary Tree?" in res
    assert "swap the left and right children" in res
    assert "Overall score: 4.2/5.0" in res


@patch("agents.coach.get_llm")
@patch("agents.coach.generate_text")
def test_generate_coaching_report(
    mock_gen_text: MagicMock,
    mock_get_llm: MagicMock,
    sample_state: InterviewState,
):
    """Test generate_coaching_report produces Markdown report with required headers."""
    sample_report = (
        "# Interview Feedback\n\n"
        "## Overall Assessment\nGood performance overall.\n\n"
        "## Overall Score\nScore: 4.2 / 5.0\n\n"
        "## Dimension-wise Performance\n- Technical Correctness: 4.0\n\n"
        "## Strengths\n- Clear recursion\n\n"
        "## Key Gaps\n- Missed space complexity\n\n"
        "## Evidence From Your Answers\nCandidate said: 'swap left and right'\n\n"
        "## Priority Practice Plan\n- Practice tree space complexity\n\n"
        "## Example Improvement Approach\nMention call stack depth O(h).\n\n"
        "## Suggested Focus for Your Next Session\nGraph traversals\n"
    )
    mock_gen_text.return_value = sample_report

    report = generate_coaching_report(sample_state)

    for heading in REQUIRED_HEADINGS:
        assert heading in report, f"Missing required heading: {heading}"

    mock_gen_text.assert_called_once()
