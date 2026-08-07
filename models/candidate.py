"""Candidate-provided input: what the setup screen collects."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class FocusArea(str, Enum):
    BEHAVIORAL = "behavioral"
    TECHNICAL = "technical"
    DSA_CODING = "dsa_coding"
    CASE = "case"
    MIXED = "mixed"


class CandidateProfile(BaseModel):
    target_role: str = Field(..., min_length=1, description="e.g. 'Frontend Engineer Intern'")
    background: str | None = Field(
        default=None, description="Optional 2-3 line background/resume snippet."
    )
    job_description: str | None = Field(
        default=None, description="Optional job description text for grounding the interview strategy."
    )
    focus_area: FocusArea
