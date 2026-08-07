"""
Evaluator Agent — grades candidate answers on multiple dimensions.

Evaluates an answer on:
- technical_correctness (1-5)
- clarity (1-5)
- technical_depth (1-5)
- reasoning (1-5)
- relevance (1-5)

Produces an EvaluationResult with structured feedback, strengths, weaknesses,
and a recommended routing action for the Decision Engine.
"""
from __future__ import annotations

from models.evaluation import (
    AnswerStatus,
    DifficultyAdjustment,
    EvaluationResult,
    RecommendedAction,
)
from models.interview_plan import InterviewStrategy
from models.interview_turn import InterviewerQuestion
from utils.code_executor import extract_code_snippet, execute_code_snippet
from services.llm_service import generate_structured, get_llm_structured
from services.search_service import search_web
from utils.logger import get_logger
from utils.prompt_loader import load_prompt

logger = get_logger(__name__)


def evaluate_answer(
    target_role: str,
    focus_area: str,
    question: InterviewerQuestion,
    answer: str,
    strategy: InterviewStrategy,
) -> EvaluationResult:
    """Evaluate candidate's answer against question, role, and focus area with fallback."""
    # Deterministic Non-Answer Detection ("i dont know", "idk", skip, empty)
    clean_ans = answer.strip().lower() if answer else ""
    non_answer_triggers = (
        "i dont know", "i don't know", "dont know", "don't know", "idk", "idont know",
        "no idea", "not sure", "no clue", "pass", "skip", "no answer", "n/a", "none"
    )
    is_non_answer = (
        not clean_ans
        or clean_ans in non_answer_triggers
        or any(clean_ans.startswith(p) for p in ("i dont know", "i don't know", "idk", "no idea", "not sure"))
    )

    if is_non_answer:
        logger.info("Evaluator: detected explicit non-answer/skip, applying deterministic no_answer evaluation")
        dims = strategy.evaluation_dimensions if (strategy and strategy.evaluation_dimensions) else ["clarity", "technical_correctness"]
        return EvaluationResult(
            dimension_scores={dim: 1.0 for dim in dims},
            overall_score=1.0,
            overall_level="poor",
            strengths=[],
            weaknesses=["Candidate stated they do not know or skipped the question."],
            answer_status=AnswerStatus.NO_ANSWER,
            recommended_action=RecommendedAction.SIMPLIFY,
            follow_up_focus=f"Basic fundamentals of {question.topic}",
            difficulty_adjustment=DifficultyAdjustment.DECREASE,
            is_fallback=False,
        )

    system_prompt = load_prompt("evaluator_prompt")

    # Multi-Language Code Sandbox Execution
    sandbox_output = ""
    if answer:
        snippet = extract_code_snippet(answer)
        if snippet:
            exec_res = execute_code_snippet(snippet)
            if exec_res.executed:
                sandbox_output = (
                    f"\n[Multi-Language Code Sandbox Execution ({exec_res.language})]\n"
                    f"Stdout: {exec_res.stdout}\n"
                    f"Stderr: {exec_res.stderr}\n"
                    f"Linter Output: {exec_res.lint_report or 'clean'}\n"
                )

    # Autonomous Web Search Fact-Checking (Tool Use)
    search_context = ""
    if answer and len(answer.split()) > 5:
        search_query = f"{target_role} {question.topic} {answer[:60]}"
        search_snippets = search_web(search_query, max_results=2)
        if search_snippets:
            search_context = (
                f"\n[Live Web Search Fact-Check Context (DuckDuckGo Tool)]\n"
                f"The Evaluator ran a live web search for '{search_query[:50]}...':\n"
                f"{search_snippets}\n"
                "Use these live search results to verify candidate claims.\n"
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
        f"{search_context}\n"
        "Evaluate this answer now."
    )

    logger.info("Evaluator: scoring answer for topic=%r difficulty=%d", question.topic, question.difficulty)
    llm = get_llm_structured()
    try:
        result = generate_structured(
            llm=llm,
            system_prompt=system_prompt,
            user_message=user_message,
            output_model=EvaluationResult,
        )
    except Exception as exc:
        logger.error("Evaluator failed to grade answer via LLM, using fallback: %s", exc)
        result = EvaluationResult(
            dimension_scores={"clarity": 3.0, "technical_correctness": 3.0},
            overall_score=3.0,
            overall_level="adequate",
            strengths=["Candidate provided a structured response."],
            weaknesses=[],
            answer_status=AnswerStatus.ADEQUATE,
            recommended_action=RecommendedAction.MOVE_ON,
            follow_up_focus="Next topic area",
            difficulty_adjustment=DifficultyAdjustment.MAINTAIN,
            is_fallback=True,
        )

    # Post-Processing Guardrails: Enforce score and difficulty alignment consistency
    if result.answer_status == AnswerStatus.NO_ANSWER:
        result.overall_score = 1.0
        result.overall_level = "poor"
        result.difficulty_adjustment = DifficultyAdjustment.DECREASE
        result.recommended_action = RecommendedAction.SIMPLIFY
    elif result.answer_status in (AnswerStatus.WEAK, AnswerStatus.INCORRECT, AnswerStatus.OFF_TOPIC):
        result.overall_score = min(result.overall_score, 2.5)
        if result.overall_score < 2.0:
            result.overall_level = "poor"
        else:
            result.overall_level = "weak"
        if result.difficulty_adjustment == DifficultyAdjustment.INCREASE:
            result.difficulty_adjustment = DifficultyAdjustment.DECREASE
    elif result.answer_status == AnswerStatus.STRONG:
        if result.overall_score < 3.8:
            result.overall_score = 4.0
        result.overall_level = "strong"

    logger.info(
        "Evaluator: status=%s action=%s overall_score=%.1f diff_adj=%s",
        result.answer_status.value,
        result.recommended_action.value,
        result.overall_score,
        result.difficulty_adjustment.value,
    )
    return result