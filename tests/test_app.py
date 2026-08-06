"""
Unit tests for Streamlit UI helper and routing logic (Phase 9 & Priority 2 Analytics).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app import init_session_state, render_analytics_dashboard, reset_interview
from models.candidate import CandidateProfile, FocusArea
from models.evaluation import AnswerStatus, DifficultyAdjustment, EvaluationResult, RecommendedAction
from models.interview_state import InterviewState, InterviewStatus
from models.interview_turn import InterviewerQuestion, InterviewTurn, QuestionType


@patch("streamlit.session_state", {})
def test_init_session_state():
    """Test initializing session state keys."""
    import streamlit as st
    init_session_state()
    assert "interview_state" in st.session_state
    assert st.session_state["interview_state"] is None


@patch("streamlit.rerun")
@patch("streamlit.session_state", {"interview_state": "some_state"})
def test_reset_interview(mock_rerun: MagicMock):
    """Test resetting interview state clears session state and reruns."""
    import streamlit as st
    reset_interview()
    assert st.session_state["interview_state"] is None
    mock_rerun.assert_called_once()


@patch("streamlit.bar_chart")
@patch("streamlit.line_chart")
@patch("streamlit.metric")
@patch("streamlit.markdown")
def test_render_analytics_dashboard_with_data(
    mock_markdown: MagicMock,
    mock_metric: MagicMock,
    mock_line_chart: MagicMock,
    mock_bar_chart: MagicMock,
):
    """Test render_analytics_dashboard renders metrics and charts when evaluations exist."""
    candidate = CandidateProfile(target_role="Data Engineer", focus_area=FocusArea.TECHNICAL)
    q1 = InterviewerQuestion(question="Q1", question_type=QuestionType.OPENING, topic="SQL", difficulty=2)
    e1 = EvaluationResult(
        dimension_scores={"clarity": 4.0, "technical_correctness": 5.0},
        overall_score=4.5,
        overall_level="strong",
        strengths=["Good syntax"],
        weaknesses=[],
        answer_status=AnswerStatus.STRONG,
        recommended_action=RecommendedAction.MOVE_ON,
        follow_up_focus="",
        difficulty_adjustment=DifficultyAdjustment.INCREASE,
    )
    turn1 = InterviewTurn(turn_number=1, question=q1, answer="A1", evaluation=e1)

    state = InterviewState(
        candidate=candidate,
        transcript=[turn1],
        max_turns=3,
        status=InterviewStatus.COMPLETED,
    )

    render_analytics_dashboard(state)

    assert mock_markdown.call_count >= 1
    assert mock_metric.call_count == 3
    mock_line_chart.assert_called_once()
    mock_bar_chart.assert_called_once()


@patch("streamlit.info")
def test_render_analytics_dashboard_empty(mock_info: MagicMock):
    """Test render_analytics_dashboard shows info box when no evaluation data exists."""
    candidate = CandidateProfile(target_role="Data Engineer", focus_area=FocusArea.TECHNICAL)
    state = InterviewState(candidate=candidate, transcript=[], max_turns=3)

    render_analytics_dashboard(state)

    mock_info.assert_called_once_with("No evaluation data available to chart.")
