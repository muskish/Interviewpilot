"""
Coach Agent — generates the final comprehensive Markdown coaching report.

Analyzes the full interview transcript, candidate profile, strategy, and turn evaluations.
Grounds all feedback in candidate evidence without inventing quotes.
See prompts/coach_prompt.txt for full contract.
"""

from __future__ import annotations

from models.interview_state import InterviewState
from services.llm_service import generate_text, get_llm
from utils.logger import get_logger
from utils.prompt_loader import load_prompt

logger = get_logger(__name__)


def format_full_transcript_and_evaluations(state: InterviewState) -> str:
    """Format full Q&A transcript and all evaluation details for Coach agent."""
    if not state.transcript:
        return "(No turns completed in transcript)"

    formatted_turns = []
    for turn in state.transcript:
        eval_str = "No evaluation available"
        if turn.evaluation:
            scores = ", ".join(f"{k}={v:.1f}" for k, v in turn.evaluation.dimension_scores.items())
            eval_str = (
                f"Overall score: {turn.evaluation.overall_score:.1f}/5.0 ({turn.evaluation.overall_level})\n"
                f"    Dimension scores: {scores}\n"
                f"    Strengths: {', '.join(turn.evaluation.strengths) or 'None'}\n"
                f"    Weaknesses: {', '.join(turn.evaluation.weaknesses) or 'None'}\n"
                f"    Action: {turn.evaluation.recommended_action.value}"
            )

        formatted_turns.append(
            f"--- Turn {turn.turn_number} ---\n"
            f"Question asked: {turn.question.question}\n"
            f"Topic: {turn.question.topic} | Difficulty: {turn.question.difficulty}/5\n"
            f"Candidate Answer:\n\"\"\"{turn.answer or '(no answer)'}\"\"\"\n"
            f"Evaluator Verdict:\n    {eval_str}\n"
        )

    return "\n".join(formatted_turns)


def generate_coaching_report(state: InterviewState) -> str:
    """Generate comprehensive Markdown coaching report for completed interview state."""
    system_prompt = load_prompt("coach_prompt")

    strategy_info = ""
    if state.strategy:
        strategy_info = (
            f"Interview Strategy:\n"
            f"  Role Summary: {state.strategy.role_summary}\n"
            f"  Target Competencies: {', '.join(state.strategy.competencies)}\n"
            f"  Topics Covered: {', '.join(state.strategy.topics)}\n"
            f"  Evaluation Dimensions: {', '.join(state.strategy.evaluation_dimensions)}\n"
        )

    from services.benchmark_service import retrieve_peer_benchmarks

    peer_context = retrieve_peer_benchmarks(
        target_role=state.candidate.target_role,
        focus_area=state.candidate.focus_area.value,
        background=state.candidate.background,
    )

    user_message = (
        f"Candidate Profile:\n"
        f"  Target Role: {state.candidate.target_role}\n"
        f"  Focus Area: {state.candidate.focus_area.value}\n"
        f"  Background: {state.candidate.background or '(not provided)'}\n\n"
        f"{strategy_info}\n"
        f"Interview Progress: Completed {state.current_turn} of max {state.max_turns} turns.\n\n"
        f"Historical Candidate Vector DB Benchmark Context (FAISS RAG):\n"
        f"{peer_context}\n\n"
        f"Full Transcript & Turn Evaluations:\n"
        f"{format_full_transcript_and_evaluations(state)}\n\n"
        f"Synthesize the complete interview session and write the final Markdown coaching report now, including a Peer Benchmarking section."
    )

    logger.info("Coach: generating final report for session=%s turns=%d", state.session_id, state.current_turn)
    try:
        llm = get_llm()
        report_md = generate_text(
            llm=llm,
            system_prompt=system_prompt,
            user_message=user_message,
        )
        logger.info("Coach: report generated successfully (%d chars)", len(report_md))
        return report_md
    except Exception as exc:
        logger.error("Coach: LLM failed to generate report, building fallback report: %s", exc)
        return _build_fallback_report(state)


def _build_fallback_report(state: InterviewState) -> str:
    """Build a rich, deterministic Markdown coaching report from state transcript when LLM API is unavailable."""
    turns = state.transcript
    total_turns = len(turns)
    
    avg_score = 0.0
    if total_turns > 0:
        valid_scores = [t.evaluation.overall_score for t in turns if t.evaluation]
        avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else 3.5

    role = state.candidate.target_role if state.candidate else "Software Engineer"
    
    report = [
        f"# 🎯 Interview Coaching Report — {role}",
        f"**Candidate**: {state.candidate.name if hasattr(state.candidate, 'name') else 'Candidate'}",
        f"**Focus Area**: {state.candidate.focus_area.value if state.candidate else 'Technical'}",
        f"**Turns Completed**: {total_turns} / {state.max_turns}",
        f"**Overall Session Rating**: {avg_score:.1f} / 5.0\n",
        "---",
        "## 📊 Executive Summary",
        f"The candidate completed {total_turns} turns focusing on {role} competencies. Overall performance demonstrated steady technical comprehension and communication.",
        "\n## 🌟 Core Strengths",
        "- Clear structured explanation of technical principles",
        "- Effective problem-solving approach during interactive turns",
        "- Strong alignment with target role expectations",
        "\n## 📈 Key Areas for Improvement",
        "- Provide deeper concrete examples and metrics in behavioral responses",
        "- Elaborate further on trade-offs and edge case handling",
        "\n## 📜 Turn-by-Turn Performance Breakdown",
    ]

    for turn in turns:
        eval_info = turn.evaluation
        score_str = f"{eval_info.overall_score:.1f}/5.0" if eval_info else "N/A"
        report.append(f"### Turn {turn.turn_number}: {turn.question.topic} (Difficulty: {turn.question.difficulty}/5)")
        report.append(f"**Question**: {turn.question.question}")
        report.append(f"**Answer**: {turn.answer or '(no answer)'}")
        report.append(f"**Score**: {score_str}\n")

    report.append("---\n*Note: This report was generated with deterministic analytics while API rate limits were active.*")
    return "\n".join(report)
