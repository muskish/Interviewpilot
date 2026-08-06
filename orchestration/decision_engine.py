"""
Decision Engine — deterministic orchestrator routing logic for InterviewPilot.

Controls interview turn transitions, difficulty scaling, topic changes, probing limits,
and turn limits without calling any LLM API.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from models.evaluation import AnswerStatus, DifficultyAdjustment, EvaluationResult, RecommendedAction
from models.interview_plan import DIFFICULTY_MAX, DIFFICULTY_MIN, InterviewStrategy
from models.interview_state import InterviewState, InterviewStatus
from utils.logger import get_logger

logger = get_logger(__name__)

MAX_CONSECUTIVE_PROBES = 2


class DecisionResult(BaseModel):
    """Output of the deterministic decision engine for a single turn transition."""

    next_action: RecommendedAction
    next_difficulty: int = Field(..., ge=DIFFICULTY_MIN, le=DIFFICULTY_MAX)
    next_topic: str
    is_complete: bool = False
    reasoning: str = Field(..., description="Brief explanation of why this decision was made.")


def select_next_topic(state: InterviewState, move_on: bool = True) -> str:
    """Select the next topic from strategy.topics or retain current topic."""
    if not state.strategy or not state.strategy.topics:
        return state.current_topic or "General"

    topics = state.strategy.topics
    if not state.current_topic or state.current_topic not in topics:
        return topics[0]

    if move_on:
        current_idx = topics.index(state.current_topic)
        next_idx = (current_idx + 1) % len(topics)
        return topics[next_idx]

    return state.current_topic


def count_consecutive_probes(state: InterviewState, current_topic: str) -> int:
    """Count how many consecutive past turns probed on the given topic."""
    count = 0
    for turn in reversed(state.transcript):
        if turn.question.topic == current_topic and turn.evaluation:
            if turn.evaluation.recommended_action in (
                RecommendedAction.PROBE_DEEPER,
                RecommendedAction.CLARIFY,
            ):
                count += 1
            else:
                break
        else:
            break
    return count


def process_turn_decision(
    state: InterviewState, evaluation: EvaluationResult | None = None
) -> DecisionResult:
    """
    Deterministically decide the next action, difficulty, topic, and completion state.

    Args:
        state: The active InterviewState.
        evaluation: The EvaluationResult of the candidate's latest turn, if available.

    Returns:
        DecisionResult containing next_action, next_difficulty, next_topic, and is_complete.
    """
    # 1. Turn limit check
    if state.current_turn >= state.max_turns or state.status == InterviewStatus.ENDED_EARLY:
        logger.info(
            "Decision Engine: interview complete (turn=%d/%d, status=%s)",
            state.current_turn,
            state.max_turns,
            state.status.value,
        )
        return DecisionResult(
            next_action=RecommendedAction.MOVE_ON,
            next_difficulty=state.current_difficulty,
            next_topic=state.current_topic or "General",
            is_complete=True,
            reasoning=f"Reached turn limit ({state.current_turn}/{state.max_turns}) or early exit.",
        )

    # 2. Fallback if evaluation is missing
    if evaluation is None:
        logger.warning("Decision Engine: no evaluation provided, defaulting to MOVE_ON")
        next_topic = select_next_topic(state, move_on=True)
        return DecisionResult(
            next_action=RecommendedAction.MOVE_ON,
            next_difficulty=state.current_difficulty,
            next_topic=next_topic,
            is_complete=False,
            reasoning="No evaluation result provided; defaulting to move on.",
        )

    # 3. Difficulty adjustment with strict clamping [1, 5]
    next_diff = state.current_difficulty
    if evaluation.difficulty_adjustment == DifficultyAdjustment.INCREASE:
        next_diff = min(DIFFICULTY_MAX, state.current_difficulty + 1)
    elif evaluation.difficulty_adjustment == DifficultyAdjustment.DECREASE:
        next_diff = max(DIFFICULTY_MIN, state.current_difficulty - 1)

    # 4. Consecutive probing check to prevent infinite probing loops
    current_topic = state.current_topic or (
        state.strategy.topics[0] if state.strategy and state.strategy.topics else "General"
    )
    past_probes = count_consecutive_probes(state, current_topic)

    action = evaluation.recommended_action
    reasoning = f"Evaluator recommended action: {action.value}."

    if past_probes >= MAX_CONSECUTIVE_PROBES and action in (
        RecommendedAction.PROBE_DEEPER,
        RecommendedAction.CLARIFY,
    ):
        action = RecommendedAction.CHANGE_TOPIC
        reasoning = (
            f"Overrode probing action to CHANGE_TOPIC after {past_probes} consecutive probes "
            f"on topic '{current_topic}'."
        )

    # 5. Topic selection based on action
    if action in (
        RecommendedAction.PROBE_DEEPER,
        RecommendedAction.CLARIFY,
        RecommendedAction.REDIRECT,
        RecommendedAction.SIMPLIFY,
    ):
        next_topic = current_topic
    else:  # RecommendedAction.MOVE_ON, RecommendedAction.CHANGE_TOPIC
        next_topic = select_next_topic(state, move_on=True)

    logger.info(
        "Decision Engine verdict: action=%s diff=%d topic=%r complete=False (%s)",
        action.value,
        next_diff,
        next_topic,
        reasoning,
    )

    return DecisionResult(
        next_action=action,
        next_difficulty=next_diff,
        next_topic=next_topic,
        is_complete=False,
        reasoning=reasoning,
    )
