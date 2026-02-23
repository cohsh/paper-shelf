import json
import os
import tempfile

import pytest

from src.library import (
    UNSORTED_SHELF_ID,
    add_paper_to_shelf,
    assign_paper_to_shelves,
    create_shelf,
    delete_shelf,
    get_paper,
    get_shelf,
    list_papers_by_shelf,
    list_shelves,
    load_index,
    remove_paper_from_shelf,
    rename_shelf,
    search,
    update_index,
)
from src.exceptions import StorageError
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


# ---------------------------------------------------------------------------
# Index basics
# ---------------------------------------------------------------------------

def test_load_index_empty(library_dir):
    index = load_index(library_dir)
    assert index["version"] == 2
    assert index["papers"] == []
    assert index["shelves"] == []


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


# ---------------------------------------------------------------------------
# v1 -> v2 migration
# ---------------------------------------------------------------------------

def test_migrate_v1_to_v2(library_dir):
    """v1 index should auto-migrate to v2 on load."""
    v1 = {
        "version": 1,
        "updated_at": "2025-01-01T00:00:00+00:00",
        "papers": [
            {
                "paper_id": "test-paper",
                "title": "Test Paper",
                "authors": ["Author"],
                "year": 2024,
                "read_date": "2025-01-01",
                "tags": ["test"],
                "readers_used": ["claude"],
            }
        ],
    }
    index_path = os.path.join(library_dir, "index.json")
    with open(index_path, "w") as f:
        json.dump(v1, f)

    index = load_index(library_dir)
    assert index["version"] == 2
    assert index["shelves"] == []
    assert index["papers"][0]["shelves"] == []


def test_migrate_preserves_papers(library_dir):
    """All v1 papers should exist in v2 with empty shelves."""
    v1 = {
        "version": 1,
        "updated_at": "2025-01-01T00:00:00+00:00",
        "papers": [
            {"paper_id": "a", "title": "Paper A"},
            {"paper_id": "b", "title": "Paper B"},
        ],
    }
    index_path = os.path.join(library_dir, "index.json")
    with open(index_path, "w") as f:
        json.dump(v1, f)

    index = load_index(library_dir)
    assert len(index["papers"]) == 2
    for p in index["papers"]:
        assert p["shelves"] == []


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

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


def test_search_with_shelf_filter(populated_library):
    library_dir, pid1, pid2 = populated_library
    shelf = create_shelf("NLP", library_dir)
    add_paper_to_shelf(pid1, shelf["shelf_id"], library_dir)

    results = search("nlp", field="tags", output_dir=library_dir, shelf=shelf["shelf_id"])
    assert len(results) == 1
    assert results[0]["paper_id"] == pid1


def test_search_with_unsorted_filter(populated_library):
    library_dir, pid1, pid2 = populated_library
    shelf = create_shelf("NLP", library_dir)
    add_paper_to_shelf(pid1, shelf["shelf_id"], library_dir)

    results = search("nlp", field="tags", output_dir=library_dir, shelf=UNSORTED_SHELF_ID)
    assert len(results) == 1
    assert results[0]["paper_id"] == pid2


# ---------------------------------------------------------------------------
# Shelf CRUD
# ---------------------------------------------------------------------------

def test_create_shelf(library_dir):
    shelf = create_shelf("Machine Learning", library_dir, name_ja="機械学習")
    assert shelf["shelf_id"] == "machine-learning"
    assert shelf["name"] == "Machine Learning"
    assert shelf["name_ja"] == "機械学習"
    assert "created_at" in shelf


def test_create_shelf_duplicate_raises(library_dir):
    create_shelf("ML", library_dir)
    with pytest.raises(StorageError, match="already exists"):
        create_shelf("ML", library_dir)


def test_list_shelves_includes_unsorted(library_dir):
    shelves = list_shelves(library_dir)
    assert len(shelves) == 1
    assert shelves[0]["shelf_id"] == UNSORTED_SHELF_ID
    assert shelves[0]["is_virtual"] is True


