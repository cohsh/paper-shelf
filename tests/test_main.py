import json
import os
import tempfile
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from paper_shelf.main import cli
from paper_shelf.storage import save
from paper_shelf.library import update_index


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def populated_library():
    """Create a temporary library with one paper."""
    with tempfile.TemporaryDirectory() as d:
        results = {
            "claude": {
                "title": "Test Paper",
                "authors": ["Author, A."],
                "year": 2024,
                "abstract_summary": "A test paper summary.",
                "key_contributions": ["Contribution 1"],
                "methodology": "Test method",
                "main_results": "Test results",
                "limitations": ["Limitation 1"],
                "connections": "Related work",
                "tags": ["test", "ml"],
            }
        }
        pid = save(results, {}, d)
        update_index(pid, d)
        yield d, pid


def test_cli_help(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Paper Reading Library" in result.output


def test_list_empty(runner):
    with tempfile.TemporaryDirectory() as d:
        result = runner.invoke(cli, ["list", "--output-dir", d])
        assert result.exit_code == 0
        assert "No papers" in result.output


def test_list_papers(runner, populated_library):
    library_dir, _ = populated_library
    result = runner.invoke(cli, ["list", "--output-dir", library_dir])
    assert result.exit_code == 0
    assert "Test Paper" in result.output


def test_list_json_format(runner, populated_library):
    library_dir, _ = populated_library
    result = runner.invoke(cli, ["list", "--format", "json", "--output-dir", library_dir])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["title"] == "Test Paper"


def test_search_found(runner, populated_library):
    library_dir, _ = populated_library
    result = runner.invoke(cli, ["search", "test", "--output-dir", library_dir])
    assert result.exit_code == 0
    assert "Test Paper" in result.output


def test_search_not_found(runner, populated_library):
    library_dir, _ = populated_library
    result = runner.invoke(cli, ["search", "quantum", "--output-dir", library_dir])
    assert result.exit_code == 0
    assert "No papers found" in result.output


def test_show_paper(runner, populated_library):
    library_dir, pid = populated_library
    result = runner.invoke(cli, ["show", pid, "--output-dir", library_dir, "--raw"])
    assert result.exit_code == 0
    assert "Test Paper" in result.output


def test_show_not_found(runner):
    with tempfile.TemporaryDirectory() as d:
        result = runner.invoke(cli, ["show", "nonexistent", "--output-dir", d])
        assert result.exit_code == 1
