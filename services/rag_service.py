"""
RAG Service — Question Bank Retrieval Service.

Retrieves relevant seed questions and scoring rubrics from data/question_bank.json
based on topic, focus area, and target difficulty.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from utils.logger import get_logger

logger = get_logger(__name__)

QUESTION_BANK_PATH = Path(__file__).resolve().parent.parent / "data" / "question_bank.json"


def load_question_bank() -> list[dict[str, Any]]:
    """Load the raw question bank from disk."""
    if not QUESTION_BANK_PATH.exists():
        logger.warning("Question bank path %s does not exist.", QUESTION_BANK_PATH)
        return []

    try:
        with open(QUESTION_BANK_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.error("Failed to load question bank: %s", exc)
        return []


def retrieve_question_context(topic: str, focus_area: str, difficulty: int) -> dict[str, Any] | None:
    """
    Retrieve the best matching question entry from the question bank.
    Matches primarily by topic and focus_area, then closest difficulty level.
    """
    bank = load_question_bank()
    if not bank:
        return None

    topic_lower = topic.lower()
    focus_lower = focus_area.lower()

    candidates = []
    for item in bank:
        item_topic = str(item.get("topic", "")).lower()
        item_focus = str(item.get("focus_area", "")).lower()

        topic_match = (
            topic_lower in item_topic
            or item_topic in topic_lower
            or any(concept in topic_lower for concept in item.get("key_concepts", []))
        )
        focus_match = item_focus == focus_lower

        if focus_match or topic_match:
            diff_score = abs(item.get("difficulty", 3) - difficulty)
            topic_bonus = 0 if topic_match else 1
            candidates.append((diff_score + topic_bonus, item))

    if not candidates:
        candidates = [(abs(item.get("difficulty", 3) - difficulty), item) for item in bank]

    candidates.sort(key=lambda x: x[0])
    best_match = candidates[0][1]

    logger.info("RAG: Retrieved question seed %r (topic=%s, difficulty=%d)", best_match.get("id"), best_match.get("topic"), best_match.get("difficulty"))
    return best_match


def retrieve_relevant_questions(role: str = "", topic: str = "", difficulty: int = 3, top_k: int = 2) -> str:
    """Retrieve relevant questions formatted as string snippets for RAG prompt inclusion."""
    match = retrieve_question_context(topic=topic, focus_area="technical", difficulty=difficulty)
    if not match:
        return ""
    q_text = match.get("question", match.get("prompt", ""))
    rubric = match.get("rubric", {})
    return f"- Topic: {match.get('topic')}\n  Question: {q_text}\n  Rubric: {json.dumps(rubric)}"
