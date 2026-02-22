import json
from unittest.mock import patch

import pytest

from src.exceptions import ClaudeReaderError
from src.pdf_extractor import ExtractedPaper
from src.reader_claude import read


@pytest.fixture
def sample_paper():
    return ExtractedPaper(
        text="This is test paper content about machine learning.",
        metadata={"title": "Test Paper"},
        page_count=1,
        source_path="/tmp/test.pdf",
        char_count=50,
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
        "confidence_notes": "Clean extraction.",
    }


def test_read_success(sample_paper, valid_response):
    mock_result = type("Result", (), {
        "returncode": 0,
        "stdout": json.dumps({"result": json.dumps(valid_response)}),
        "stderr": "",
    })()

    with patch("src.reader_claude.subprocess.run", return_value=mock_result):
        result = read(sample_paper)

    assert result["title"] == "Test Paper"
    assert result["year"] == 2024


def test_read_direct_json(sample_paper, valid_response):
    """Test when Claude returns the JSON directly (not wrapped in result)."""
    mock_result = type("Result", (), {
        "returncode": 0,
        "stdout": json.dumps(valid_response),
        "stderr": "",
    })()

    with patch("src.reader_claude.subprocess.run", return_value=mock_result):
        result = read(sample_paper)

    assert result["title"] == "Test Paper"


def test_read_cli_failure(sample_paper):
    mock_result = type("Result", (), {
        "returncode": 1,
        "stdout": "",
        "stderr": "Error occurred",
    })()

    with patch("src.reader_claude.subprocess.run", return_value=mock_result):
        with pytest.raises(ClaudeReaderError, match="failed"):
            read(sample_paper)


def test_read_invalid_json(sample_paper):
    mock_result = type("Result", (), {
        "returncode": 0,
        "stdout": "not valid json at all",
        "stderr": "",
    })()

    with patch("src.reader_claude.subprocess.run", return_value=mock_result):
        with pytest.raises(ClaudeReaderError, match="Failed to parse"):
            read(sample_paper)


def test_read_timeout(sample_paper):
    import subprocess

    with patch(
        "src.reader_claude.subprocess.run",
        side_effect=subprocess.TimeoutExpired("claude", 600),
    ):
        with pytest.raises(ClaudeReaderError, match="timed out"):
            read(sample_paper)


def test_read_cli_not_found(sample_paper):
    with patch(
        "src.reader_claude.subprocess.run",
        side_effect=FileNotFoundError,
    ):
        with pytest.raises(ClaudeReaderError, match="not found"):
            read(sample_paper)