def test_list_shelves_paper_counts(populated_library):
    library_dir, pid1, pid2 = populated_library
    shelf = create_shelf("NLP", library_dir)
    add_paper_to_shelf(pid1, shelf["shelf_id"], library_dir)

    shelves = list_shelves(library_dir)
    unsorted = next(s for s in shelves if s["shelf_id"] == UNSORTED_SHELF_ID)
    nlp = next(s for s in shelves if s["shelf_id"] == shelf["shelf_id"])
    assert unsorted["paper_count"] == 1  # pid2 has no shelf
    assert nlp["paper_count"] == 1


def test_get_shelf(library_dir):
    create_shelf("Physics", library_dir)
    shelf = get_shelf("physics", library_dir)
    assert shelf["name"] == "Physics"


def test_get_shelf_not_found(library_dir):
    with pytest.raises(StorageError, match="not found"):
        get_shelf("nonexistent", library_dir)


def test_get_unsorted_shelf(library_dir):
    shelf = get_shelf(UNSORTED_SHELF_ID, library_dir)
    assert shelf["is_virtual"] is True


def test_rename_shelf(library_dir):
    create_shelf("ML", library_dir)
    updated = rename_shelf("ml", "Machine Learning", library_dir, name_ja="機械学習")
    assert updated["shelf_id"] == "machine-learning"
    assert updated["name"] == "Machine Learning"
    assert updated["name_ja"] == "機械学習"


def test_rename_shelf_updates_paper_references(populated_library):
    library_dir, pid1, _ = populated_library
    shelf = create_shelf("ML", library_dir)
    add_paper_to_shelf(pid1, shelf["shelf_id"], library_dir)

    rename_shelf("ml", "Machine Learning", library_dir)

    index = load_index(library_dir)
    paper = next(p for p in index["papers"] if p["paper_id"] == pid1)
    assert "machine-learning" in paper["shelves"]
    assert "ml" not in paper["shelves"]


def test_rename_unsorted_raises(library_dir):
    with pytest.raises(StorageError, match="Cannot rename"):
        rename_shelf(UNSORTED_SHELF_ID, "Something", library_dir)


def test_delete_shelf(populated_library):
    library_dir, pid1, _ = populated_library
    shelf = create_shelf("Temp", library_dir)
    add_paper_to_shelf(pid1, shelf["shelf_id"], library_dir)

    delete_shelf(shelf["shelf_id"], library_dir)

    shelves = list_shelves(library_dir)
    assert not any(s["shelf_id"] == shelf["shelf_id"] for s in shelves)

    index = load_index(library_dir)
    paper = next(p for p in index["papers"] if p["paper_id"] == pid1)
    assert shelf["shelf_id"] not in paper["shelves"]


def test_delete_unsorted_raises(library_dir):
    with pytest.raises(StorageError, match="Cannot delete"):
        delete_shelf(UNSORTED_SHELF_ID, library_dir)


def test_delete_shelf_not_found(library_dir):
    with pytest.raises(StorageError, match="not found"):
        delete_shelf("nonexistent", library_dir)


# ---------------------------------------------------------------------------
# Paper-shelf assignment
# ---------------------------------------------------------------------------

def test_assign_paper_to_shelves(populated_library):
    library_dir, pid1, _ = populated_library
    s1 = create_shelf("A", library_dir)
    s2 = create_shelf("B", library_dir)

    assign_paper_to_shelves(pid1, [s1["shelf_id"], s2["shelf_id"]], library_dir)

    index = load_index(library_dir)
    paper = next(p for p in index["papers"] if p["paper_id"] == pid1)
    assert set(paper["shelves"]) == {s1["shelf_id"], s2["shelf_id"]}


def test_assign_replaces_existing(populated_library):
    library_dir, pid1, _ = populated_library
    s1 = create_shelf("A", library_dir)
    s2 = create_shelf("B", library_dir)

    assign_paper_to_shelves(pid1, [s1["shelf_id"]], library_dir)
    assign_paper_to_shelves(pid1, [s2["shelf_id"]], library_dir)

    index = load_index(library_dir)
    paper = next(p for p in index["papers"] if p["paper_id"] == pid1)
    assert paper["shelves"] == [s2["shelf_id"]]


