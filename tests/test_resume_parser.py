"""
Unit tests for the resume parser utility.
"""
from __future__ import annotations

import io
from collections import namedtuple
from unittest.mock import MagicMock

import pytest

from utils.resume_parser import extract_resume_text

# Create a mock Streamlit UploadedFile class
MockUploadedFile = namedtuple("MockUploadedFile", ["name", "read"])


def test_extract_txt_resume():
    """Verify TXT files are parsed correctly."""
    mock_file = MockUploadedFile(
        name="resume.txt",
        read=lambda: b"Jane Doe\nPython Developer\nSkills: React, SQL",
    )
    text = extract_resume_text(mock_file)
    assert text is not None
    assert "Jane Doe" in text
    assert "Python Developer" in text


def test_extract_invalid_extension():
    """Verify unsupported extensions return None."""
    mock_file = MockUploadedFile(
        name="resume.docx",
        read=lambda: b"fake docx bytes",
    )
    text = extract_resume_text(mock_file)
    assert text is None


def test_extract_none_file():
    """Verify None input is handled gracefully."""
    text = extract_resume_text(None)
    assert text is None
