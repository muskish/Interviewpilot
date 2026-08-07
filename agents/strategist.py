"""
Strategist Agent — plans the interview before it starts.

Runs exactly once, before the first question. Turns (target_role, background,
focus_area) into a structured InterviewStrategy: competencies to probe,
topics to draw questions from, a starting difficulty, and which evaluation
dimensions matter for this focus area. Does not ask questions, evaluate
answers, or coach — see prompts/strategist_prompt.txt for its full contract.
"""
from __future__ import annotations

from models.candidate import CandidateProfile
from models.interview_plan import InterviewStrategy
from services.llm_service import generate_structured, get_llm_structured
from utils.logger import get_logger
from utils.prompt_loader import load_prompt

logger = get_logger(__name__)


def create_strategy(candidate: CandidateProfile) -> InterviewStrategy:
    """Generate a role-aware InterviewStrategy for this candidate with safe fallback."""
    system_prompt = load_prompt("strategist_prompt")

    user_message = (
        f"Target role: {candidate.target_role}\n"
        f"Focus area: {candidate.focus_area.value}\n"
        f"Candidate background: {candidate.background or '(not provided)'}\n"
        f"Job Description: {candidate.job_description or '(not provided)'}\n\n"
        "Create the interview strategy for this candidate."
    )

    logger.info("Strategist: planning for role=%r focus=%r", candidate.target_role, candidate.focus_area.value)
    llm = get_llm_structured()
    try:
        strategy = generate_structured(
            llm=llm,
            system_prompt=system_prompt,
            user_message=user_message,
            output_model=InterviewStrategy,
        )
    except Exception as exc:
        logger.error("Strategist failed to generate strategy via LLM, using fallback: %s", exc)
        strategy = InterviewStrategy(
            role_summary=f"Interview plan for {candidate.target_role}",
            competencies=[candidate.focus_area.value, "Problem Solving", "System Architecture"],
            initial_difficulty=2,
            topics=[candidate.target_role, candidate.focus_area.value, "System Design"],
            evaluation_dimensions=["technical_correctness", "clarity", "reasoning"],
        )

    logger.info(
        "Strategist: plan ready — %d competencies, %d topics, initial_difficulty=%d",
        len(strategy.competencies), len(strategy.topics), strategy.initial_difficulty,
    )
    return strategy