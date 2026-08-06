"""
Unit tests for the Python Sandbox Executor tool.
"""
from __future__ import annotations

from utils.code_executor import extract_python_code, execute_python_code


def test_extract_python_code():
    """Verify markdown code blocks are extracted correctly."""
    text = "Here is my answer:\n```python\nprint('hello')\n```\nHope it helps!"
    code = extract_python_code(text)
    assert code == "print('hello')"


def test_extract_python_code_no_lang():
    """Verify markdown code blocks without lang tag work."""
    text = "```\nx = 1\n```"
    code = extract_python_code(text)
    assert code == "x = 1"


def test_extract_python_code_none():
    """Verify returns None if no code block."""
    text = "Just standard text here."
    code = extract_python_code(text)
    assert code is None


def test_execute_python_success():
    """Verify normal execution captures stdout correctly."""
    code = "print('hello world')"
    result = execute_python_code(code)
    assert result.executed is True
    assert result.stdout == "hello world"
    assert result.exit_code == 0
    assert result.timeout is False


def test_execute_python_syntax_error():
    """Verify syntax errors are captured in stderr."""
    code = "print('hello"
    result = execute_python_code(code)
    assert result.executed is True
    assert result.exit_code != 0
    assert "SyntaxError" in result.stderr


def test_execute_python_timeout():
    """Verify infinite loops are killed by timeout."""
    code = "import time\nwhile True:\n    time.sleep(0.1)"
    result = execute_python_code(code, timeout_seconds=1)
    assert result.executed is True
    assert result.timeout is True
    assert result.exit_code is None
    assert "Execution timed out" in result.stderr