def test_assign_invalid_shelf_raises(populated_library):
    library_dir, pid1, _ = populated_library
    with pytest.raises(StorageError, match="not found"):
        assign_paper_to_shelves(pid1, ["nonexistent"], library_dir)


def test_add_paper_to_shelf(populated_library):
    library_dir, pid1, _ = populated_library
    shelf = create_shelf("NLP", library_dir)
    add_paper_to_shelf(pid1, shelf["shelf_id"], library_dir)

    index = load_index(library_dir)
    paper = next(p for p in index["papers"] if p["paper_id"] == pid1)
    assert shelf["shelf_id"] in paper["shelves"]


def test_add_paper_to_shelf_idempotent(populated_library):
    library_dir, pid1, _ = populated_library
    shelf = create_shelf("NLP", library_dir)
    add_paper_to_shelf(pid1, shelf["shelf_id"], library_dir)
    add_paper_to_shelf(pid1, shelf["shelf_id"], library_dir)

    index = load_index(library_dir)
    paper = next(p for p in index["papers"] if p["paper_id"] == pid1)
    assert paper["shelves"].count(shelf["shelf_id"]) == 1


def test_remove_paper_from_shelf(populated_library):
    library_dir, pid1, _ = populated_library
    shelf = create_shelf("NLP", library_dir)
    add_paper_to_shelf(pid1, shelf["shelf_id"], library_dir)
    remove_paper_from_shelf(pid1, shelf["shelf_id"], library_dir)

    index = load_index(library_dir)
    paper = next(p for p in index["papers"] if p["paper_id"] == pid1)
    assert shelf["shelf_id"] not in paper["shelves"]


def test_paper_with_no_shelves_is_unsorted(populated_library):
    library_dir, pid1, pid2 = populated_library
    # No shelves assigned -> both should be in unsorted
    papers = list_papers_by_shelf(UNSORTED_SHELF_ID, library_dir)
    assert len(papers) == 2


# ---------------------------------------------------------------------------
# Filtered listing
# ---------------------------------------------------------------------------

def test_list_papers_by_shelf(populated_library):
    library_dir, pid1, pid2 = populated_library
    shelf = create_shelf("NLP", library_dir)
    add_paper_to_shelf(pid1, shelf["shelf_id"], library_dir)

    papers = list_papers_by_shelf(shelf["shelf_id"], library_dir)
    assert len(papers) == 1
    assert papers[0]["paper_id"] == pid1


def test_list_papers_all(populated_library):
    library_dir, _, _ = populated_library
    papers = list_papers_by_shelf(None, library_dir)
    assert len(papers) == 2


def test_list_papers_unsorted_shelf(populated_library):
    library_dir, pid1, pid2 = populated_library
    shelf = create_shelf("NLP", library_dir)
    add_paper_to_shelf(pid1, shelf["shelf_id"], library_dir)

    papers = list_papers_by_shelf(UNSORTED_SHELF_ID, library_dir)
    assert len(papers) == 1
    assert papers[0]["paper_id"] == pid2


# ---------------------------------------------------------------------------
# update_index with shelves parameter
# ---------------------------------------------------------------------------

def test_update_index_preserves_existing_shelves(populated_library):
    library_dir, pid1, _ = populated_library
    shelf = create_shelf("NLP", library_dir)
    add_paper_to_shelf(pid1, shelf["shelf_id"], library_dir)

    # Re-index without specifying shelves -> should preserve
    update_index(pid1, library_dir)

    index = load_index(library_dir)
    paper = next(p for p in index["papers"] if p["paper_id"] == pid1)
    assert shelf["shelf_id"] in paper["shelves"]


def test_update_index_with_new_shelves(populated_library):
    library_dir, pid1, _ = populated_library
    shelf = create_shelf("NLP", library_dir)

    update_index(pid1, library_dir, shelves=[shelf["shelf_id"]])

    index = load_index(library_dir)
    paper = next(p for p in index["papers"] if p["paper_id"] == pid1)
    assert paper["shelves"] == [shelf["shelf_id"]]
