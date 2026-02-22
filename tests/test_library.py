import json
import os
import tempfile

import pytest

from src.library import get_paper, load_index, search, update_index
from src.storage import save


@pytest.fixture
def library_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def populated_library(library_dir):
    """Create a library with two papers."""
    results1 = {
        "claude": {
            "title": "Attention Is All You Need",
            "authors": ["Vaswani, A."],
            "year": 2017,
            "abstract_summary": "Introduces the Transformer.",
            "key_contributions": ["Self-attention"],
            "methodology": "Novel architecture",
            "main_results": "SOTA on translation",
            "limitations": ["Memory usage"],
            "connections": "Prior attention work",
            "tags": ["transformer", "nlp"],
        }
    }
    results2 = {
        "claude": {
            "title": "BERT: Pre-training",
            "authors": ["Devlin, J."],
            "year": 2018,
            "abstract_summary": "Pre-training for NLP.",
            "key_contributions": ["Bidirectional pre-training"],
            "methodology": "Masked LM",
            "main_results": "SOTA on GLUE",
            "limitations": ["Compute cost"],
            "connections": "Builds on Transformer",
            "tags": ["bert", "nlp", "pre-training"],
        }
    }

    pid1 = save(results1, {}, library_dir)
    update_index(pid1, library_dir)
    pid2 = save(results2, {}, library_dir)
    update_index(pid2, library_dir)

    return library_dir, pid1, pid2


def test_load_index_empty(library_dir):
    index = load_index(library_dir)
    assert index["version"] == 1
    assert index["papers"] == []


def test_update_and_load_index(populated_library):
    library_dir, pid1, pid2 = populated_library
    index = load_index(library_dir)
    assert len(index["papers"]) == 2

    ids = [p["paper_id"] for p in index["papers"]]
    assert pid1 in ids
    assert pid2 in ids


def test_get_paper(populated_library):
    library_dir, pid1, _ = populated_library
    paper = get_paper(pid1, library_dir)
    assert paper["title"] == "Attention Is All You Need"
    assert "readings" in paper


def test_search_by_title(populated_library):
    library_dir, _, _ = populated_library
    results = search("attention", field="title", output_dir=library_dir)
    assert len(results) == 1
    assert results[0]["title"] == "Attention Is All You Need"


def test_search_by_tags(populated_library):
    library_dir, _, _ = populated_library
    results = search("nlp", field="tags", output_dir=library_dir)
    assert len(results) == 2


def test_search_all(populated_library):
    library_dir, _, _ = populated_library
    results = search("transformer", field="all", output_dir=library_dir)
    assert len(results) >= 1


def test_search_no_results(populated_library):
    library_dir, _, _ = populated_library
    results = search("quantum computing", field="all", output_dir=library_dir)
    assert len(results) == 0
