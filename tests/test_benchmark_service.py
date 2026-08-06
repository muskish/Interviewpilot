"""
Unit tests for FAISS Vector DB Benchmarking RAG service.
"""
from __future__ import annotations

import pytest

from services.benchmark_service import (
    VectorBenchmarkStore,
    retrieve_peer_benchmarks,
)


def test_vector_benchmark_store_init():
    """Verify store initializes with 9 mock candidates."""
    store = VectorBenchmarkStore()
    assert len(store.profiles) == 9
    assert store.index is not None


def test_query_similar_peers():
    """Verify vector search returns closest peers."""
    store = VectorBenchmarkStore()
    peers = store.query_similar_peers("AI Engineer", "technical", top_k=3)
    assert len(peers) == 3
    # Check that AI/ML candidates are retrieved at top
    retrieved_roles = [p.role for p in peers]
    assert "AI Engineer" in retrieved_roles or "AI Research Scientist" in retrieved_roles or "ML Engineer" in retrieved_roles


def test_retrieve_peer_benchmarks_format():
    """Verify helper function returns non-empty formatted markdown string."""
    context = retrieve_peer_benchmarks("Software Engineer", "technical", "Python, React")
    assert isinstance(context, str)
    assert "Peer Role:" in context
    assert "Historical Score:" in context
