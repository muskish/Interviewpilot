"""
Unit tests for Edge Cases (Phase 11).

Tests API failures, malformed LLM responses, and the retry logic built into llm_service.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from services.llm_service import generate_structured


class DummyOutput(BaseModel):
    name: str
    age: int


@patch("time.sleep", return_value=None)  # prevent actual sleeping during tests
def test_generate_structured_retry_success(mock_sleep: MagicMock):
    """Test that generate_structured retries on validation failure and succeeds if a later attempt is valid."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured

    # First call returns bad dict (missing 'age'), second call returns valid model
    mock_structured.invoke.side_effect = [
        {"name": "Alice"},  # Invalid
        DummyOutput(name="Bob", age=30),  # Valid
    ]

    result = generate_structured(
        llm=mock_llm,
        system_prompt="sys",
        user_message="user",
        output_model=DummyOutput,
        max_retries=2,
    )

    assert result.name == "Bob"
    assert result.age == 30
    assert mock_structured.invoke.call_count == 2
    assert mock_sleep.call_count == 1  # Slept once after first failure


@patch("time.sleep", return_value=None)
def test_generate_structured_max_retries_exceeded(mock_sleep: MagicMock):
    """Test that generate_structured raises RuntimeError if all retries fail."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured

    # Always return invalid dict
    mock_structured.invoke.return_value = {"name": "Alice"}

    with pytest.raises(RuntimeError) as exc_info:
        generate_structured(
            llm=mock_llm,
            system_prompt="sys",
            user_message="user",
            output_model=DummyOutput,
            max_retries=2,
        )

    assert "LLM failed to return valid DummyOutput after 3 attempts" in str(exc_info.value)
    assert mock_structured.invoke.call_count == 3
    assert mock_sleep.call_count == 3
