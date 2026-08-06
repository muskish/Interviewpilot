"""
Multi-Language Code Sandbox & Code Quality Linter Tool.

Extracts Python, JavaScript, or SQL code blocks from candidate answers.
Executes them in isolated sandboxes and runs static code quality linting (flake8).
"""
from __future__ import annotations

import re
import sqlite3
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExecutionResult:
    language: str
    executed: bool
    stdout: str
    stderr: str
    lint_report: str | None
    exit_code: int | None
    timeout: bool


@dataclass
class CodeSnippet:
    language: str
    code: str


def extract_code_snippet(text: str) -> CodeSnippet | None:
    """Extract python, javascript, or sql code blocks from markdown text."""
    if not text:
        return None

    # Matches ```python, ```javascript, ```js, or ```sql
    pattern = r"```(python|py|javascript|js|sql)?\n(.*?)\n```"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        lang_tag = (match.group(1) or "python").lower()
        code_content = match.group(2).strip()

        if lang_tag in ("python", "py"):
            return CodeSnippet(language="python", code=code_content)
        elif lang_tag in ("javascript", "js"):
            return CodeSnippet(language="javascript", code=code_content)
        elif lang_tag == "sql":
            return CodeSnippet(language="sql", code=code_content)

    return None


def _lint_python_code(script_path: Path) -> str | None:
    """Run flake8 linter on python code snippet."""
    try:
        res = subprocess.run(
            [sys.executable, "-m", "flake8", str(script_path), "--max-line-length=100"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        output = res.stdout.strip()
        if output:
            return f"Flake8 PEP-8 Quality Feedback:\n{output}"
        return "Flake8 Quality Feedback: 0 PEP-8 violations found! Excellent code style."
    except Exception:
        return None


def execute_python_code(code: str, timeout_seconds: int = 3) -> ExecutionResult:
    """Execute Python code in subprocess and run flake8 linter."""
    with tempfile.TemporaryDirectory() as temp_dir:
        script_path = Path(temp_dir) / "sandbox.py"
        script_path.write_text(code, encoding="utf-8")

        lint_report = _lint_python_code(script_path)

        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            return ExecutionResult(
                language="python",
                executed=True,
                stdout=result.stdout.strip(),
                stderr=result.stderr.strip(),
                lint_report=lint_report,
                exit_code=result.returncode,
                timeout=False,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode("utf-8") if isinstance(exc.stdout, bytes) else str(exc.stdout or "")
            stderr = exc.stderr.decode("utf-8") if isinstance(exc.stderr, bytes) else str(exc.stderr or "")
            return ExecutionResult(
                language="python",
                executed=True,
                stdout=stdout.strip(),
                stderr=f"{stderr.strip()}\n[Execution Timed Out ({timeout_seconds}s)]",
                lint_report=lint_report,
                exit_code=None,
                timeout=True,
            )
        except Exception as exc:
            return ExecutionResult(
                language="python",
                executed=False,
                stdout="",
                stderr=str(exc),
                lint_report=lint_report,
                exit_code=1,
                timeout=False,
            )


def execute_javascript_code(code: str, timeout_seconds: int = 3) -> ExecutionResult:
    """Execute JavaScript code via node.exe."""
    with tempfile.TemporaryDirectory() as temp_dir:
        script_path = Path(temp_dir) / "sandbox.js"
        script_path.write_text(code, encoding="utf-8")

        try:
            result = subprocess.run(
                ["node", str(script_path)],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            return ExecutionResult(
                language="javascript",
                executed=True,
                stdout=result.stdout.strip(),
                stderr=result.stderr.strip(),
                lint_report=None,
                exit_code=result.returncode,
                timeout=False,
            )
        except FileNotFoundError:
            return ExecutionResult(
                language="javascript",
                executed=False,
                stdout="",
                stderr="Node.js is not installed on system path for JS execution.",
                lint_report=None,
                exit_code=1,
                timeout=False,
            )
        except subprocess.TimeoutExpired as exc:
            return ExecutionResult(
                language="javascript",
                executed=True,
                stdout="",
                stderr=f"[JS Execution Timed Out ({timeout_seconds}s)]",
                lint_report=None,
                exit_code=None,
                timeout=True,
            )


def execute_sql_code(code: str) -> ExecutionResult:
    """Execute SQL queries against in-memory SQLite database."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    
    stdout_lines = []
    stderr = ""
    exit_code = 0

    try:
        # Separate statements by semicolon
        statements = [stmt.strip() for stmt in code.split(";") if stmt.strip()]
        for stmt in statements:
            cursor.execute(stmt)
            if cursor.description:  # It was a SELECT query
                headers = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                
                # Format into ASCII Markdown Table
                stdout_lines.append(f"Query Result for `{stmt[:40]}...`:")
                stdout_lines.append(" | ".join(headers))
                stdout_lines.append("-" * (len(" | ".join(headers)) + 4))
                for row in rows:
                    stdout_lines.append(" | ".join(str(val) for val in row))
                stdout_lines.append("")
        conn.commit()
    except Exception as exc:
        stderr = f"SQL Execution Error: {exc}"
        exit_code = 1
    finally:
        conn.close()

    return ExecutionResult(
        language="sql",
        executed=True,
        stdout="\n".join(stdout_lines).strip() or "SQL Statements executed successfully (No result set returned).",
        stderr=stderr,
        lint_report=None,
        exit_code=exit_code,
        timeout=False,
    )


def execute_code_snippet(snippet: CodeSnippet) -> ExecutionResult:
    """Route code snippet to appropriate multi-language sandbox."""
    if snippet.language == "python":
        return execute_python_code(snippet.code)
    elif snippet.language == "javascript":
        return execute_javascript_code(snippet.code)
    elif snippet.language == "sql":
        return execute_sql_code(snippet.code)
    else:
        return ExecutionResult(
            language=snippet.language,
            executed=False,
            stdout="",
            stderr=f"Unsupported sandbox language: {snippet.language}",
            lint_report=None,
            exit_code=1,
            timeout=False,
        )
