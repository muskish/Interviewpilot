"""
Interviewer Agent — generates context-aware, adaptive questions.

Takes the current InterviewState, Strategy, Conversation History, and the
Decision Engine's Routing Instruction (action, target_topic, target_difficulty),
and generates the single next question for the candidate.
"""
from __future__ import annotations

from models.evaluation import EvaluationResult, RecommendedAction
from models.interview_state import InterviewState
from models.interview_turn import InterviewerQuestion, QuestionType
from services.llm_service import generate_structured, get_llm
from utils.logger import get_logger
from utils.prompt_loader import load_prompt

logger = get_logger(__name__)


def format_transcript(state: InterviewState) -> str:
    """Format previous turns into a readable block for the LLM prompt."""
    if not state.transcript:
        return "(No questions answered yet — this is the opening turn.)"

    lines = []
    for turn in state.transcript:
        lines.append(f"Turn {turn.turn_number} [{turn.question.topic} | Diff {turn.question.difficulty}]:")
        lines.append(f"  Q: {turn.question.question}")
        lines.append(f"  A: {turn.answer}")
        if turn.evaluation:
            lines.append(
                f"  Eval: status={turn.evaluation.answer_status.value}, "
                f"score={turn.evaluation.overall_score:.1f}, "
                f"action={turn.evaluation.recommended_action.value}"
            )
        lines.append("")
    return "\n".join(lines).strip()


def generate_question(
    state: InterviewState,
    action: RecommendedAction,
    target_topic: str,
    target_difficulty: int,
    latest_evaluation: EvaluationResult | None = None,
) -> InterviewerQuestion:
    """
    Generate the next question based on candidate state and routing instruction.
    """
    system_prompt = load_prompt("interviewer_prompt")

    strategy_info = (
        f"Interview Plan:\n"
        f"  Competencies to test: {', '.join(state.strategy.competencies)}\n"
        f"  Topics pool: {', '.join(state.strategy.topics)}\n"
        if state.strategy
        else ""
    )

    eval_context = ""
    if latest_evaluation:
        eval_context = (
            f"Latest Evaluation of Candidate's Response:\n"
            f"  Answer Status: {latest_evaluation.answer_status.value}\n"
            f"  Follow-up Focus: {latest_evaluation.follow_up_focus or 'N/A'}\n"
            f"  Strengths: {', '.join(latest_evaluation.strengths) or 'None noted'}\n"
            f"  Weaknesses: {', '.join(latest_evaluation.weaknesses) or 'None noted'}\n"
        )

    # Question Bank RAG context lookup
    rag_context = ""
    if state.candidate and state.candidate.target_role:
        from services.rag_service import retrieve_relevant_questions
        rag_snippets = retrieve_relevant_questions(
            role=state.candidate.target_role,
            topic=target_topic,
            difficulty=target_difficulty,
            top_k=2,
        )
        if rag_snippets:
            rag_context = (
                f"RAG Question Bank Exemplars (Use for guidance/style):\n"
                f"{rag_snippets}\n\n"
            )

    target_role = state.candidate.target_role if state.candidate else "Software Engineer"
    user_message = (
        f"Target Role: {target_role}\n"
        f"Focus Area: {state.candidate.focus_area.value if state.candidate else 'technical'}\n"
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
    try:
        question = generate_structured(
            llm=llm,
            system_prompt=system_prompt,
            user_message=user_message,
            output_model=InterviewerQuestion,
        )
    except Exception as exc:
        logger.error("Interviewer failed to generate question via LLM, using fallback: %s", exc)
        q_type = QuestionType.OPENING if state.current_turn == 0 else QuestionType.CORE
        question = InterviewerQuestion(
            question=f"Could you explain your technical experience and key engineering principles when working with {target_topic}?",
            question_type=q_type,
            topic=target_topic,
            difficulty=target_difficulty,
            rationale="Fallback question generated to ensure uninterrupted session progress.",
        )

    logger.info(
        "Interviewer: generated question type=%s topic=%r diff=%d",
        question.question_type.value,
        question.topic,
        question.difficulty,
    )
    return question
