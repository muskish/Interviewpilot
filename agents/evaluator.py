"""
Evaluator Agent — scores one candidate answer, in isolation.

Runs every turn, right after the candidate answers. Has no visibility into
what happens with its verdict — it does not ask questions, coach, or know
the interview's overall trajectory. See prompts/evaluator_prompt.txt for
its full contract, including messy-answer handling and routing rules.
"""
from __future__ import annotations

from models.evaluation import EvaluationResult
from models.interview_plan import InterviewStrategy
from models.interview_turn import InterviewerQuestion
from services.llm_service import generate_structured, get_llm
from utils.logger import get_logger
from utils.prompt_loader import load_prompt

logger = get_logger(__name__)


def evaluate_answer(
    question: InterviewerQuestion,
    answer: str,
    target_role: str,
    focus_area: str,
    strategy: InterviewStrategy,
) -> EvaluationResult:
    """Score one answer against the strategy's evaluation_dimensions."""
    system_prompt = load_prompt("evaluator_prompt")

    user_message = (
        f"Target role: {target_role}\n"
        f"Focus area: {focus_area}\n"
        f"Current difficulty: {question.difficulty}\n"
        f"Evaluation dimensions to score (use exactly these keys): {strategy.evaluation_dimensions}\n\n"
        f"Question asked: {question.question}\n"
        f"Question topic: {question.topic}\n\n"
        f"Candidate's answer: {answer or '(no answer provided)'}\n\n"
        "Evaluate this answer now."
    )

    logger.info("Evaluator: scoring answer for topic=%r difficulty=%d", question.topic, question.difficulty)
    llm = get_llm()
    result = generate_structured(
        llm=llm,
        system_prompt=system_prompt,
        user_message=user_message,
        output_model=EvaluationResult,
    )
    logger.info(
        "Evaluator: status=%s action=%s overall_score=%.1f",
        result.answer_status.value, result.recommended_action.value, result.overall_score,
    )
    return result