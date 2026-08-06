"""
Unit tests for Question Bank RAG service (services/rag_service.py).
"""
from __future__ import annotations

from services.rag_service import load_question_bank, retrieve_question_context


def test_load_question_bank():
    """Verify that question bank loads non-empty list of entries."""
    bank = load_question_bank()
    assert isinstance(bank, list)
    assert len(bank) > 0
    assert "id" in bank[0]
    assert "seed_question" in bank[0]


def test_retrieve_question_context_topic_match():
    """Verify retrieval returns relevant item when topic matches."""
    match = retrieve_question_context(topic="Python", focus_area="technical", difficulty=2)
    assert match is not None
    assert "Python" in match["topic"] or "lists and tuples" in match["seed_question"]


def test_retrieve_question_context_fallback():
    """Verify retrieval gracefully falls back to closest difficulty if topic is novel."""
    match = retrieve_question_context(topic="Quantum Mechanics", focus_area="technical", difficulty=4)
    assert match is not None
    assert "id" in match
