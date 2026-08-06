"""
Unit tests for the audio multimodal service.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from services.audio_service import generate_speech, transcribe_audio


def test_generate_speech_none():
    """Verify none handles correctly."""
    assert generate_speech("") is None
    assert generate_speech(None) is None


@patch("services.audio_service.gTTS")
def test_generate_speech_success(mock_gtts):
    """Verify gTTS is called and bytes are returned."""
    mock_instance = mock_gtts.return_value
    
    def fake_write_to_fp(fp):
        fp.write(b"fake_mp3_data")
        
    mock_instance.write_to_fp = fake_write_to_fp

    audio_bytes = generate_speech("Hello world")
    assert audio_bytes == b"fake_mp3_data"
    mock_gtts.assert_called_once_with(text="Hello world", lang="en", slow=False)


def test_transcribe_audio_none():
    """Verify none handles correctly."""
    assert transcribe_audio(None) is None
    assert transcribe_audio(b"") is None


@patch("services.audio_service._transcribe_free_google")
@patch("services.audio_service.os.getenv")
def test_transcribe_no_api_keys(mock_getenv, mock_google):
    """Verify it falls back to free google when no API keys are set."""
    mock_getenv.return_value = None
    mock_google.return_value = "Hello transcribed text"
    result = transcribe_audio(b"fake_audio")
    assert result == "Hello transcribed text"
