"""
Audio Service for Voice-to-Voice Multimodal Interviews.

Provides:
- Speech-to-Text (STT) via Groq Whisper API (or OpenAI Whisper).
- Text-to-Speech (TTS) via gTTS (Google Text-to-Speech) for free audio generation.
"""
from __future__ import annotations

import io
import os
import tempfile
from typing import Any

from gtts import gTTS
from groq import Groq
from openai import OpenAI

from utils.logger import get_logger

logger = get_logger(__name__)


import streamlit as st

@st.cache_data(show_spinner=False)
def generate_speech(text: str) -> bytes | None:
    """
    Generate MP3 speech from text using gTTS.
    Returns the MP3 data as bytes, which Streamlit can play natively.
    """
    if not text:
        return None
        
    try:
        logger.info("Generating TTS audio for text: %s...", text[:30])
        tts = gTTS(text=text, lang="en", slow=False)
        
        # Save to an in-memory bytes buffer
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.read()
        
    except Exception as exc:
        logger.error("Failed to generate TTS audio: %s", exc)
        return None


def transcribe_audio(audio_bytes: bytes) -> str | None:
    """
    Transcribe candidate's recorded audio (WAV bytes) into text.
    Prefers Groq (whisper-large-v3) for speed, falls back to OpenAI Whisper.
    """
    if not audio_bytes:
        return None
        
    groq_api_key = os.getenv("GROQ_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not groq_api_key and not openai_api_key:
        logger.error("No GROQ_API_KEY or OPENAI_API_KEY found for transcription.")
        return None

    # We must save the bytes to a temp file because both Groq and OpenAI 
    # clients expect a file-like object with a named extension.
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_filepath = tmp_file.name
            
        transcribed_text = None
        
        # Try Groq Whisper First (Extremely Fast)
        if groq_api_key:
            try:
                client = Groq(api_key=groq_api_key)
                with open(tmp_filepath, "rb") as file:
                    transcription = client.audio.transcriptions.create(
                        file=(tmp_filepath, file.read()),
                        model="whisper-large-v3-turbo",
                        response_format="text",
                    )
                transcribed_text = transcription
                logger.info("Transcribed via Groq Whisper successfully.")
            except Exception as e:
                logger.error("Groq Whisper API failed: %s", e)
                
        # Fallback to OpenAI Whisper
        if not transcribed_text and openai_api_key:
            try:
                client = OpenAI(api_key=openai_api_key)
                with open(tmp_filepath, "rb") as file:
                    transcription = client.audio.transcriptions.create(
                        file=(tmp_filepath, file.read()),
                        model="whisper-1",
                        response_format="text",
                    )
                transcribed_text = transcription
                logger.info("Transcribed via OpenAI Whisper successfully.")
            except Exception as e:
                logger.error("OpenAI Whisper API failed: %s", e)
                
        # Clean up temp file
        if os.path.exists(tmp_filepath):
            os.remove(tmp_filepath)
            
        return transcribed_text.strip() if transcribed_text else None
        
    except Exception as exc:
        logger.error("Failed to process audio bytes for transcription: %s", exc)
        return None
