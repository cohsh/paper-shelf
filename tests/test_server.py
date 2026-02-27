import json
import os
import tempfile

import pymupdf
import pytest
from fastapi.testclient import TestClient

from paper_shelf.server.app import create_app
from paper_shelf.server.tasks import TaskManager
from paper_shelf.storage import save
from paper_shelf.library import update_index


@pytest.fixture
def library_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def populated_library(library_dir):
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
    pid = save(results, {}, library_dir)
    update_index(pid, library_dir)
    return library_dir, pid


@pytest.fixture
def client(library_dir):
    app = create_app(output_dir=library_dir)
    return TestClient(app)


@pytest.fixture
def populated_client(populated_library):
    library_dir, pid = populated_library
    app = create_app(output_dir=library_dir)
    return TestClient(app), pid


def test_list_papers_empty(client):
    res = client.get("/api/papers")
    assert res.status_code == 200
    data = res.json()
    assert data["papers"] == []
    assert data["total"] == 0


def test_list_papers(populated_client):
    client, _ = populated_client
    res = client.get("/api/papers")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["papers"][0]["title"] == "Test Paper"


def test_get_paper(populated_client):
    client, pid = populated_client
    res = client.get(f"/api/papers/{pid}")
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "Test Paper"
    assert "readings" in data


def test_get_paper_not_found(client):
    res = client.get("/api/papers/nonexistent")
    assert res.status_code == 404


def test_get_paper_markdown(populated_client):
    client, pid = populated_client
    res = client.get(f"/api/papers/{pid}/markdown")
    assert res.status_code == 200
    data = res.json()
    assert "Test Paper" in data["markdown"]


def test_delete_paper(populated_client):
    client, pid = populated_client
    res = client.delete(f"/api/papers/{pid}")
    assert res.status_code == 200
    assert res.json() == {"ok": True}

    # Verify it's gone
    res = client.get(f"/api/papers/{pid}")
    assert res.status_code == 404


def test_search_papers(populated_client):
    client, _ = populated_client
    res = client.get("/api/papers?search=test")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1


def test_search_no_results(populated_client):
    client, _ = populated_client
    res = client.get("/api/papers?search=quantum")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0


def test_upload_non_pdf(client):
    res = client.post(
        "/api/upload",
        files={"file": ("test.txt", b"not a pdf", "text/plain")},
        data={"reader": "claude"},
    )
    assert res.status_code == 400


def test_task_not_found(client):
    res = client.get("/api/tasks/nonexistent")
    assert res.status_code == 404


def test_task_manager():
    tm = TaskManager()
    tid = tm.create_task()
    task = tm.get(tid)
    assert task is not None
    assert task.status == "pending"

    tm.update(tid, status="extracting", progress_message="Working...")
    task = tm.get(tid)
    assert task is not None
    assert task.status == "extracting"
    assert task.progress_message == "Working..."

    all_tasks = tm.all_tasks()
    assert len(all_tasks) == 1
