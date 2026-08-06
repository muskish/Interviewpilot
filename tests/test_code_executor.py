"""
Unit tests for the Multi-Language Sandbox & Code Quality Linter Tool.
"""
from __future__ import annotations

from utils.code_executor import (
    extract_code_snippet,
    execute_code_snippet,
    execute_sql_code,
)


def test_extract_code_snippet_python():
    """Verify python code extraction."""
    text = "Here is my answer:\n```python\nprint('hello')\n```"
    snippet = extract_code_snippet(text)
    assert snippet is not None
    assert snippet.language == "python"
    assert snippet.code == "print('hello')"


def test_extract_code_snippet_js():
    """Verify javascript code extraction."""
    text = "```javascript\nconsole.log('hi');\n```"
    snippet = extract_code_snippet(text)
    assert snippet is not None
    assert snippet.language == "javascript"
    assert snippet.code == "console.log('hi');"


def test_extract_code_snippet_sql():
    """Verify sql code extraction."""
    text = "```sql\nSELECT * FROM users;\n```"
    snippet = extract_code_snippet(text)
    assert snippet is not None
    assert snippet.language == "sql"


def test_execute_python_with_linter():
    """Verify python execution captures stdout and flake8 linting."""
    snippet = extract_code_snippet("```python\nx = 1\nprint(x)\n```")
    result = execute_code_snippet(snippet)
    assert result.executed is True
    assert result.stdout == "1"
    assert result.lint_report is not None


def test_execute_sql_query():
    """Verify in-memory SQLite table execution and ASCII table output."""
    sql_code = """
    CREATE TABLE candidates (id INT, name TEXT);
    INSERT INTO candidates VALUES (1, 'Alice');
    SELECT * FROM candidates;
    """
    result = execute_sql_code(sql_code)
    assert result.executed is True
    assert result.exit_code == 0
    assert "Alice" in result.stdout
    assert "Query Result" in result.stdout
