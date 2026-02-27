import json
import os
from unittest.mock import patch

import pytest

from paper_shelf.exceptions import CodexReaderError
from paper_shelf.pdf_extractor import ExtractedPaper
from paper_shelf.reader_codex import is_available, read


@pytest.fixture
def sample_paper():
    return ExtractedPaper(
        text="This is test paper content about deep learning.",
        metadata={"title": "Test Paper"},
        page_count=1,
        source_path="/tmp/test.pdf",
        char_count=47,
    )


@pytest.fixture
def valid_response():
    return {
        "title": "Test Paper",
        "authors": ["Author, A."],
        "year": 2024,
        "abstract_summary": "A test paper.",
        "key_contributions": ["Contribution 1"],
        "methodology": "Test method",
        "main_results": "Test results",
        "limitations": ["Limitation 1"],
        "connections": "Related work",
        "tags": ["test"],
    }


def test_is_available():
    with patch("paper_shelf.reader_codex.shutil.which", return_value="/usr/bin/codex"):
        assert is_available() is True

    with patch("paper_shelf.reader_codex.shutil.which", return_value=None):
        assert is_available() is False


def test_read_not_available(sample_paper):
    with patch("paper_shelf.reader_codex.shutil.which", return_value=None):
        with pytest.raises(CodexReaderError, match="not found"):
            read(sample_paper)


def test_read_success_from_stdout(sample_paper, valid_response):
    mock_result = type("Result", (), {
        "returncode": 0,
        "stdout": json.dumps(valid_response),
        "stderr": "",
    })()

    with (
        patch("paper_shelf.reader_codex.shutil.which", return_value="/usr/bin/codex"),
        patch("paper_shelf.reader_codex.subprocess.run", return_value=mock_result),
    ):
        result = read(sample_paper)

    assert result["title"] == "Test Paper"


def test_read_cli_failure(sample_paper):
    mock_result = type("Result", (), {
        "returncode": 1,
        "stdout": "",
        "stderr": "Error",
    })()

    with (
        patch("paper_shelf.reader_codex.shutil.which", return_value="/usr/bin/codex"),
        patch("paper_shelf.reader_codex.subprocess.run", return_value=mock_result),
    ):
        with pytest.raises(CodexReaderError, match="failed"):
            read(sample_paper)


def test_read_timeout(sample_paper):
    import subprocess

    with (
        patch("paper_shelf.reader_codex.shutil.which", return_value="/usr/bin/codex"),
        patch(
            "paper_shelf.reader_codex.subprocess.run",
            side_effect=subprocess.TimeoutExpired("codex", 600),
        ),
    ):
        with pytest.raises(CodexReaderError, match="timed out"):
            read(sample_paper)


def test_read_markdown_json(sample_paper, valid_response):
    """Test extracting JSON from markdown code block output."""
    stdout = f"```json\n{json.dumps(valid_response)}\n```"
    mock_result = type("Result", (), {
        "returncode": 0,
        "stdout": stdout,
        "stderr": "",
    })()

    with (
        patch("paper_shelf.reader_codex.shutil.which", return_value="/usr/bin/codex"),
        patch("paper_shelf.reader_codex.subprocess.run", return_value=mock_result),
    ):
        result = read(sample_paper)

    assert result["title"] == "Test Paper"
