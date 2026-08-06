"""
Interviewer Agent — generates the next interview question.

Runs every turn to generate exactly one question (opening, follow-up, probe,
simplification, or redirect). Never coaches, reveals internal scores, or
asks multiple questions at once. See prompts/interviewer_prompt.txt for its contract.
"""

from __future__ import annotations

from models.evaluation import EvaluationResult, RecommendedAction
from models.interview_state import InterviewState
from models.interview_turn import InterviewerQuestion
from services.llm_service import generate_structured, get_llm
from services.rag_service import retrieve_question_context
from utils.logger import get_logger
from utils.prompt_loader import load_prompt

logger = get_logger(__name__)


def format_transcript(state: InterviewState) -> str:
    """Format previous Q&A turns for the LLM prompt."""
    if not state.transcript:
        return "(No prior questions — this is turn 1)"

    formatted_turns = []
    for turn in state.transcript:
        eval_info = ""
        if turn.evaluation:
            eval_info = (
                f" [Evaluated: status={turn.evaluation.answer_status.value}, "
                f"action={turn.evaluation.recommended_action.value}]"
            )
        formatted_turns.append(
            f"Turn {turn.turn_number}:\n"
            f"  Question ({turn.question.question_type.value}, topic='{turn.question.topic}', diff={turn.question.difficulty}): {turn.question.question}\n"
            f"  Candidate Answer: {turn.answer or '(no answer)'}{eval_info}"
        )
    return "\n\n".join(formatted_turns)


def generate_question(
    state: InterviewState,
    action: RecommendedAction,
    target_topic: str,
    target_difficulty: int,
    latest_evaluation: EvaluationResult | None = None,
) -> InterviewerQuestion:
    """Generate the next interview question based on current state and decision engine routing."""
    system_prompt = load_prompt("interviewer_prompt")

    eval_context = ""
    if latest_evaluation:
        eval_context = (
            f"Latest Evaluator Feedback:\n"
            f"  Answer Status: {latest_evaluation.answer_status.value}\n"
            f"  Follow-up Focus: {latest_evaluation.follow_up_focus or '(none)'}\n"
            f"  Identified Strengths: {', '.join(latest_evaluation.strengths) or 'None'}\n"
            f"  Identified Weaknesses: {', '.join(latest_evaluation.weaknesses) or 'None'}\n"
        )

    strategy_info = ""
    if state.strategy:
        strategy_info = (
            f"Interview Strategy:\n"
            f"  Role Summary: {state.strategy.role_summary}\n"
            f"  Competencies: {', '.join(state.strategy.competencies)}\n"
            f"  All Topics: {', '.join(state.strategy.topics)}\n"
        )

    # Retrieve RAG Question Seed from Question Bank
    rag_entry = retrieve_question_context(
        topic=target_topic,
        focus_area=state.candidate.focus_area.value,
        difficulty=target_difficulty,
    )
    rag_context = ""
    if rag_entry:
        rag_context = (
            f"Retrieved Question Seed (RAG Context):\n"
            f"  Seed Question: {rag_entry.get('seed_question')}\n"
            f"  Evaluation Rubric: {rag_entry.get('rubric')}\n"
            f"  Key Concepts: {', '.join(rag_entry.get('key_concepts', []))}\n\n"
        )

    user_message = (
        f"Target Role: {state.candidate.target_role}\n"
        f"Focus Area: {state.candidate.focus_area.value}\n"
        f"Candidate Background: {state.candidate.background or '(not provided)'}\n\n"
        f"{strategy_info}\n"
        f"{rag_context}"
        f"Turn Info: Turn {state.current_turn + 1} of max {state.max_turns}\n"
        f"Decision Engine Routing Instruction:\n"
        f"  Action: {action.value}\n"
        f"  Target Topic: {target_topic}\n"
        f"  Target Difficulty: {target_difficulty} (1-5 scale)\n\n"
        f"{eval_context}\n"
        f"Conversation History:\n"
        f"{format_transcript(state)}\n\n"
        f"Generate the next question now."
    )

    logger.info(
        "Interviewer: generating question for turn=%d action=%s topic=%r difficulty=%d",
        state.current_turn + 1,
        action.value,
        target_topic,
        target_difficulty,
    )
    llm = get_llm()
    question = generate_structured(
        llm=llm,
        system_prompt=system_prompt,
        user_message=user_message,
        output_model=InterviewerQuestion,
    )
    logger.info(
        "Interviewer: generated question type=%s topic=%r diff=%d",
        question.question_type.value,
        question.topic,
        question.difficulty,
    )
    return question
