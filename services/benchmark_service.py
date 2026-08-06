"""
Vector Database (FAISS) RAG Service for Candidate Benchmarking.

Maintains a dense vector index of historical candidate performances.
When a candidate finishes their interview, the Coach Agent queries FAISS
to retrieve the top similar historical peers and benchmark their performance.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import faiss
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from utils.logger import get_logger

logger = get_logger(__name__)

# Lightweight, zero-latency vectorizer
_VECTORIZER = None


def _get_vectorizer() -> TfidfVectorizer:
    global _VECTORIZER
    if _VECTORIZER is None:
        _VECTORIZER = TfidfVectorizer(ngram_range=(1, 2), max_features=128)
    return _VECTORIZER


@dataclass
class PeerProfile:
    peer_id: str
    role: str
    focus_area: str
    score: float
    summary: str


# 9 Mock Historical Candidates for RAG Benchmarking
MOCK_CANDIDATE_DATABASE: list[PeerProfile] = [
    PeerProfile(
        peer_id="peer_001",
        role="AI Engineer",
        focus_area="technical",
        score=4.8,
        summary="Expert proficiency in PyTorch, LangChain, RAG architectures, and fine-tuning LLMs.",
    ),
    PeerProfile(
        peer_id="peer_002",
        role="Backend Engineer",
        focus_area="technical",
        score=3.2,
        summary="Intermediate knowledge of Python, Django, REST APIs, and PostgreSQL query optimization.",
    ),
    PeerProfile(
        peer_id="peer_003",
        role="Frontend Engineer",
        focus_area="technical",
        score=4.5,
        summary="Advanced skills in React, TypeScript, Next.js SSR, and modern CSS glassmorphism styling.",
    ),
    PeerProfile(
        peer_id="peer_004",
        role="Data Engineer",
        focus_area="mixed",
        score=2.5,
        summary="Basic understanding of PySpark, SQL joins, and Airflow DAG construction; struggled with window functions.",
    ),
    PeerProfile(
        peer_id="peer_005",
        role="ML Engineer",
        focus_area="technical",
        score=4.2,
        summary="Strong background in Scikit-learn, MLOps deployment pipelines, Docker containerization, and ONNX runtime.",
    ),
    PeerProfile(
        peer_id="peer_006",
        role="Product Manager",
        focus_area="behavioral",
        score=3.9,
        summary="Solid strategic thinking, user story mapping, and Agile sprint planning; good trade-off awareness.",
    ),
    PeerProfile(
        peer_id="peer_007",
        role="Fullstack Developer",
        focus_area="technical",
        score=4.6,
        summary="Exemplary full-stack capabilities across Node.js, React, FastAPI, and WebSocket real-time communication.",
    ),
    PeerProfile(
        peer_id="peer_008",
        role="DevOps Engineer",
        focus_area="mixed",
        score=3.0,
        summary="Elementary knowledge of Kubernetes cluster management, CI/CD pipelines, and Terraform state files.",
    ),
    PeerProfile(
        peer_id="peer_009",
        role="AI Research Scientist",
        focus_area="technical",
        score=4.9,
        summary="Flawless grasp of Transformer attention mechanisms, KV-caching, and distributed multi-GPU training math.",
    ),
]


class VectorBenchmarkStore:
    """FAISS Vector Store wrapper for RAG benchmarking."""

    def __init__(self):
        self.profiles: list[PeerProfile] = list(MOCK_CANDIDATE_DATABASE)
        self.index: faiss.IndexFlatIP | None = None
        self._build_index()

    def _build_index(self):
        """Vectorize all candidate profiles into FAISS index."""
        try:
            vectorizer = _get_vectorizer()
            texts = [
                f"Role: {p.role}. Focus: {p.focus_area}. Score: {p.score}. Summary: {p.summary}"
                for p in self.profiles
            ]
            embeddings = vectorizer.fit_transform(texts).toarray().astype(np.float32)
            
            # Normalize vectors for Cosine Similarity (Inner Product)
            faiss.normalize_L2(embeddings)
            dimension = embeddings.shape[1]

            # Use Inner Product (Cosine similarity on normalized vectors)
            self.index = faiss.IndexFlatIP(dimension)
            self.index.add(embeddings)
            logger.info("FAISS Vector Index initialized with %d peer profiles.", len(self.profiles))
        except Exception as exc:
            logger.error("Failed to build FAISS index: %s", exc)

    def query_similar_peers(self, target_role: str, focus_area: str, background: str | None = None, top_k: int = 3) -> list[PeerProfile]:
        """RAG Retrieval: Vector search for top_k most relevant historical peers."""
        if self.index is None or not self.profiles:
            return self.profiles[:top_k]

        try:
            vectorizer = _get_vectorizer()
            query_text = f"Role: {target_role}. Focus: {focus_area}. Background: {background or ''}"
            query_vector = vectorizer.transform([query_text]).toarray().astype(np.float32)
            faiss.normalize_L2(query_vector)

            scores, indices = self.index.search(query_vector, top_k)
            
            matched_peers = []
            for idx in indices[0]:
                if 0 <= idx < len(self.profiles):
                    matched_peers.append(self.profiles[idx])
            return matched_peers
        except Exception as exc:
            logger.error("FAISS Vector Search failed: %s", exc)
            return self.profiles[:top_k]


# Global singleton instance
_BENCHMARK_STORE = None

def get_benchmark_store() -> VectorBenchmarkStore:
    global _BENCHMARK_STORE
    if _BENCHMARK_STORE is None:
        _BENCHMARK_STORE = VectorBenchmarkStore()
    return _BENCHMARK_STORE


def retrieve_peer_benchmarks(target_role: str, focus_area: str, background: str | None = None) -> str:
    """Helper function to fetch RAG peer context formatted for the Coach agent."""
    store = get_benchmark_store()
    peers = store.query_similar_peers(target_role, focus_area, background, top_k=3)

    formatted_peers = []
    for p in peers:
        formatted_peers.append(
            f"- Peer Role: {p.role} | Historical Score: {p.score:.1f}/5.0\n"
            f"  Summary: {p.summary}"
        )
    
    return "\n".join(formatted_peers)
