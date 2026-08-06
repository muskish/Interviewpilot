"""
LangGraph Workflow Orchestrator for InterviewPilot.

Uses typed shared state (InterviewState) to coordinate Strategist,
Interviewer, Evaluator, and Decision Engine nodes.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from agents.coach import generate_coaching_report
from agents.evaluator import evaluate_answer
from agents.interviewer import generate_question
from agents.strategist import create_strategy
from models.candidate import CandidateProfile
from models.evaluation import EvaluationResult, RecommendedAction
from models.interview_state import InterviewState, InterviewStatus
from models.interview_turn import InterviewTurn
from orchestration.decision_engine import process_turn_decision
from services.session_service import save_session
from utils.logger import get_logger

logger = get_logger(__name__)


# --- Node functions for LangGraph StateGraph ---

def strategist_node(state: InterviewState) -> dict[str, Any]:
    """LangGraph node: generate interview strategy."""
    logger.info("LangGraph Node [Strategist]: generating strategy")
    strategy = create_strategy(state.candidate)
    return {
        "strategy": strategy,
        "current_topic": strategy.topics[0] if strategy.topics else "General",
        "current_difficulty": strategy.initial_difficulty,
        "status": InterviewStatus.IN_PROGRESS,
    }


def generate_question_node(state: InterviewState) -> dict[str, Any]:
    """LangGraph node: generate next question."""
    logger.info("LangGraph Node [Interviewer]: generating question")
    action = state.next_action or RecommendedAction.MOVE_ON
    topic = state.current_topic or (state.strategy.topics[0] if state.strategy and state.strategy.topics else "General")
    difficulty = state.current_difficulty

    latest_eval = state.transcript[-1].evaluation if state.transcript else None

    question = generate_question(
        state=state,
        action=action,
        target_topic=topic,
        target_difficulty=difficulty,
        latest_evaluation=latest_eval,
    )
    return {"current_question": question}


def decision_engine_node(state: InterviewState) -> dict[str, Any]:
    """LangGraph node: run decision engine routing."""
    logger.info("LangGraph Node [Decision Engine]: computing next step")
    latest_eval = state.transcript[-1].evaluation if state.transcript else None
    decision = process_turn_decision(state, latest_eval)

    new_status = state.status
    if decision.is_complete or state.current_turn >= state.max_turns:
        new_status = InterviewStatus.COMPLETED

    return {
        "next_action": decision.next_action,
        "current_difficulty": decision.next_difficulty,
        "current_topic": decision.next_topic,
        "status": new_status,
    }


def coach_node(state: InterviewState) -> dict[str, Any]:
    """LangGraph node: generate final coaching report."""
    logger.info("LangGraph Node [Coach]: generating final report")
    report = generate_coaching_report(state)
    return {"final_report": report}


def should_continue(state: InterviewState) -> str:
    """Conditional edge router."""
    if state.status == InterviewStatus.COMPLETED or state.current_turn >= state.max_turns:
        return "complete"
    return "continue"


# --- Build LangGraph StateGraph ---
workflow = StateGraph(InterviewState)

workflow.add_node("strategist", strategist_node)
workflow.add_node("interviewer", generate_question_node)
workflow.add_node("decision_engine", decision_engine_node)
workflow.add_node("coach", coach_node)

workflow.add_edge(START, "strategist")
workflow.add_edge("strategist", "interviewer")
workflow.add_edge("interviewer", END)  # Pauses for candidate answer in Streamlit UI
workflow.add_edge("coach", END)

workflow.add_conditional_edges(
    "decision_engine",
    should_continue,
    {
        "continue": "interviewer",
        "complete": "coach",
    },
)

interview_graph = workflow.compile()


# --- Application Service Wrappers for Interactive Streamlit Flow ---

def run_start_interview(candidate: CandidateProfile) -> InterviewState:
    """
    Start a new interview session:
    1. Create candidate profile & strategy.
    2. Generate 1st question.
    3. Return initial state ready for candidate answer.
    """
    logger.info("Application Service: starting new interview for role=%r", candidate.target_role)
    initial_state = InterviewState(
        candidate=candidate,
        status=InterviewStatus.NOT_STARTED,
    )
    strategy = create_strategy(candidate)
    initial_state.strategy = strategy
    initial_state.current_topic = strategy.topics[0] if strategy.topics else "General"
    initial_state.current_difficulty = strategy.initial_difficulty
    initial_state.status = InterviewStatus.IN_PROGRESS

    question = generate_question(
        state=initial_state,
        action=RecommendedAction.MOVE_ON,
        target_topic=initial_state.current_topic,
        target_difficulty=initial_state.current_difficulty,
        latest_evaluation=None,
    )
    initial_state.current_question = question
    return initial_state


def run_answer_turn(state: InterviewState, answer: str) -> InterviewState:
    """
    Process candidate answer for current turn:
    1. Score answer with Evaluator.
    2. Append turn to transcript and increment turn count.
    3. Run Decision Engine.
    4. If not complete, generate next question; else generate Coach report, save session, and mark COMPLETED.
    """
    if not state.current_question:
        raise ValueError("Cannot submit answer when there is no active current_question.")

    logger.info("Application Service: processing answer for turn %d", state.current_turn + 1)

    # 1. Evaluate answer
    eval_result = evaluate_answer(
        question=state.current_question,
        answer=answer,
        target_role=state.candidate.target_role,
        focus_area=state.candidate.focus_area.value,
        strategy=state.strategy,
    )

    # 2. Add turn to transcript
    new_turn_num = state.current_turn + 1
    turn = InterviewTurn(
        turn_number=new_turn_num,
        question=state.current_question,
        answer=answer,
        evaluation=eval_result,
    )
    state.transcript.append(turn)
    state.current_turn = new_turn_num

    # 3. Decision Engine
    decision = process_turn_decision(state, eval_result)
    state.next_action = decision.next_action
    state.current_difficulty = decision.next_difficulty
    state.current_topic = decision.next_topic

    if decision.is_complete or state.current_turn >= state.max_turns:
        logger.info("Application Service: interview completed at turn %d, generating coach report", state.current_turn)
        state.status = InterviewStatus.COMPLETED
        state.current_question = None
        state.final_report = generate_coaching_report(state)
        save_session(state)
    else:
        # 4. Generate next question
        next_q = generate_question(
            state=state,
            action=decision.next_action,
            target_topic=decision.next_topic,
            target_difficulty=decision.next_difficulty,
            latest_evaluation=eval_result,
        )
        state.current_question = next_q

    return state


