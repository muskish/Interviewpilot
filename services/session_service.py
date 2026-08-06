"""
Session Service — JSON persistent storage for InterviewPilot sessions.

Handles saving and loading InterviewState models to/from the sessions/ directory.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

from models.interview_state import InterviewState
from utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_SESSIONS_DIR = Path(__file__).parent.parent / "sessions"


def get_sessions_dir(dir_path: Union[str, Path, None] = None) -> Path:
    """Ensure sessions directory exists and return Path object."""
    path = Path(dir_path) if dir_path else DEFAULT_SESSIONS_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_session(state: InterviewState, sessions_dir: Union[str, Path, None] = None) -> Path:
    """Save InterviewState to JSON file under sessions/{session_id}.json."""
    folder = get_sessions_dir(sessions_dir)
    file_path = folder / f"{state.session_id}.json"

    json_data = state.model_dump_json(indent=2)
    file_path.write_text(json_data, encoding="utf-8")

    logger.info("Session Service: saved session %s to %s", state.session_id, file_path)
    return file_path


def load_session(session_id: str, sessions_dir: Union[str, Path, None] = None) -> InterviewState:
    """Load and deserialize InterviewState from JSON file."""
    folder = get_sessions_dir(sessions_dir)
    file_path = folder / f"{session_id}.json"

    if not file_path.exists():
        raise FileNotFoundError(f"Session file not found for session_id '{session_id}': {file_path}")

    json_data = file_path.read_text(encoding="utf-8")
    state = InterviewState.model_validate_json(json_data)
    logger.info("Session Service: loaded session %s from %s", session_id, file_path)
    return state


def list_saved_sessions(sessions_dir: Union[str, Path, None] = None) -> list[str]:
    """Return list of saved session IDs."""
    folder = get_sessions_dir(sessions_dir)
    return [f.stem for f in folder.glob("*.json")]
