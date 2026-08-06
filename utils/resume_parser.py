"""
Resume parsing utilities for the Streamlit UI.
"""
from __future__ import annotations

import io
from typing import Any

from pypdf import PdfReader
from utils.logger import get_logger

logger = get_logger(__name__)


def extract_resume_text(uploaded_file: Any) -> str | None:
    """
    Extract text from a Streamlit UploadedFile object.
    Supports .pdf and .txt extensions.
    """
    if uploaded_file is None:
        return None

    filename = uploaded_file.name.lower()
    
    try:
        # Read the file bytes
        file_bytes = uploaded_file.read()

        if filename.endswith(".txt"):
            text = file_bytes.decode("utf-8", errors="replace")
            # Truncate to a reasonable length (e.g., ~1500 words or 8000 chars) to fit in context window
            return text[:8000].strip()

        elif filename.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(file_bytes))
            text_blocks = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_blocks.append(page_text)
            
            full_text = "\n".join(text_blocks)
            # Truncate
            return full_text[:8000].strip()
        else:
            logger.warning("Unsupported resume file type: %s", filename)
            return None

    except Exception as exc:
        logger.error("Failed to parse resume %r: %s", filename, exc)
        return None
