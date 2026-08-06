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

from dotenv import load_dotenv
import speech_recognition as sr

from utils.logger import get_logger

load_dotenv()
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


def _transcribe_free_google(audio_bytes: bytes) -> str | None:
    """Free SpeechRecognition fallback (No API keys required)."""
    try:
        r = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio_data = r.record(source)
            text = r.recognize_google(audio_data)
            logger.info("Transcribed via free Google Speech API successfully.")
            return text
    except Exception as e:
        logger.warning("Free Google Speech Recognition failed: %s", e)
        return None


def transcribe_audio(audio_bytes: bytes) -> str | None:
    """
    Transcribe candidate's recorded audio into text.
    Tries Groq Whisper -> OpenAI Whisper -> Free Google SpeechRecognition fallback.
    """
    if not audio_bytes:
        return None
        
    groq_api_key = os.getenv("GROQ_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    try:
        transcribed_text = None
        
        # 1. Try Groq Whisper First
        if groq_api_key:
            try:
                client = Groq(api_key=groq_api_key)
                transcription = client.audio.transcriptions.create(
                    file=("speech.wav", audio_bytes, "audio/wav"),
                    model="whisper-large-v3-turbo",
                    response_format="text",
                )
                transcribed_text = transcription
                logger.info("Transcribed via Groq Whisper successfully.")
            except Exception as e:
                logger.error("Groq Whisper API failed: %s", e)
                
        # 2. Fallback to OpenAI Whisper
        if not transcribed_text and openai_api_key:
            try:
                client = OpenAI(api_key=openai_api_key)
                transcription = client.audio.transcriptions.create(
                    file=("speech.wav", audio_bytes, "audio/wav"),
                    model="whisper-1",
                    response_format="text",
                )
                transcribed_text = transcription
                logger.info("Transcribed via OpenAI Whisper successfully.")
            except Exception as e:
                logger.error("OpenAI Whisper API failed: %s", e)

        # 3. Fallback to 100% Free Google SpeechRecognition
        if not transcribed_text:
            transcribed_text = _transcribe_free_google(audio_bytes)
            
        return transcribed_text.strip() if transcribed_text else None
        
    except Exception as exc:
        logger.error("Failed to process audio bytes for transcription: %s", exc)
        return None
