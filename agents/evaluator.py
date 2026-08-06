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
from utils.code_executor import extract_python_code, execute_python_code
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

    # Optional Sandbox Execution (Tool Use)
    sandbox_output = ""
    if focus_area == "technical" and answer:
        code_block = extract_python_code(answer)
        if code_block:
            logger.info("Evaluator: Python code block detected. Executing sandbox...")
            exec_result = execute_python_code(code_block)
            sandbox_output = (
                "\n[Code Execution Sandbox Output]\n"
                "The candidate provided a Python code block. I executed it in a sandbox.\n"
                f"Execution Output (stdout): {exec_result.stdout or '(none)'}\n"
                f"Execution Errors (stderr): {exec_result.stderr or '(none)'}\n"
                f"Exit Code: {exec_result.exit_code}\n"
                f"Timed Out: {exec_result.timeout}\n"
                "Review these actual execution results when determining your score.\n"
            )

    user_message = (
        f"Target role: {target_role}\n"
        f"Focus area: {focus_area}\n"
        f"Current difficulty: {question.difficulty}\n"
        f"Evaluation dimensions to score (use exactly these keys): {strategy.evaluation_dimensions}\n\n"
        f"Question asked: {question.question}\n"
        f"Question topic: {question.topic}\n\n"
        f"Candidate's answer: {answer or '(no answer provided)'}\n"
        f"{sandbox_output}\n"
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