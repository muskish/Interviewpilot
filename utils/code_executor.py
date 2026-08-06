"""
Python Code Sandbox Execution Tool.

Extracts python code blocks from candidate answers and runs them in a safe
subprocess sandbox with a strict timeout.
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExecutionResult:
    executed: bool
    stdout: str
    stderr: str
    exit_code: int | None
    timeout: bool


def extract_python_code(text: str) -> str | None:
    """Extract the first python code block from a markdown string."""
    # Matches ```python ... ``` or ``` ... ``` if it looks like code
    match = re.search(r"```(?:python|py)?\n(.*?)\n```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def execute_python_code(code: str, timeout_seconds: int = 3) -> ExecutionResult:
    """
    Execute python code in a temporary file and return the result.
    WARNING: In a real production system, this should run inside a Docker container
    or secure sandbox (like gVisor or WebAssembly) to prevent RCE.
    """
    if not code.strip():
        return ExecutionResult(executed=False, stdout="", stderr="No code provided.", exit_code=None, timeout=False)

    logger.info("CodeExecutor: Running candidate python code block...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        script_path = Path(temp_dir) / "sandbox.py"
        script_path.write_text(code, encoding="utf-8")

        try:
            # Run the python script as a subprocess
            result = subprocess.run(
                ["python", str(script_path)],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            return ExecutionResult(
                executed=True,
                stdout=result.stdout.strip(),
                stderr=result.stderr.strip(),
                exit_code=result.returncode,
                timeout=False,
            )
        except subprocess.TimeoutExpired as exc:
            logger.warning("CodeExecutor: Execution timed out after %d seconds.", timeout_seconds)
            # Try to grab whatever was produced before timeout
            stdout = exc.stdout.decode("utf-8") if isinstance(exc.stdout, bytes) else str(exc.stdout or "")
            stderr = exc.stderr.decode("utf-8") if isinstance(exc.stderr, bytes) else str(exc.stderr or "")
            
            return ExecutionResult(
                executed=True,
                stdout=stdout.strip(),
                stderr=f"{stderr.strip()}\n[Error: Execution timed out after {timeout_seconds} seconds.]",
                exit_code=None,
                timeout=True,
            )
        except Exception as exc:
            logger.error("CodeExecutor: Unexpected error during execution: %s", exc)
            return ExecutionResult(
                executed=False,
                stdout="",
                stderr=f"Sandbox Execution Error: {exc}",
                exit_code=1,
                timeout=False,
            )
