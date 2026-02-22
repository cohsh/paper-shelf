import json
import os
import tempfile

import pytest

from src.storage import generate_paper_id, save


@pytest.fixture
def output_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def sample_results():
    return {
        "claude": {
            "title": "Attention Is All You Need",
            "authors": ["Vaswani, A.", "Shazeer, N."],
            "year": 2017,
            "abstract_summary": "This paper introduces the Transformer architecture.",
            "key_contributions": [
                "Introduced self-attention mechanism",
                "Removed need for recurrence",
            ],
            "methodology": "The authors propose a novel architecture based on attention.",
            "main_results": "Achieved state-of-the-art on WMT translation tasks.",
            "limitations": ["Limited to sequence tasks", "High memory usage"],
            "connections": "Builds on prior attention work by Bahdanau et al.",
            "tags": ["transformer", "attention", "nlp"],
            "confidence_notes": "Text extraction was clean.",
        }
    }


@pytest.fixture
def sample_metadata():
    return {"title": "Attention Is All You Need", "author": "Vaswani et al."}


def test_generate_paper_id():
    assert generate_paper_id("Attention Is All You Need") == "attention-is-all-you-need"
    assert generate_paper_id("") == "untitled"
    assert generate_paper_id("A/B Testing: Results!") == "ab-testing-results"


def test_generate_paper_id_length_limit():
    long_title = "A" * 200
    result = generate_paper_id(long_title)
    assert len(result) <= 80


def test_save_creates_files(sample_results, sample_metadata, output_dir):
    paper_id = save(sample_results, sample_metadata, output_dir)
    assert paper_id == "attention-is-all-you-need"

    json_path = os.path.join(output_dir, "json", f"{paper_id}.json")
    md_path = os.path.join(output_dir, "markdown", f"{paper_id}.md")
    assert os.path.exists(json_path)
    assert os.path.exists(md_path)


def test_save_json_content(sample_results, sample_metadata, output_dir):
    paper_id = save(sample_results, sample_metadata, output_dir)
    json_path = os.path.join(output_dir, "json", f"{paper_id}.json")

    with open(json_path) as f:
        data = json.load(f)

    assert data["title"] == "Attention Is All You Need"
    assert data["authors"] == ["Vaswani, A.", "Shazeer, N."]
    assert data["year"] == 2017
    assert "claude" in data["readings"]
    assert data["readers_used"] == ["claude"]


def test_save_markdown_content(sample_results, sample_metadata, output_dir):
    paper_id = save(sample_results, sample_metadata, output_dir)
    md_path = os.path.join(output_dir, "markdown", f"{paper_id}.md")

    with open(md_path) as f:
        content = f.read()

    assert "# Attention Is All You Need" in content
    assert "Vaswani, A." in content
    assert "Claude's Reading" in content


def test_save_conflict_resolution(sample_results, sample_metadata, output_dir):
    paper_id1 = save(sample_results, sample_metadata, output_dir)
    paper_id2 = save(sample_results, sample_metadata, output_dir)
    assert paper_id1 == "attention-is-all-you-need"
    assert paper_id2 == "attention-is-all-you-need-2"


def test_save_dual_reader(sample_metadata, output_dir):
    results = {
        "claude": {
            "title": "Test Paper",
            "authors": ["Author, A."],
            "year": 2024,
            "abstract_summary": "Claude's summary.",
            "key_contributions": ["Contribution 1"],
            "methodology": "Method A",
            "main_results": "Result A",
            "limitations": ["Limit 1"],
            "connections": "Connection A",
            "tags": ["tag1"],
        },
        "codex": {
            "title": "Test Paper",
            "authors": ["Author, A."],
            "year": 2024,
            "abstract_summary": "Codex's summary.",
            "key_contributions": ["Contribution 2"],
            "methodology": "Method B",
            "main_results": "Result B",
            "limitations": ["Limit 2"],
            "connections": "Connection B",
            "tags": ["tag2"],
        },
    }
    paper_id = save(results, sample_metadata, output_dir)

    json_path = os.path.join(output_dir, "json", f"{paper_id}.json")
    with open(json_path) as f:
        data = json.load(f)

    assert "claude" in data["readings"]
    assert "codex" in data["readings"]
    assert set(data["readers_used"]) == {"claude", "codex"}
